"""Downloading remote videos with yt-dlp.

Pure logic, no ``bpy`` dependency. ``yt_dlp`` is imported lazily in
:func:`get_youtube_dl_class` so this module is importable (and testable with a
double) even when yt-dlp is not installed.
"""
import os

#: Preferred format: best mp4/m4a video+audio, falling back to a single file.
DEFAULT_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"


class DependencyError(RuntimeError):
    """yt-dlp is not available."""


def get_youtube_dl_class():
    """Return the ``yt_dlp.YoutubeDL`` class or raise :class:`DependencyError`.

    Kept in its own function so it can be replaced by a double in tests and so
    the import failure is explicit.
    """
    try:
        import yt_dlp  # noqa: WPS433 (lazy import on purpose)
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise DependencyError(
            "yt-dlp is not available. Click 'Update yt-dlp' in the panel."
        ) from exc
    return yt_dlp.YoutubeDL


def build_ydl_opts(out_dir, progress_hook=None, ffmpeg_location=None):
    """Build the options dict for ``YoutubeDL``.

    ``ffmpeg_location`` (optional): path to ffmpeg. Needed to merge separate
    video+audio (DASH, typical of YouTube 1080p+); on Windows ffmpeg is not
    bundled, so it is located and passed explicitly.
    """
    opts = {
        "format": DEFAULT_FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    return opts


def _first_entry(info):
    """If ``info`` is a playlist, return the first entry."""
    entries = info.get("entries") if isinstance(info, dict) else None
    if entries:
        return entries[0]
    return info


def _resolve_filepath(info, ydl):
    """Get the final path of the downloaded (already merged) file."""
    downloads = info.get("requested_downloads")
    if downloads:
        path = downloads[0].get("filepath")
        if path:
            return path
    # Fallback: rebuild the name from the template.
    return ydl.prepare_filename(info)


def download(url, out_dir, progress_hook=None, ffmpeg_location=None):
    """Download ``url`` into ``out_dir`` and return path + metadata.

    :returns: dict with ``filepath``, ``title``, ``fps`` and ``duration``.
    :raises DependencyError: if yt-dlp is not available.
    """
    youtube_dl_class = get_youtube_dl_class()
    opts = build_ydl_opts(out_dir, progress_hook, ffmpeg_location)
    with youtube_dl_class(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        info = _first_entry(info)
        filepath = _resolve_filepath(info, ydl)
    return {
        "filepath": filepath,
        "title": info.get("title"),
        "fps": info.get("fps"),
        "duration": info.get("duration"),
    }
