import os
import re
import sys
import shutil
from datetime import date as date_module, datetime

import frontmatter

from render import render_post, write_post_html
from images import process_images
from feeds import build_index


FIELD_ORDER = [
    "title", "slug", "legacy_urls", "date", "time",
    "image", "image-alt",
    "description",
    "category", "subcategory", "tags",
    "layer", "type",
    "source",
    "origin", "import-date",
]


# Slugs that can't be used at root because they collide with site paths,
# planned site paths, or common web conventions. Adjust as site grows.
RESERVED_SLUGS = {
    # Existing or planned root paths on stephenoravec.com
    "about", "blog", "books", "cablepunk", "games", "inventory", "photogrpahy", "profiles",
    "reputation", "resources", "sythography", "videogames", "websites",
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


def slugify(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-')
    return slug


def validate_slug(slug, exclude_path=None):
    """Check that a slug is usable. Returns (is_valid, error_message).

    Fails if the slug is empty, reserved, or already in use by another post.
    exclude_path lets the caller exclude one specific .md file from the
    uniqueness check (used during publish to ignore the draft being published).
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


def _find_slug_usage(slug, exclude_path=None):
    """Search drafts/ and published/ for any post using this slug.
    Returns the path of the first match, or None.
    """
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    published_dir = os.path.join(blog_dir, "published")

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


def validate_all():
    """Scan every draft and published post. Returns list of (path, issue) tuples.
    Empty list means everything is valid.
    """
    issues = []
    seen = {}  # slug -> path that first claimed it

    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    published_dir = os.path.join(blog_dir, "published")

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


def write_post_file(path, post):
    """Write a frontmatter Post to file with our preferred field order."""
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
        elif isinstance(value, str) and (":" in value or "*" in value or "'" in value):
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


def _parse_post_date(post):
    """Parse the post's date frontmatter. Returns (date_obj, date_path) or (None, '')."""
    post_date = post.get("date")
    if not post_date:
        return None, ""
    if isinstance(post_date, str):
        date_obj = datetime.strptime(post_date, "%Y-%m-%d")
    else:
        date_obj = datetime.combine(post_date, datetime.min.time())
    return date_obj, date_obj.strftime("%Y/%m/%d")


def _find_published_path(slug, published_dir):
    """Search published/YYYY/MM/ for slug.md. Returns full path or None."""
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


def new_post(title):
    slug = slugify(title)

    valid, error = validate_slug(slug)
    if not valid:
        print(error)
        sys.exit(1)

    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    staging_dir = os.path.join(blog_dir, "staging")

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


def preview_post(slug):
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    templates_dir = os.path.join(blog_dir, "templates")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")
    if not os.path.exists(draft_path):
        print(f"Draft not found: {draft_path}")
        sys.exit(1)

    with open(draft_path, "r") as f:
        post = frontmatter.load(f)

    actual_slug = post.get("slug", slug) or slug
    _, date_path = _parse_post_date(post)

    html = render_post(post, actual_slug, date_path, templates_dir)
    output_dir = os.path.join(blog_dir, "preview", date_path, actual_slug)
    output_path = write_post_html(html, output_dir)

    print(f"Built post: {output_path}")


def publish_post(slug):
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    published_dir = os.path.join(blog_dir, "published")
    templates_dir = os.path.join(blog_dir, "templates")
    repo_root = os.path.dirname(blog_dir)

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

    write_post_file(draft_path, post)

    process_images(slug, date_path)

    html = render_post(post, actual_slug, date_path, templates_dir)
    output_dir = os.path.join(repo_root, "blog", date_path, actual_slug)
    output_path = write_post_html(html, output_dir)
    print(f"Built: {output_path}")

    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    published_path = os.path.join(published_dir, year, month, f"{slug}.md")
    os.makedirs(os.path.dirname(published_path), exist_ok=True)
    shutil.move(draft_path, published_path)
    print(f"Moved draft to: {published_path}")

    print(f"Published: https://stephenoravec.com/blog/{date_path}/{slug}/")

    build_index(repo_root)


def fix_post(slug):
    """Regenerate a published post's HTML without reprocessing images."""
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    published_dir = os.path.join(blog_dir, "published")
    templates_dir = os.path.join(blog_dir, "templates")
    repo_root = os.path.dirname(blog_dir)

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

    actual_slug = post.get("slug", slug) or slug
    html = render_post(post, actual_slug, date_path, templates_dir)
    output_dir = os.path.join(repo_root, "blog", date_path, actual_slug)
    output_path = write_post_html(html, output_dir)
    print(f"Built: {output_path}")

    build_index(repo_root)

    print(f"Fixed: https://stephenoravec.com/blog/{date_path}/{slug}/")