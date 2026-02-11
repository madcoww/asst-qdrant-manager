"""
Author : Wonjun Kim
e-mail : wonjun.kim@seculayer.com
Powered by Seculayer © 2025 AI Team, R&D Center.
"""
from __future__ import annotations

import re

from fastapi import HTTPException


def validate_collection_name(name: str) -> str:
    """Validate collection name for security."""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail='Collection name cannot be empty')

    if len(name) > 255:
        raise HTTPException(status_code=400, detail='Collection name too long (max 255)')

    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise HTTPException(
            status_code=400,
            detail='Invalid collection name. Use only letters, numbers, hyphens, and underscores',
        )

    return name
