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
    html = html.replace("{{description}}", description)
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
        print("Commands: new, preview, process-images")
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
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()