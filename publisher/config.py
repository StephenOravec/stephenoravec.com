import json
import os


PUBLISHER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(PUBLISHER_DIR)
_config_path = os.path.join(REPO_ROOT, "bountiful.config.json")


def _load() -> dict:
    if not os.path.exists(_config_path):
        raise FileNotFoundError(
            f"bountiful.config.json not found at {_config_path}. "
            f"Site configuration is required."
        )
    with open(_config_path, "r") as f:
        return json.load(f)


_data = _load()

URL_SCHEME = _data.get("url_scheme", "collapsed")

_SUPPORTED_URL_SCHEMES = {"collapsed", "expanded"}
if URL_SCHEME not in _SUPPORTED_URL_SCHEMES:
    raise ValueError(
        f"bountiful.config.json: 'url_scheme' value '{URL_SCHEME}' is not supported. "
        f"Supported values: {sorted(_SUPPORTED_URL_SCHEMES)}."
    )


def post_output_subpath(slug: str, date_path: str) -> tuple[str, ...]:
    """Return the path segments from repo root to a post's directory.
    Always under blog/YYYY/MM/DD/slug/ regardless of url_scheme — the
    url_scheme only affects URL form, not filesystem layout.
    """
    return ("blog", *date_path.split("/"), slug)


def post_url_path(slug: str, date_path: str) -> str:
    """Return the post's URL path (starts with /, ends with /)."""
    if URL_SCHEME == "collapsed":
        return f"/{slug}/"
    if URL_SCHEME == "expanded":
        return f"/blog/{date_path}/{slug}/"
    raise NotImplementedError(f"URL scheme '{URL_SCHEME}' not implemented.")