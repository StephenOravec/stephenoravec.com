"""Post lifecycle for the blog: new, preview, publish, fix, validate, rebuild.

Handles draft creation, slug validation, URN generation, frontmatter
serialization, and the orchestration of rendering + index/routes/sitemap
regeneration after each operation.

Posts live in publisher/drafts/ until published, then move to
publisher/published/YYYY/MM/<slug>.md. Rendered HTML output lands at
blog/YYYY/MM/DD/<slug>/index.html in the repo root.
"""

import os
import re
import shutil
import sys
from datetime import date as date_module, datetime

import frontmatter

from .blog import build_index
from .config import PUBLISHER_DIR, REPO_ROOT, post_output_subpath, post_url_path
from .feeds import build_routes, build_sitemap
from .images import process_images
from .render import render_post, write_post_html


FIELD_ORDER: list[str] = [
    "title", "urn", "slug", "legacy_urls", "date", "time",
    "image", "image-alt",
    "description",
    "category", "subcategory", "tags",
    "layer", "type",
    "source",
    "origin", "import-date",
]


# Slugs that can't be used at root because they collide with site paths,
# planned site paths, or common web conventions. Adjust as site grows.
RESERVED_SLUGS: set[str] = {
    # Existing or planned root paths on stephenoravec.com
    "about", "blog", "books", "cablepunk", "games", "inventory", "photography", "profiles",
    "reputation", "resources", "synthography", "videogames", "websites",
    # Web conventions
    "index", "404", "robots", "sitemap",
    # Feed-related names
    "feed", "feeds", "rss", "atom",
    # Common system paths
    "api", "admin", "static", "assets", "data", "search",
    # Taxonomy paths
    "tag", "tags", "category", "categories", "archive", "archives",
    # General conventions
    "contact", "login", "logout", "signin", "signout",
}


