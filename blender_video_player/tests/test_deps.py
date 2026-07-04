"""Tests for the deps logic (no bpy): ffmpeg detection."""
import deps


class TestFindFfmpeg:
    def test_uses_system_ffmpeg_first(self, monkeypatch):
        monkeypatch.setattr(
            deps.shutil, "which",
            lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
        )
        # Should not even consult imageio if the system has ffmpeg.
        monkeypatch.setattr(deps, "_imageio_ffmpeg_exe", lambda: "/should/not/be/used")
        assert deps.find_ffmpeg(refresh=True) == "/usr/bin/ffmpeg"

    def test_falls_back_to_imageio(self, monkeypatch):
        monkeypatch.setattr(deps.shutil, "which", lambda name: None)
        monkeypatch.setattr(deps, "_imageio_ffmpeg_exe", lambda: "/opt/imageio/ffmpeg")
        assert deps.find_ffmpeg(refresh=True) == "/opt/imageio/ffmpeg"

    def test_none_when_nothing_available(self, monkeypatch):
        monkeypatch.setattr(deps.shutil, "which", lambda name: None)
        monkeypatch.setattr(deps, "_imageio_ffmpeg_exe", lambda: None)
        assert deps.find_ffmpeg(refresh=True) is None

    def test_result_is_cached(self, monkeypatch):
        calls = {"n": 0}

        def fake_which(name):
            calls["n"] += 1
            return "/usr/bin/ffmpeg"

        monkeypatch.setattr(deps.shutil, "which", fake_which)
        deps.find_ffmpeg(refresh=True)
        n_after_first = calls["n"]
        deps.find_ffmpeg()  # no refresh: uses cache
        assert calls["n"] == n_after_first
