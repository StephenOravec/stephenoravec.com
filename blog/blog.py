import sys
import os
import re
import frontmatter
from PIL import Image
from google.cloud import storage as gcs_storage

def slugify(title):
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-')
    return slug

def md_to_html(text):
    """Convert basic Markdown formatting to HTML for rich-text contexts."""
    if not text:
        return ""
    # Bold first: **text** becomes <strong>text</strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Then italics: *text* becomes <em>text</em>
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text

def strip_markdown(text):
    """Strip Markdown formatting for plain-text contexts like meta tags."""
    if not text:
        return ""
    # Remove bold markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Remove italic markers
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return text

def process_images(slug, date_path):
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    staging_dir = os.path.join(blog_dir, "staging", slug)

    if not os.path.exists(staging_dir):
        print(f"Staging folder not found: {staging_dir}")
        sys.exit(1)

    # Find all images in the staging folder
    image_extensions = (".png", ".jpg", ".jpeg")
    images = [f for f in os.listdir(staging_dir) if f.lower().endswith(image_extensions)]

    if not images:
        print(f"No images found in: {staging_dir}")
        return

    # Connect to GCS
    client = gcs_storage.Client()
    bucket = client.bucket("stephenoravec-media")

    for filename in images:
        source_path = os.path.join(staging_dir, filename)
        name = os.path.splitext(filename)[0]
        gcs_prefix = f"blog/{date_path}/{name}"

        img = Image.open(source_path)

        # Generate sizes: 1000w, 2000w, 400w thumbnail, 1200x630 OG
        sizes = {
            "1000": 1000,
            "2000": 2000,
            "400": 400,
        }

        for suffix, width in sizes.items():
            if img.width > width:
                ratio = width / img.width
                height = int(img.height * ratio)
                resized = img.resize((width, height), Image.LANCZOS)
            else:
                resized = img.copy()

            # Save to temporary file
            temp_path = os.path.join(staging_dir, f"{name}-{suffix}.webp")
            resized.save(temp_path, "WEBP", quality=85)

            # Upload to GCS
            blob = bucket.blob(f"{gcs_prefix}-{suffix}.webp")
            blob.upload_from_filename(temp_path)
            print(f"Uploaded: {gcs_prefix}-{suffix}.webp")

            # Clean up temp file
            os.remove(temp_path)

        # Generate OG image (1200x630 center crop)
        og_width = 1200
        og_height = 630
        og_ratio = og_width / og_height

        img_ratio = img.width / img.height

        if img_ratio > og_ratio:
            # Image is wider — crop sides
            new_width = int(img.height * og_ratio)
            left = (img.width - new_width) // 2
            cropped = img.crop((left, 0, left + new_width, img.height))
        else:
            # Image is taller — crop top and bottom
            new_height = int(img.width / og_ratio)
            top = (img.height - new_height) // 2
            cropped = img.crop((0, top, img.width, top + new_height))

        og = cropped.resize((og_width, og_height), Image.LANCZOS)
        og_temp_path = os.path.join(staging_dir, f"{name}-og.webp")
        og.save(og_temp_path, "WEBP", quality=85)

        blob = bucket.blob(f"{gcs_prefix}-og.webp")
        blob.upload_from_filename(og_temp_path)
        print(f"Uploaded: {gcs_prefix}-og.webp")

        os.remove(og_temp_path)

        # Upload original as archive
        blob = bucket.blob(f"{gcs_prefix}-original{os.path.splitext(filename)[1]}")
        blob.upload_from_filename(source_path)
        print(f"Uploaded: {gcs_prefix}-original{os.path.splitext(filename)[1]}")

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
    description_raw = post.get("description", "") or ""
    description_html = md_to_html(description_raw)
    description_plain = strip_markdown(description_raw)
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
    image_url_400 = ""
    image_url_1000 = ""
    image_url_2000 = ""
    og_image_url = ""
    if image_name:
        base = f"https://storage.googleapis.com/stephenoravec-media/blog/{date_path}"
        image_url = f"{base}/{image_name}-1000.webp"
        image_url_400 = f"{base}/{image_name}-400.webp"
        image_url_1000 = f"{base}/{image_name}-1000.webp"
        image_url_2000 = f"{base}/{image_name}-2000.webp"
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
    html = html.replace("{{description_html}}", description_html)
    html = html.replace("{{description_plain}}", description_plain)
    html = html.replace("{{slug}}", slug)
    html = html.replace("{{date}}", date)
    html = html.replace("{{date_path}}", date_path)
    html = html.replace("{{display_date}}", display_date)
    html = html.replace("{{image_url}}", image_url)
    html = html.replace("{{image_url_400}}", image_url_400)
    html = html.replace("{{image_url_1000}}", image_url_1000)
    html = html.replace("{{image_url_2000}}", image_url_2000)
    html = html.replace("{{image_alt}}", image_alt)
    html = html.replace("{{og_image_url}}", og_image_url)
    html = html.replace("{{body_content}}", body_content)

    # Write output
    output_dir = os.path.join(blog_dir, "preview", date_path, slug)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built post: {output_path}")