def slugify(title: str) -> str:
    """Convert a title into a URL-safe slug."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-')
    return slug


def validate_slug(slug: str, exclude_path: str | None = None) -> tuple[bool, str]:
    """Validate a slug against reserved names and existing usage.
    Returns (True, "") on success, (False, error_message) on failure.
    """
    if not slug:
        return False, "Slug is empty."
    if slug in RESERVED_SLUGS:
        return False, (
            f"Slug '{slug}' is reserved (conflicts with a site path "
            f"or web convention). Pick a different slug."
        )
    conflict = _find_slug_usage(slug, exclude_path)
    if conflict:
        return False, f"Slug '{slug}' is already used by {conflict}."
    return True, ""


def _find_slug_usage(slug: str, exclude_path: str | None = None) -> str | None:
    """Find the path of the post currently using this slug, or None."""
    drafts_dir = os.path.join(PUBLISHER_DIR, "drafts")
    published_dir = os.path.join(PUBLISHER_DIR, "published")

    candidates = []

    if os.path.exists(drafts_dir):
        for filename in os.listdir(drafts_dir):
            if filename.endswith(".md"):
                candidates.append(os.path.join(drafts_dir, filename))

    if os.path.exists(published_dir):
        for year_dir in os.listdir(published_dir):
            year_path = os.path.join(published_dir, year_dir)
            if not os.path.isdir(year_path):
                continue
            for month_dir in os.listdir(year_path):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                for filename in os.listdir(month_path):
                    if filename.endswith(".md"):
                        candidates.append(os.path.join(month_path, filename))

    for md_path in candidates:
        if exclude_path and os.path.abspath(md_path) == os.path.abspath(exclude_path):
            continue
        with open(md_path, "r") as f:
            post = frontmatter.load(f)
        if (post.get("slug", "") or "") == slug:
            return md_path

    return None


def validate_all() -> list[tuple[str, str]]:
    """Scan all drafts and published posts for slug issues. Returns list of (path, issue) tuples."""
    issues = []
    seen = {}

    drafts_dir = os.path.join(PUBLISHER_DIR, "drafts")
    published_dir = os.path.join(PUBLISHER_DIR, "published")

    paths = []
    if os.path.exists(drafts_dir):
        for filename in sorted(os.listdir(drafts_dir)):
            if filename.endswith(".md"):
                paths.append(os.path.join(drafts_dir, filename))
    if os.path.exists(published_dir):
        for year_dir in sorted(os.listdir(published_dir)):
            year_path = os.path.join(published_dir, year_dir)
            if not os.path.isdir(year_path):
                continue
            for month_dir in sorted(os.listdir(year_path)):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                for filename in sorted(os.listdir(month_path)):
                    if filename.endswith(".md"):
                        paths.append(os.path.join(month_path, filename))

    for md_path in paths:
        with open(md_path, "r") as f:
            post = frontmatter.load(f)
        slug = post.get("slug", "") or ""

        if not slug:
            issues.append((md_path, "No slug in frontmatter"))
            continue
        if slug in RESERVED_SLUGS:
            issues.append((md_path, f"Slug '{slug}' is reserved"))
        if slug in seen:
            issues.append((md_path, f"Slug '{slug}' duplicates {seen[slug]}"))
        else:
            seen[slug] = md_path

    return issues


def _all_existing_urns() -> set[str]:
    """Collect every URN already present in drafts and published posts."""
    drafts_dir = os.path.join(PUBLISHER_DIR, "drafts")
    published_dir = os.path.join(PUBLISHER_DIR, "published")

    urns = set()
    paths = []

    if os.path.exists(drafts_dir):
        for filename in os.listdir(drafts_dir):
            if filename.endswith(".md"):
                paths.append(os.path.join(drafts_dir, filename))

    if os.path.exists(published_dir):
        for year_dir in os.listdir(published_dir):
            year_path = os.path.join(published_dir, year_dir)
            if not os.path.isdir(year_path):
                continue
            for month_dir in os.listdir(year_path):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                for filename in os.listdir(month_path):
                    if filename.endswith(".md"):
                        paths.append(os.path.join(month_path, filename))

    for md_path in paths:
        with open(md_path, "r") as f:
            post = frontmatter.load(f)
        urn = post.get("urn")
        if urn:
            urns.add(str(urn))

    return urns


def _generate_urn(date_obj: datetime) -> str:
    """Generate a unique URN for a natively-published post.

    Format: 14-digit YYYYMMDDHHMMSS. For native blog posts, the time portion
    starts at 000000 and increments by 1 for each collision on the same date.
    """
    existing = _all_existing_urns()
    date_prefix = date_obj.strftime("%Y%m%d")
    for seconds in range(1000000):  # one million slots per day, more than enough
        candidate = f"{date_prefix}{seconds:06d}"
        if candidate not in existing:
            return candidate
    raise RuntimeError(f"Exhausted URN slots for {date_prefix}.")


def write_post_file(path: str, post: frontmatter.Post) -> None:
    """Write a frontmatter Post to file with preferred field order."""
    lines = ["---"]
    for field in FIELD_ORDER:
        value = post.metadata.get(field)
        if value is None or value == "":
            lines.append(f"{field}:")
        elif isinstance(value, list):
            if len(value) == 0:
                lines.append(f"{field}: []")
            else:
                items = ", ".join(str(v) for v in value)
                lines.append(f"{field}: [{items}]")
        elif isinstance(value, str) and (
            ":" in value or "*" in value or "'" in value or value.isdigit()
        ):
            escaped = value.replace("'", "''")
            lines.append(f"{field}: '{escaped}'")
        else:
            lines.append(f"{field}: {value}")

    lines.append("---")
    if post.content:
        lines.append("")
        lines.append(post.content)

    with open(path, "w") as f:
        f.write("\n".join(lines))


def _parse_post_date(post: frontmatter.Post) -> tuple[datetime | None, str]:
    """Parse the post's date frontmatter. Returns (datetime, "YYYY/MM/DD") or (None, "")."""
    post_date = post.get("date")
    if not post_date:
        return None, ""
    if isinstance(post_date, str):
        date_obj = datetime.strptime(post_date, "%Y-%m-%d")
    else:
        date_obj = datetime.combine(post_date, datetime.min.time())
    return date_obj, date_obj.strftime("%Y/%m/%d")


