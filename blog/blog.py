import sys

from posts import new_post, preview_post, publish_post, fix_post
from images import process_images
from feeds import build_index


def main():
    if len(sys.argv) < 2:
        print("Usage: python blog.py <command> [arguments]")
        print("Commands: new, preview, process-images, publish, fix, build-index")
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
    elif command == "build-index":
        import os
        blog_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(blog_dir)
        build_index(repo_root)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()