def build_published_html(slug, date_path, repo_root):
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    templates_dir = os.path.join(blog_dir, "templates")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")

    with open(draft_path, "r") as f:
        post = frontmatter.load(f)

    title = post.get("title", "") or ""
    description_raw = post.get("description", "") or ""
    description_html = md_to_html(description_raw)
    description_plain = strip_markdown(description_raw)
    slug = post.get("slug", slug) or slug
    date = post.get("date", "") or ""
    image_name = post.get("image", "") or ""
    image_alt = post.get("image-alt", "") or ""

    display_date = ""
    if date:
        from datetime import datetime
        if isinstance(date, str):
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        else:
            date_obj = datetime.combine(date, datetime.min.time())
        display_date = date_obj.strftime("%B %-d, %Y")
        date = date_obj.strftime("%Y-%m-%d")

    image_url = ""
    image_url_400 = ""
    image_url_1000 = ""
    image_url_2000 = ""
    og_image_url = ""
    if image_name:
        base = f"https://storage.googleapis.com/stephenoravec-media/blog/{date_path}"
        image_url = f"{base}/{image_name}-1000.webp"
        image_url_400 = f"{base}/{image_name}-400.webp"
        image_url_1000 = f"{base}/{image_name}-1000.webp"
        image_url_2000 = f"{base}/{image_name}-2000.webp"
        og_image_url = f"{base}/{image_name}-og.webp"

    body_content = ""
    if post.content.strip():
        body_content = post.content

    template_path = os.path.join(templates_dir, "post.html")
    with open(template_path, "r") as f:
        template = f.read()

    html = template.replace("{{title}}", title)
    html = html.replace("{{description_html}}", description_html)
    html = html.replace("{{description_plain}}", description_plain)
    html = html.replace("{{slug}}", slug)
    html = html.replace("{{date}}", date)
    html = html.replace("{{date_path}}", date_path)
    html = html.replace("{{display_date}}", display_date)
    html = html.replace("{{image_url}}", image_url)
    html = html.replace("{{image_url_400}}", image_url_400)
    html = html.replace("{{image_url_1000}}", image_url_1000)
    html = html.replace("{{image_url_2000}}", image_url_2000)
    html = html.replace("{{image_alt}}", image_alt)
    html = html.replace("{{og_image_url}}", og_image_url)
    html = html.replace("{{body_content}}", body_content)

    # Write to the live location in the repo root
    output_dir = os.path.join(repo_root, "blog", date_path, slug)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built: {output_path}")

def fix_post(slug):
    """Regenerate a published post's HTML without reprocessing images."""
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    published_dir = os.path.join(blog_dir, "published")
    repo_root = os.path.dirname(blog_dir)

    # Find the post in the published folder
    published_path = None
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
                published_path = candidate
                break
        if published_path:
            break

    if not published_path:
        print(f"Published post not found: {slug}")
        sys.exit(1)

    # Load the published post to get the date
    with open(published_path, "r") as f:
        post = frontmatter.load(f)

    post_date = post.get("date")
    if not post_date:
        print(f"Post has no date: {slug}")
        sys.exit(1)

    # Parse date to build path
    if isinstance(post_date, str):
        from datetime import datetime
        date_obj = datetime.strptime(post_date, "%Y-%m-%d")
    else:
        from datetime import datetime
        date_obj = datetime.combine(post_date, datetime.min.time())

    date_path = date_obj.strftime("%Y/%m/%d")

    # Build HTML using the published .md (not the draft)
    build_published_html_from_path(published_path, slug, date_path, repo_root)

    print(f"Fixed: https://stephenoravec.com/blog/{date_path}/{slug}/")