def _render_post_to_disk(
    post: frontmatter.Post,
    slug_fallback: str,
    date_path: str,
    templates_dir: str,
    repo_root: str,
) -> str:
    """Render a post and write its HTML to the canonical filesystem location.
    Returns the actual slug used (frontmatter wins over fallback)."""
    actual_slug = post.get("slug", slug_fallback) or slug_fallback
    html = render_post(post, actual_slug, date_path, templates_dir)
    output_dir = os.path.join(repo_root, *post_output_subpath(actual_slug, date_path))
    output_path = write_post_html(html, output_dir)
    print(f"Built: {output_path}")
    return actual_slug


def _find_published_path(slug: str, published_dir: str) -> str | None:
    """Find the .md file for a published post by slug, or None if not found."""
    if not os.path.exists(published_dir):
        return None
    for year_dir in os.listdir(published_dir):
        year_path = os.path.join(published_dir, year_dir)
        if not os.path.isdir(year_path):
            continue
        for month_dir in os.listdir(year_path):
            month_path = os.path.join(year_path, month_dir)
            if not os.path.isdir(month_path):
                continue
            candidate = os.path.join(month_path, f"{slug}.md")
            if os.path.exists(candidate):
                return candidate
    return None


def new_post(title: str) -> None:
    """Create a new draft .md file and corresponding staging folder for the given title."""
    slug = slugify(title)

    valid, error = validate_slug(slug)
    if not valid:
        print(error)
        sys.exit(1)

    drafts_dir = os.path.join(PUBLISHER_DIR, "drafts")
    staging_dir = os.path.join(PUBLISHER_DIR, "staging")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")

    if os.path.exists(draft_path):
        print(f"Draft already exists: {draft_path}")
        sys.exit(1)

    lines = ["---"]
    for field in FIELD_ORDER:
        if field == "title":
            lines.append(f'title: "{title}"')
        elif field == "slug":
            lines.append(f"slug: {slug}")
        elif field == "urn":
            lines.append("urn:")
        elif field == "legacy_urls":
            lines.append("legacy_urls: []")
        elif field == "tags":
            lines.append("tags: []")
        elif field == "layer":
            lines.append("layer: status")
        elif field == "source":
            lines.append("source: original")
        elif field == "type":
            lines.append("type:")
        else:
            lines.append(f"{field}:")
    lines.append("---")
    lines.append("")

    with open(draft_path, "w") as f:
        f.write("\n".join(lines))

    staging_path = os.path.join(staging_dir, slug)
    os.makedirs(staging_path, exist_ok=True)

    print(f"Created draft: {draft_path}")
    print(f"Created staging folder: {staging_path}")


def preview_post(slug: str) -> None:
    """Render a draft to publisher/preview/ without modifying the draft itself.
    Images will be broken; image processing occurs during publish_post.
    """
    drafts_dir = os.path.join(PUBLISHER_DIR, "drafts")
    templates_dir = os.path.join(PUBLISHER_DIR, "templates")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")
    if not os.path.exists(draft_path):
        print(f"Draft not found: {draft_path}")
        sys.exit(1)

    with open(draft_path, "r") as f:
        post = frontmatter.load(f)

    actual_slug = post.get("slug", slug) or slug
    _, date_path = _parse_post_date(post)

    html = render_post(post, actual_slug, date_path, templates_dir)
    output_dir = os.path.join(
        PUBLISHER_DIR, "preview", *post_output_subpath(actual_slug, date_path)
    )
    output_path = write_post_html(html, output_dir)

    print(f"Built post: {output_path}")


