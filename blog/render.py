import os
import re
from datetime import datetime


def md_to_html(text):
    """Convert basic Markdown formatting to HTML for rich-text contexts."""
    if not text:
        return ""
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text


def strip_markdown(text):
    """Strip Markdown formatting for plain-text contexts like meta tags."""
    if not text:
        return ""
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return text


def inline_format(text):
    """Apply inline Markdown formatting: links, bold, italics."""
    if not text:
        return ""

    def link_replacer(match):
        link_text = match.group(1)
        url = match.group(2)
        if url.startswith("http://") or url.startswith("https://"):
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{link_text}</a>'
        else:
            return f'<a href="{url}">{link_text}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link_replacer, text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return text


def render_figure(image_name, alt_text, caption_text, date_path):
    """Render a body image as a <figure> with responsive srcset and optional caption."""
    if not image_name:
        return ""
    base = f"https://storage.googleapis.com/stephenoravec-media/blog/{date_path}"
    img_html = (
        f'<img src="{base}/{image_name}-1000.webp" '
        f'srcset="{base}/{image_name}-400.webp 400w, '
        f'{base}/{image_name}-1000.webp 1000w, '
        f'{base}/{image_name}-2000.webp 2000w" '
        f'sizes="(max-width: 768px) 100vw, 1000px" '
        f'alt="{alt_text}" '
        f'loading="lazy">'
    )
    if caption_text:
        return f'<figure>{img_html}<figcaption>{caption_text}</figcaption></figure>'
    else:
        return f'<figure>{img_html}</figure>'


def parse_body(text, date_path):
    """Parse Markdown body content into HTML, including custom image syntax."""
    if not text or not text.strip():
        return ""

    lines = text.split("\n")
    blocks = []
    current_block = []

    for line in lines:
        if line.strip() == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    html_parts = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        first_line = block[0].strip()

        if first_line.startswith("::image["):
            image_name = first_line[len("::image["):-1] if first_line.endswith("]") else ""
            alt_text = ""
            caption_text = ""
            for line in block[1:]:
                stripped = line.strip()
                if stripped.startswith("::alt[") and stripped.endswith("]"):
                    alt_text = stripped[len("::alt["):-1]
                elif stripped.startswith("::caption[") and stripped.endswith("]"):
                    caption_text = stripped[len("::caption["):-1]
            html_parts.append(render_figure(image_name, alt_text, caption_text, date_path))
            i += 1
            continue

        if first_line.startswith("#"):
            level = 0
            while level < len(first_line) and first_line[level] == "#":
                level += 1
            if 1 <= level <= 3:
                heading_text = first_line[level:].strip()
                heading_html = inline_format(heading_text)
                html_parts.append(f"<h{level}>{heading_html}</h{level}>")
                i += 1
                continue

        paragraph_text = " ".join(block).strip()
        paragraph_html = inline_format(paragraph_text)
        html_parts.append(f"<p>{paragraph_html}</p>")
        i += 1

    return "\n".join(html_parts)


def render_post(post, slug_default, date_path, templates_dir):
    """Render a post's HTML from a frontmatter Post object.

    Single source of truth for HTML generation. Used by preview, publish,
    and fix lifecycle commands. The slug from frontmatter takes precedence
    over slug_default when present.
    """
    title = post.get("title", "") or ""
    description_raw = post.get("description", "") or ""
    description_html = md_to_html(description_raw)
    description_plain = strip_markdown(description_raw)
    slug = post.get("slug", slug_default) or slug_default
    date = post.get("date", "") or ""
    image_name = post.get("image", "") or ""
    image_alt = post.get("image-alt", "") or ""

    display_date = ""
    if date:
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

    body_content = parse_body(post.content, date_path) if date_path else ""

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

    return html


def write_post_html(html, output_dir):
    """Write rendered HTML to output_dir/index.html. Returns the full output path."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w") as f:
        f.write(html)
    return output_path