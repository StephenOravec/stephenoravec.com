import sys
import os
import re
import frontmatter

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