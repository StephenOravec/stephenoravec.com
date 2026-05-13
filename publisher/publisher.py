import os
import sys

from posts import new_post, preview_post, publish_post, fix_post, validate_all, rebuild
from images import process_images
from blog import build_index
from feeds import build_routes, build_sitemap


def main():
    if len(sys.argv) < 2:
        print("Usage: python publisher.py <command> [arguments]")
        print("Commands: new, preview, process-images, publish, fix, build-index, validate, build-routes, build-sitemap, rebuild")
        sys.exit(1)

    command = sys.argv[1]

    if command == "new":
        if len(sys.argv) < 3:
            print('Usage: python publisher.py new "Post Title"')
            sys.exit(1)
        new_post(sys.argv[2])
    elif command == "preview":
        if len(sys.argv) < 3:
            print('Usage: python publisher.py preview <slug>')
            sys.exit(1)
        preview_post(sys.argv[2])
    elif command == "process-images":
        if len(sys.argv) < 4:
            print('Usage: python publisher.py process-images <slug> <date-path>')
            print('Example: python publisher.py process-images spring-break-2026 2026/04/08')
            sys.exit(1)
        process_images(sys.argv[2], sys.argv[3])
    elif command == "publish":
        if len(sys.argv) < 3:
            print('Usage: python publisher.py publish <slug>')
            sys.exit(1)
        publish_post(sys.argv[2])
    elif command == "fix":
        if len(sys.argv) < 3:
            print('Usage: python publisher.py fix <slug>')
            sys.exit(1)
        fix_post(sys.argv[2])
    elif command == "rebuild":
        rebuild()
    elif command == "build-index":
        blog_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(blog_dir)
        build_index(repo_root)
    elif command == "build-routes":
        publisher_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(publisher_dir)
        from feeds import build_routes
        build_routes(repo_root)
    elif command == "build-sitemap":
        publisher_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(publisher_dir)
        build_sitemap(repo_root)
    elif command == "validate":
        issues = validate_all()
        if not issues:
            print("All posts have valid slugs.")
        else:
            print(f"Found {len(issues)} issue(s):")
            for path, issue in issues:
                print(f"  {path}: {issue}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()