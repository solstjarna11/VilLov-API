# app/utils/logging_helper.py

import base64
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_BASE64_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")

def summarize_ciphertext(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "present": False,
            "type": None,
            "length": 0,
            "preview": None,
            "base64_like": False,
        }

    if isinstance(value, bytes):
        preview = value[:12].hex()
        return {
            "present": True,
            "type": "bytes",
            "length": len(value),
            "preview": preview,
            "base64_like": False,
        }

    if isinstance(value, str):
        preview = value[:12]
        return {
            "present": True,
            "type": "str",
            "length": len(value),
            "preview": preview,
            "base64_like": bool(_BASE64_RE.fullmatch(value)),
        }

    return {
        "present": True,
        "type": type(value).__name__,
        "length": None,
        "preview": None,
        "base64_like": False,
    }