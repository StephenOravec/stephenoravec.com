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

def new_post(title):
    slug = slugify(title)
    
    blog_dir = os.path.dirname(os.path.abspath(__file__))
    drafts_dir = os.path.join(blog_dir, "drafts")
    staging_dir = os.path.join(blog_dir, "staging")

    draft_path = os.path.join(drafts_dir, f"{slug}.md")

    if os.path.exists(draft_path):
        print(f"Draft already exists: {draft_path}")
        sys.exit(1)

    post = frontmatter.Post("")
    post["title"] = title
    post["slug"] = slug
    post["date"] = ""
    post["time"] = ""
    post["image"] = ""
    post["image-alt"] = ""
    post["description"] = ""
    post["tags"] = []
    post["category"] = ""
    post["subcategory"] = ""
    post["source"] = "original"
    post["type"] = "short"
    post["origin"] = ""
    post["origin-date"] = ""
    post["import-date"] = ""

    with open(draft_path, "w") as f:
        f.write(frontmatter.dumps(post))

    staging_path = os.path.join(staging_dir, slug)
    os.makedirs(staging_path, exist_ok=True)

    print(f"Created draft: {draft_path}")
    print(f"Created staging folder: {staging_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python blog.py <command> [arguments]")
        print("Commands: new")
        sys.exit(1)

    command = sys.argv[1]

    if command == "new":
        if len(sys.argv) < 3:
            print('Usage: python blog.py new "Post Title"')
            sys.exit(1)
        new_post(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()