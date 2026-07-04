"""Dependency access (yt-dlp and ffmpeg). Fully bundled — no runtime installs.

The Blender extensions platform forbids installing packages at runtime, so all
dependencies ship as bundled wheels declared in ``blender_manifest.toml``:

- ``yt_dlp`` (pure-python) → importable directly.
- ``imageio-ffmpeg`` (per-platform binary) → provides ffmpeg for merging.

As a development fallback (e.g. running from a symlinked source), the bundled
``.whl`` files are added to ``sys.path`` (wheels are importable via zipimport).

Does not import ``bpy``: only the standard library.
"""
import importlib
import os
import shutil
import sys

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
WHEELS_DIR = os.path.join(ADDON_DIR, "wheels")

_UNSET = object()
#: Cache of the ffmpeg path (avoids recomputing on every panel redraw).
_ffmpeg_path = _UNSET


def _candidate_paths():
    paths = []
    if os.path.isdir(WHEELS_DIR):
        paths.append(WHEELS_DIR)
        for name in sorted(os.listdir(WHEELS_DIR)):
            if name.endswith(".whl"):
                paths.append(os.path.join(WHEELS_DIR, name))
    return paths


def _add_local_paths():
    for path in _candidate_paths():
        if path not in sys.path:
            sys.path.insert(0, path)


def ensure_ytdlp():
    """Return the importable ``yt_dlp`` module, or ``None`` if not available."""
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        pass
    _add_local_paths()
    importlib.invalidate_caches()
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        return None


def ytdlp_version():
    module = ensure_ytdlp()
    if module is None:
        return None
    try:
        return module.version.__version__
    except AttributeError:
        return "?"


# --- ffmpeg (bundled via imageio-ffmpeg; system ffmpeg preferred if present) ---

def _imageio_ffmpeg_exe():
    """Path to imageio-ffmpeg's ffmpeg (bundled wheel), or ``None``."""
    _add_local_paths()
    importlib.invalidate_caches()
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - not available / no binary
        return None
    return path if path and os.path.isfile(path) else None


def find_ffmpeg(refresh=False):
    """Path to a usable ffmpeg (system first, then bundled), or ``None``. Cached."""
    global _ffmpeg_path
    if _ffmpeg_path is not _UNSET and not refresh:
        return _ffmpeg_path
    _ffmpeg_path = shutil.which("ffmpeg") or _imageio_ffmpeg_exe()
    return _ffmpeg_path
