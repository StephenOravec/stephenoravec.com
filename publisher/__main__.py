"""CLI entry point for the blog publisher.

Dispatches to functions in posts.py, blog.py, feeds.py, and images.py based
on the command argument. Run with `python -m publisher <command> [arguments]`
from the repo root to see all available commands.
"""


import sys

from .blog import build_index
from .config import REPO_ROOT
from .feeds import build_routes, build_sitemap
from .images import process_images
from .posts import new_post, preview_post, publish_post, fix_post, validate_all, rebuild


def main() -> None:
    """Parse command-line arguments and dispatch to the appropriate handler."""
    if len(sys.argv) < 2:
        print("Usage: python -m publisher <command> [arguments]")
        print("Commands:")
        print("  Lifecycle:        new, preview, publish, fix")
        print("  Image processing: process-images")
        print("  Orchestration:    rebuild")
        print("  Builders:         build-index, build-routes, build-sitemap")
        print("  Validation:       validate")
        sys.exit(1)

    command = sys.argv[1]

    if command == "new":
        if len(sys.argv) < 3:
            print('Usage: python -m publisher new "Post Title"')
            sys.exit(1)
        new_post(sys.argv[2])
    elif command == "preview":
        if len(sys.argv) < 3:
            print('Usage: python -m publisher preview <slug>')
            sys.exit(1)
        preview_post(sys.argv[2])    
    elif command == "publish":
        if len(sys.argv) < 3:
            print('Usage: python -m publisher publish <slug>')
            sys.exit(1)
        publish_post(sys.argv[2])
    elif command == "fix":
        if len(sys.argv) < 3:
            print('Usage: python -m publisher fix <slug>')
            sys.exit(1)
        fix_post(sys.argv[2])
    elif command == "process-images":
        if len(sys.argv) < 4:
            print('Usage: python -m publisher process-images <slug> <date-path>')
            print('Example: python -m publisher process-images spring-break-2026 2026/04/08')
            sys.exit(1)
        process_images(sys.argv[2], sys.argv[3])
    elif command == "rebuild":
        rebuild()
    elif command == "build-index":
        build_index(REPO_ROOT)
    elif command == "build-routes":
        build_routes(REPO_ROOT)
    elif command == "build-sitemap":
        build_sitemap(REPO_ROOT)
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