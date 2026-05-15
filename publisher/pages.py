"""Static page metadata for sitemap generation.

Edit this list when you add or remove top-level site sections.

Each entry is a dict with three keys:
  - url:      Path on the site (e.g. "/cablepunk")
  - lastmod:  Last-modified date in ISO 8601 format ("YYYY-MM-DD")
  - priority: Sitemap priority value from "0.0" to "1.0" as a string
"""


PAGES: list[dict[str, str]] = [
    {"url": "/", "lastmod": "2026-02-05", "priority": "1.0"},
    {"url": "/cablepunk", "lastmod": "2026-05-02", "priority": "0.8"},
    {"url": "/books", "lastmod": "2026-02-05", "priority": "0.8"},
    {"url": "/profiles", "lastmod": "2026-02-05", "priority": "0.8"},
]