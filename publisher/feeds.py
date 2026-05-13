import os
import json
from datetime import datetime

import frontmatter

from config import URL_SCHEME, post_url_path


def build_routes(repo_root):
    """Generate staticwebapp.config.json with route rules:
    - Block publisher internals from public access
    - For each post, generate rewrite/redirect rules based on url_scheme
    - For each post's legacy_urls, generate redirects to the current canonical
    """
    publisher_dir = os.path.dirname(os.path.abspath(__file__))
    published_dir = os.path.join(publisher_dir, "published")

    routes = []

    # Baseline: block all publisher internals from public access
    routes.append({
        "route": "/publisher/*",
        "statusCode": 404,
    })

    if os.path.exists(published_dir):
        for year_dir in sorted(os.listdir(published_dir)):
            year_path = os.path.join(published_dir, year_dir)
            if not os.path.isdir(year_path):
                continue
            for month_dir in sorted(os.listdir(year_path)):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                for filename in sorted(os.listdir(month_path)):
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

                    date_path = date_obj.strftime("%Y/%m/%d")
                    slug = post.get("slug")
                    if not slug:
                        continue

                    canonical = post_url_path(slug, date_path)
                    physical = f"/blog/{date_path}/{slug}/"
                    physical_file = f"/blog/{date_path}/{slug}/index.html"

                    if URL_SCHEME == "collapsed":
                        # Rewrite the canonical URL to the physical file
                        routes.append({
                            "route": canonical,
                            "rewrite": physical_file,
                        })
                        # Redirect the physical URL to the canonical URL
                        routes.append({
                            "route": physical,
                            "redirect": canonical,
                            "statusCode": 301,
                        })
                    # expanded: canonical == physical, no extra routes needed

                    # Legacy URL redirects (skip self-references and already-handled paths)
                    legacy_urls = post.get("legacy_urls", []) or []
                    for legacy_url in legacy_urls:
                        if legacy_url == canonical:
                            continue
                        if URL_SCHEME == "collapsed" and legacy_url == physical:
                            continue  # already redirected above
                        routes.append({
                            "route": legacy_url,
                            "redirect": canonical,
                            "statusCode": 301,
                        })

    config = {
        "routes": routes,
        "responseOverrides": {
            "404": {
                "redirect": "/",
                "statusCode": 302,
            }
        }
    }

    config_path = os.path.join(repo_root, "staticwebapp.config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Wrote: {config_path}")
    print(f"Built routes: {len(routes)} rules")