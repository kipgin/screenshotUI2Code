"""Image utilities for encoding screenshots for vision API calls."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path


def encode_image_base64(path: str | Path) -> str:
    """Read an image file and return its base64-encoded content.

    Args:
        path: Absolute or relative path to the image file.

    Returns:
        Base64-encoded string (no data URI prefix).

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is not a recognised image type.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    media_type = get_image_media_type(path)
    if media_type is None:
        raise ValueError(f"Unsupported image type: {path.suffix}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_media_type(path: str | Path) -> str | None:
    """Return the MIME type of an image file, or None if not recognised.

    Args:
        path: Path to the image file.

    Returns:
        MIME type string (e.g. "image/png", "image/jpeg"), or None.
    """
    path = Path(path)
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("image/"):
        return mime
    # Fallback by extension
    ext_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    return ext_map.get(path.suffix.lower())


def build_data_uri(path: str | Path) -> str:
    """Build a data URI for embedding an image directly in HTML/CSS.

    Returns:
        String like ``data:image/png;base64,<data>``
    """
    path = Path(path)
    media_type = get_image_media_type(path) or "application/octet-stream"
    b64 = encode_image_base64(path)
    return f"data:{media_type};base64,{b64}"
