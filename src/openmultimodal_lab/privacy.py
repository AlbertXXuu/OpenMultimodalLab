"""Small privacy helpers for durable user-visible artifacts."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable


WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:[\\/]"
    r"|\\\\[^\\/\s'\";,]+[\\/][^\\/\s'\";,]+[\\/]?)"
    r"[^\s'\";,]+"
)
POSIX_USER_PATH = re.compile(
    r"(?i)/(?:home|users)/[^/\s'\"]+(?:/[^\s'\"]*)?"
)
POSIX_ABSOLUTE_PATH = re.compile(
    r"(?<![:/A-Za-z0-9])/(?!/)[^\s'\";,]+"
)


def portable_path_reference(value: str) -> str:
    """Keep a relative path but reduce any platform's absolute path."""

    windows_path = PureWindowsPath(value)
    if windows_path.is_absolute():
        return windows_path.name or "<absolute-path>"
    posix_path = PurePosixPath(value)
    if posix_path.is_absolute():
        return posix_path.name or "<absolute-path>"
    return value


def portable_media_references(media: Iterable[str]) -> tuple[str, ...]:
    """Keep relative media references but remove absolute local directories."""

    references: list[str] = []
    for item in media:
        references.append(portable_path_reference(item))
    return tuple(references)


def redact_local_paths(value: object) -> str:
    """Redact common absolute/user-home paths from durable error text."""

    text = str(value)
    home = Path.home()
    for candidate in {
        str(home),
        home.as_posix(),
        str(home).replace("\\", "/"),
    }:
        if candidate:
            text = text.replace(candidate, "<home>")
    text = POSIX_USER_PATH.sub("<home-path>", text)
    text = WINDOWS_ABSOLUTE_PATH.sub("<local-path>", text)
    return POSIX_ABSOLUTE_PATH.sub("<local-path>", text)
