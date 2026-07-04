"""Classification and validation of video sources.

Pure logic, no ``bpy`` or ``yt_dlp`` dependency, so it can run under pytest
outside Blender.
"""
import os

#: Recognized video container extensions for local files.
VIDEO_EXTENSIONS = frozenset(
    {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".mpg", ".mpeg", ".flv", ".wmv"}
)

_URL_PREFIXES = ("http://", "https://")


def classify_source(text):
    """Return ``"url"`` or ``"local"`` for the input string.

    Classification is purely syntactic: if it starts with ``http://`` or
    ``https://`` it is treated as a remote URL; otherwise as a local file path.
    It does not touch the filesystem.

    :raises ValueError: if the text is empty or whitespace only.
    """
    if text is None:
        raise ValueError("Source cannot be None")
    stripped = text.strip()
    if not stripped:
        raise ValueError("Source is empty")
    if stripped.lower().startswith(_URL_PREFIXES):
        return "url"
    return "local"


def is_probably_video_file(path):
    """Extension-based heuristic: does this look like a video file?"""
    _, ext = os.path.splitext(path)
    return ext.lower() in VIDEO_EXTENSIONS
