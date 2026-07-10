"""Reusable Riden option metadata."""

from __future__ import annotations

from .enums import Language
from .metadata import OptionMetadata

LANGUAGE_OPTIONS = (
    OptionMetadata("english", int(Language.ENGLISH), "English"),
    OptionMetadata("chinese", int(Language.CHINESE), "中文"),
)
