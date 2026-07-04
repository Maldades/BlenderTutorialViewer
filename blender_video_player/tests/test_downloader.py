"""Tests for the pure download logic (yt-dlp mocked, no bpy)."""
import os

import pytest

import downloader


class TestBuildYdlOpts:
    def test_format_prefers_mp4_with_audio(self):
        opts = downloader.build_ydl_opts("/tmp/out")
        assert opts["format"] == (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        )

    def test_merge_output_format_is_mp4(self):
        opts = downloader.build_ydl_opts("/tmp/out")
        assert opts["merge_output_format"] == "mp4"

    def test_outtmpl_inside_out_dir(self):
        opts = downloader.build_ydl_opts("/tmp/out")
        tmpl = opts["outtmpl"]
        # outtmpl may be a str or dict {'default': str} depending on the yt-dlp version
        tmpl_str = tmpl["default"] if isinstance(tmpl, dict) else tmpl
        assert tmpl_str.startswith(os.path.join("/tmp/out", ""))

    def test_progress_hook_registered(self):
        hook = lambda d: None
        opts = downloader.build_ydl_opts("/tmp/out", progress_hook=hook)
        assert hook in opts["progress_hooks"]

    def test_no_progress_hook_by_default(self):
        opts = downloader.build_ydl_opts("/tmp/out")
        assert not opts.get("progress_hooks")

    def test_ffmpeg_location_set_when_given(self):
        opts = downloader.build_ydl_opts("/tmp/out", ffmpeg_location="/usr/bin/ffmpeg")
        assert opts["ffmpeg_location"] == "/usr/bin/ffmpeg"

    def test_ffmpeg_location_absent_by_default(self):
        opts = downloader.build_ydl_opts("/tmp/out")
        assert "ffmpeg_location" not in opts


class _FakeYDL:
    """Test double for yt_dlp.YoutubeDL (context manager)."""

    last_instance = None

    def __init__(self, opts):
        self.opts = opts
        self.extract_calls = []
        tmpl = opts["outtmpl"]
        tmpl_str = tmpl["default"] if isinstance(tmpl, dict) else tmpl
        self.out_dir = os.path.dirname(tmpl_str)
        _FakeYDL.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        self.extract_calls.append((url, download))
        return {
            "title": "My Tutorial",
            "id": "abc123",
            "fps": 30,
            "duration": 42,
            "ext": "mp4",
            "requested_downloads": [
                {"filepath": os.path.join(self.out_dir, "My Tutorial [abc123].mp4")}
            ],
        }

    def prepare_filename(self, info):
        return os.path.join("/tmp/out", f"{info['title']} [{info['id']}].{info['ext']}")


class TestDownload:
    def test_returns_filepath_and_metadata(self, monkeypatch):
        monkeypatch.setattr(downloader, "get_youtube_dl_class", lambda: _FakeYDL)
        result = downloader.download("https://youtu.be/abc123", "/tmp/out")
        assert result["filepath"].endswith("My Tutorial [abc123].mp4")
        assert result["title"] == "My Tutorial"
        assert result["fps"] == 30
        assert result["duration"] == 42

    def test_calls_extract_info_with_download_true(self, monkeypatch):
        monkeypatch.setattr(downloader, "get_youtube_dl_class", lambda: _FakeYDL)
        downloader.download("https://youtu.be/abc123", "/tmp/out")
        assert _FakeYDL.last_instance.extract_calls == [
            ("https://youtu.be/abc123", True)
        ]

    def test_download_passes_ffmpeg_location(self, monkeypatch):
        monkeypatch.setattr(downloader, "get_youtube_dl_class", lambda: _FakeYDL)
        downloader.download(
            "https://youtu.be/abc123", "/tmp/out", ffmpeg_location="/opt/ffmpeg"
        )
        assert _FakeYDL.last_instance.opts["ffmpeg_location"] == "/opt/ffmpeg"

    def test_missing_ytdlp_raises_dependency_error(self, monkeypatch):
        def _boom():
            raise downloader.DependencyError("yt-dlp unavailable")

        monkeypatch.setattr(downloader, "get_youtube_dl_class", _boom)
        with pytest.raises(downloader.DependencyError):
            downloader.download("https://youtu.be/abc123", "/tmp/out")

    def test_playlist_takes_first_entry(self, monkeypatch):
        class _PlaylistYDL(_FakeYDL):
            def extract_info(self, url, download=False):
                self.extract_calls.append((url, download))
                return {
                    "entries": [
                        {
                            "title": "First",
                            "id": "e1",
                            "fps": 25,
                            "ext": "mp4",
                            "requested_downloads": [
                                {"filepath": "/tmp/out/First [e1].mp4"}
                            ],
                        }
                    ]
                }

        monkeypatch.setattr(downloader, "get_youtube_dl_class", lambda: _PlaylistYDL)
        result = downloader.download("https://site/playlist", "/tmp/out")
        assert result["title"] == "First"
        assert result["filepath"].endswith("First [e1].mp4")
