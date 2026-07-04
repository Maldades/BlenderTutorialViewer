"""Tests for the pure source classification/validation logic (no bpy)."""
import pytest

import source


class TestClassifySource:
    def test_https_url_is_url(self):
        assert source.classify_source("https://www.youtube.com/watch?v=abc") == "url"

    def test_http_url_is_url(self):
        assert source.classify_source("http://vimeo.com/123") == "url"

    def test_arbitrary_domain_is_url(self):
        # "internet in general": not restricted to youtube
        assert source.classify_source("https://example.org/media/video.mp4") == "url"

    def test_absolute_path_is_local(self):
        assert source.classify_source("/home/user/tutorial.mp4") == "local"

    def test_relative_path_is_local(self):
        assert source.classify_source("videos/clip.mkv") == "local"

    def test_windows_path_is_local(self):
        assert source.classify_source(r"C:\Users\me\clip.mp4") == "local"

    def test_strips_whitespace(self):
        assert source.classify_source("   https://x.com/v   ") == "url"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            source.classify_source("")

    def test_blank_raises(self):
        with pytest.raises(ValueError):
            source.classify_source("    ")


class TestIsProbablyVideoFile:
    @pytest.mark.parametrize("name", ["a.mp4", "a.mkv", "a.mov", "a.webm", "a.avi"])
    def test_known_video_extensions(self, name):
        assert source.is_probably_video_file(name) is True

    def test_case_insensitive(self):
        assert source.is_probably_video_file("CLIP.MP4") is True

    def test_non_video_extension(self):
        assert source.is_probably_video_file("notes.txt") is False

    def test_no_extension(self):
        assert source.is_probably_video_file("README") is False