def publish_post(slug: str) -> None:
    """Stamp date and URN, process images, render HTML, move draft to published/, rebuild artifacts."""
    drafts_dir = os.path.join(PUBLISHER_DIR, "drafts")
    published_dir = os.path.join(PUBLISHER_DIR, "published")
    templates_dir = os.path.join(PUBLISHER_DIR, "templates")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")
    if not os.path.exists(draft_path):
        print(f"Draft not found: {draft_path}")
        sys.exit(1)

    with open(draft_path, "r") as f:
        post = frontmatter.load(f)

    actual_slug = post.get("slug", slug) or slug
    valid, error = validate_slug(actual_slug, exclude_path=draft_path)
    if not valid:
        print(error)
        sys.exit(1)

    if not post.get("date"):
        post["date"] = date_module.today().strftime("%Y-%m-%d")

    date_obj, date_path = _parse_post_date(post)

    if not post.get("urn"):
        post["urn"] = _generate_urn(date_obj)
        print(f"Stamped URN: {post['urn']}")

    write_post_file(draft_path, post)

    process_images(slug, date_path)

    _render_post_to_disk(post, slug, date_path, templates_dir, REPO_ROOT)

    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    published_path = os.path.join(published_dir, year, month, f"{slug}.md")
    os.makedirs(os.path.dirname(published_path), exist_ok=True)
    shutil.move(draft_path, published_path)
    print(f"Moved draft to: {published_path}")

    print(f"Published: https://stephenoravec.com{post_url_path(actual_slug, date_path)}")

    build_index(REPO_ROOT)
    build_routes(REPO_ROOT)
    build_sitemap(REPO_ROOT)


def fix_post(slug: str) -> None:
    """Regenerate a published post's HTML without reprocessing images."""
    published_dir = os.path.join(PUBLISHER_DIR, "published")
    templates_dir = os.path.join(PUBLISHER_DIR, "templates")

    published_path = _find_published_path(slug, published_dir)
    if not published_path:
        print(f"Published post not found: {slug}")
        sys.exit(1)

    with open(published_path, "r") as f:
        post = frontmatter.load(f)

    if not post.get("date"):
        print(f"Post has no date: {slug}")
        sys.exit(1)

    _, date_path = _parse_post_date(post)

    actual_slug = _render_post_to_disk(post, slug, date_path, templates_dir, REPO_ROOT)

    build_index(REPO_ROOT)
    build_routes(REPO_ROOT)
    build_sitemap(REPO_ROOT)

    print(f"Fixed: https://stephenoravec.com{post_url_path(actual_slug, date_path)}")


def rebuild() -> None:
    """Regenerate all post HTML, the index, and the routes file.
    Use this after changing url_scheme or anything else that affects all posts at once.
    """
    published_dir = os.path.join(PUBLISHER_DIR, "published")
    templates_dir = os.path.join(PUBLISHER_DIR, "templates")

    count = 0
    if os.path.exists(published_dir):
        for year_dir in sorted(os.listdir(published_dir)):
            year_path = os.path.join(published_dir, year_dir)
            if not os.path.isdir(year_path):
                continue
            for month_dir in sorted(os.listdir(year_path)):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                for filename in sorted(os.listdir(month_path)):
                    if not filename.endswith(".md"):
                        continue
                    md_path = os.path.join(month_path, filename)
                    with open(md_path, "r") as f:
                        post = frontmatter.load(f)

                    if not post.get("date"):
                        continue

                    _, date_path = _parse_post_date(post)
                    slug_fallback = filename[:-3]  # strip ".md"

                    _render_post_to_disk(post, slug_fallback, date_path, templates_dir, REPO_ROOT)
                    count += 1

    print(f"Rendered {count} posts")

    build_index(REPO_ROOT)
    build_routes(REPO_ROOT)
    build_sitemap(REPO_ROOT)

    print("Rebuild complete.")