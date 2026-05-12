import os
import json
from datetime import datetime

import frontmatter

from config import post_url_path
from render import md_to_html, parse_body


def build_index(repo_root):
    """Scan published posts, generate JSON chunks, and regenerate the blog index page."""
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    published_dir = os.path.join(blog_dir, "published")
    templates_dir = os.path.join(blog_dir, "templates")
    data_dir = os.path.join(repo_root, "blog", "data")

    os.makedirs(data_dir, exist_ok=True)

    posts = []
    if os.path.exists(published_dir):
        for year_dir in sorted(os.listdir(published_dir), reverse=True):
            year_path = os.path.join(published_dir, year_dir)
            if not os.path.isdir(year_path):
                continue
            for month_dir in sorted(os.listdir(year_path), reverse=True):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                for filename in os.listdir(month_path):
                    if not filename.endswith(".md"):
                        continue
                    md_path = os.path.join(month_path, filename)
                    with open(md_path, "r") as f:
                        post = frontmatter.load(f)

                    post_date = post.get("date")
                    if not post_date:
                        continue

                    if isinstance(post_date, str):
                        date_obj = datetime.strptime(post_date, "%Y-%m-%d")
                    else:
                        date_obj = datetime.combine(post_date, datetime.min.time())

                    date_str = date_obj.strftime("%Y-%m-%d")
                    date_path = date_obj.strftime("%Y/%m/%d")
                    display_date = date_obj.strftime("%B %-d, %Y")
                    
                    slug = post.get("slug")
                    if not slug:
                        continue
                    
                    urn = post.get("urn", "") or ""
                    title = post.get("title", "") or ""
                    description_raw = post.get("description", "") or ""
                    description_html = md_to_html(description_raw)
                    image_name = post.get("image", "") or ""
                    image_alt = post.get("image-alt", "") or ""

                    layer = post.get("layer") or "status"
                    post_type = post.get("type") or "screenshot"
                    if post_type == "short":
                        post_type = "screenshot"

                    has_body = post_type == "article"

                    image_url = ""
                    image_url_400 = ""
                    image_url_1000 = ""
                    image_url_2000 = ""
                    if image_name:
                        base = f"https://storage.googleapis.com/stephenoravec-media/blog/{date_path}"
                        image_url = f"{base}/{image_name}-1000.webp"
                        image_url_400 = f"{base}/{image_name}-400.webp"
                        image_url_1000 = f"{base}/{image_name}-1000.webp"
                        image_url_2000 = f"{base}/{image_name}-2000.webp"

                    body_html = None
                    if has_body:
                        body_html = parse_body(post.content, date_path)

                    posts.append({
                        "title": title,
                        "urn": urn,
                        "slug": slug,
                        "date": date_str,
                        "display_date": display_date,
                        "url": post_url_path(slug, date_path),
                        "description_html": description_html,
                        "image_url": image_url,
                        "image_url_400": image_url_400,
                        "image_url_1000": image_url_1000,
                        "image_url_2000": image_url_2000,
                        "image_alt": image_alt,
                        "layer": layer,
                        "type": post_type,
                        "body_html": body_html,
                        "has_body": has_body,
                    })

    posts.sort(key=lambda p: p["date"], reverse=True)

    version = datetime.now().strftime("%Y%m%d%H%M%S")

    chunk_size = 10
    chunks = [posts[i:i + chunk_size] for i in range(0, len(posts), chunk_size)]

    for filename in os.listdir(data_dir):
        if filename.startswith("posts-") and filename.endswith(".json"):
            os.remove(os.path.join(data_dir, filename))

    for i, chunk in enumerate(chunks, start=1):
        chunk_path = os.path.join(data_dir, f"posts-{i}.json")
        with open(chunk_path, "w") as f:
            json.dump({"posts": chunk}, f, indent=2)
        print(f"Wrote: {chunk_path}")

    manifest = {
        "total_posts": len(posts),
        "chunk_count": len(chunks),
        "chunk_size": chunk_size,
        "version": version,
    }
    manifest_path = os.path.join(data_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote: {manifest_path}")

    template_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r") as f:
            template = f.read()
        html = template.replace("{{version}}", version)
        index_path = os.path.join(repo_root, "blog", "index.html")
        with open(index_path, "w") as f:
            f.write(html)
        print(f"Wrote: {index_path}")

    print(f"Built index: {len(posts)} posts in {len(chunks)} chunk(s)")