def publish_post(slug):
    from datetime import date as date_module
    
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    published_dir = os.path.join(blog_dir, "published")
    repo_root = os.path.dirname(blog_dir)

    draft_path = os.path.join(drafts_dir, f"{slug}.md")

    if not os.path.exists(draft_path):
        print(f"Draft not found: {draft_path}")
        sys.exit(1)

    # Load the draft
    with open(draft_path, "r") as f:
        post = frontmatter.load(f)

    # Stamp today's date if not already set
    post_date = post.get("date")
    if not post_date:
        today = date_module.today()
        post["date"] = today.strftime("%Y-%m-%d")
        post_date = post["date"]

    # Parse the date to build the path
    if isinstance(post_date, str):
        from datetime import datetime
        date_obj = datetime.strptime(post_date, "%Y-%m-%d")
    else:
        from datetime import datetime
        date_obj = datetime.combine(post_date, datetime.min.time())

    date_path = date_obj.strftime("%Y/%m/%d")

    # Write the updated frontmatter back to the draft
    with open(draft_path, "w") as f:
        f.write(frontmatter.dumps(post))

    # Process images
    process_images(slug, date_path)

    # Build the HTML and write it to the live location
    build_published_html(slug, date_path, repo_root)

    # Move draft to published folder
    year = date_obj.strftime("%Y")
    month = date_obj.strftime("%m")
    published_path = os.path.join(published_dir, year, month, f"{slug}.md")
    os.makedirs(os.path.dirname(published_path), exist_ok=True)
    
    import shutil
    shutil.move(draft_path, published_path)
    print(f"Moved draft to: {published_path}")

    print(f"Published: https://stephenoravec.com/blog/{date_path}/{slug}/")

def build_published_html_from_path(md_path, slug, date_path, repo_root):
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(blog_dir, "templates")

    with open(md_path, "r") as f:
        post = frontmatter.load(f)

    title = post.get("title", "") or ""
    description_raw = post.get("description", "") or ""
    description_html = md_to_html(description_raw)
    description_plain = strip_markdown(description_raw)
    slug = post.get("slug", slug) or slug
    date = post.get("date", "") or ""
    image_name = post.get("image", "") or ""
    image_alt = post.get("image-alt", "") or ""

    display_date = ""
    if date:
        from datetime import datetime
        if isinstance(date, str):
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        else:
            date_obj = datetime.combine(date, datetime.min.time())
        display_date = date_obj.strftime("%B %-d, %Y")
        date = date_obj.strftime("%Y-%m-%d")

    image_url = ""
    image_url_400 = ""
    image_url_1000 = ""
    image_url_2000 = ""
    og_image_url = ""
    if image_name:
        base = f"https://storage.googleapis.com/stephenoravec-media/blog/{date_path}"
        image_url = f"{base}/{image_name}-1000.webp"
        image_url_400 = f"{base}/{image_name}-400.webp"
        image_url_1000 = f"{base}/{image_name}-1000.webp"
        image_url_2000 = f"{base}/{image_name}-2000.webp"
        og_image_url = f"{base}/{image_name}-og.webp"

    body_content = ""
    if post.content.strip():
        body_content = post.content

    template_path = os.path.join(templates_dir, "post.html")
    with open(template_path, "r") as f:
        template = f.read()

    html = template.replace("{{title}}", title)
    html = html.replace("{{description_html}}", description_html)
    html = html.replace("{{description_plain}}", description_plain)
    html = html.replace("{{slug}}", slug)
    html = html.replace("{{date}}", date)
    html = html.replace("{{date_path}}", date_path)
    html = html.replace("{{display_date}}", display_date)
    html = html.replace("{{image_url}}", image_url)
    html = html.replace("{{image_url_400}}", image_url_400)
    html = html.replace("{{image_url_1000}}", image_url_1000)
    html = html.replace("{{image_url_2000}}", image_url_2000)
    html = html.replace("{{image_alt}}", image_alt)
    html = html.replace("{{og_image_url}}", og_image_url)
    html = html.replace("{{body_content}}", body_content)

    output_dir = os.path.join(repo_root, "blog", date_path, slug)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built: {output_path}")

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
        print("Commands: new, preview, process-images, publish, fix")
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
    elif command == "process-images":
        if len(sys.argv) < 4:
            print('Usage: python blog.py process-images <slug> <date-path>')
            print('Example: python blog.py process-images spring-break-2026 2026/04/08')
            sys.exit(1)
        process_images(sys.argv[2], sys.argv[3])
    elif command == "publish":
        if len(sys.argv) < 3:
            print('Usage: python blog.py publish <slug>')
            sys.exit(1)
        publish_post(sys.argv[2])
    elif command == "fix":
        if len(sys.argv) < 3:
            print('Usage: python blog.py fix <slug>')
            sys.exit(1)
        fix_post(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()