import sys
import os
import re
import frontmatter

def slugify(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-')
    return slug

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

    title = post.get("title", "") or ""
    description = post.get("description", "") or ""
    slug = post.get("slug", slug) or slug
    date = post.get("date", "") or ""
    image_name = post.get("image", "") or ""
    image_alt = post.get("image-alt", "") or ""

    # Build date path like 2026/04/06
    date_path = ""
    display_date = ""
    if date:
        from datetime import datetime
        if isinstance(date, str):
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        else:
            date_obj = datetime.combine(date, datetime.min.time())
        date_path = date_obj.strftime("%Y/%m/%d")
        display_date = date_obj.strftime("%B %-d, %Y")
        date = date_obj.strftime("%Y-%m-%d")

    # Image URLs
    image_url = ""
    og_image_url = ""
    if image_name:
        base = f"https://storage.googleapis.com/stephenoravec-media/blog/{date_path}"
        image_url = f"{base}/{image_name}-1000.webp"
        og_image_url = f"{base}/{image_name}-og.webp"

    # Body content (empty for short posts)
    body_content = ""
    if post.content.strip():
        body_content = post.content

    # Read template
    template_path = os.path.join(templates_dir, "post.html")
    with open(template_path, "r") as f:
        template = f.read()

    # Replace placeholders
    html = template.replace("{{title}}", title)
    html = html.replace("{{description}}", description)
    html = html.replace("{{slug}}", slug)
    html = html.replace("{{date}}", date)
    html = html.replace("{{date_path}}", date_path)
    html = html.replace("{{display_date}}", display_date)
    html = html.replace("{{image_url}}", image_url)
    html = html.replace("{{image_alt}}", image_alt)
    html = html.replace("{{og_image_url}}", og_image_url)
    html = html.replace("{{body_content}}", body_content)

    # Write output
    output_dir = os.path.join(blog_dir, "output", "blog", date_path, slug)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built post: {output_path}")

def new_post(title):
    slug = slugify(title)
    
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    staging_dir = os.path.join(blog_dir, "staging")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")

    if os.path.exists(draft_path):
        print(f"Draft already exists: {draft_path}")
        sys.exit(1)

    template = f"""---
title: "{title}"
slug: {slug}
date:
time:
image:
image-alt:
description:
tags: []
category:
subcategory:
source: original
type: short
origin:
origin-date:
import-date:
---
"""

    with open(draft_path, "w") as f:
        f.write(template)

    staging_path = os.path.join(staging_dir, slug)
    os.makedirs(staging_path, exist_ok=True)

    print(f"Created draft: {draft_path}")
    print(f"Created staging folder: {staging_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python blog.py <command> [arguments]")
        print("Commands: new, preview")
        sys.exit(1)

    command = sys.argv[1]

    if command == "new":
        if len(sys.argv) < 3:
            print('Usage: python blog.py new "Post Title"')
            sys.exit(1)
        new_post(sys.argv[2])
    elif command == "preview":
        if len(sys.argv) < 3:
            print('Usage: python blog.py preview <slug>')
            sys.exit(1)
        preview_post(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()