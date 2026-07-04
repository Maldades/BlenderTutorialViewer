"""Tests for the scene-state snapshot/restore in ``player``.

``player`` belongs to the bpy layer, but :func:`player.save_scene_state` and
:func:`player.restore_scene_state` only touch attributes of the scene they
receive, so they are testable with a duck-typed scene. A stub ``bpy`` module is
injected so ``player`` (which does ``import bpy`` at module level) can be
imported outside Blender; the stub has no attributes, guaranteeing these
functions do not secretly rely on ``bpy``.
"""
import sys
import types

sys.modules.setdefault("bpy", types.ModuleType("bpy"))

import player  # noqa: E402


class FakeRender:
    def __init__(self):
        self.fps = 24
        self.fps_base = 1.0


class FakeScene:
    """Duck-type of ``bpy.types.Scene``: attributes + id-properties."""

    def __init__(self):
        self.render = FakeRender()
        self.frame_start = 1
        self.frame_end = 250
        self.frame_current = 1
        self.sync_mode = "NONE"
        self._idprops = {}

    def get(self, key, default=None):
        return self._idprops.get(key, default)

    def __setitem__(self, key, value):
        self._idprops[key] = value

    def __delitem__(self, key):
        del self._idprops[key]


def _customized_scene():
    scene = FakeScene()
    scene.frame_start = 3
    scene.frame_end = 77
    scene.frame_current = 10
    scene.render.fps = 30
    scene.render.fps_base = 1.001
    scene.sync_mode = "FRAME_DROP"
    return scene


def _hijack(scene):
    """Simulate what ``add_video`` does to the scene."""
    scene.frame_start = 1
    scene.frame_end = 25789
    scene.frame_current = 1
    scene.render.fps = 25
    scene.render.fps_base = 1.0
    scene.sync_mode = "AUDIO_SYNC"


def test_save_scene_state_snapshots_timeline_and_sync():
    scene = _customized_scene()
    player.save_scene_state(scene)
    state = scene.get(player.SCENE_STATE_KEY)
    assert state == {
        "frame_start": 3,
        "frame_end": 77,
        "frame_current": 10,
        "fps": 30,
        "fps_base": 1.001,
        "sync_mode": "FRAME_DROP",
    }


def test_save_scene_state_keeps_the_first_snapshot():
    """Loading a second video must not overwrite the pre-video snapshot."""
    scene = _customized_scene()
    player.save_scene_state(scene)
    _hijack(scene)
    player.save_scene_state(scene)  # second load: must be a no-op
    assert scene.get(player.SCENE_STATE_KEY)["frame_end"] == 77


def test_restore_scene_state_restores_and_clears():
    scene = _customized_scene()
    player.save_scene_state(scene)
    _hijack(scene)

    assert player.restore_scene_state(scene) is True

    assert scene.frame_start == 3
    assert scene.frame_end == 77
    assert scene.frame_current == 10
    assert scene.render.fps == 30
    assert scene.render.fps_base == 1.001
    assert scene.sync_mode == "FRAME_DROP"
    # The snapshot is consumed: a second restore has nothing to do.
    assert scene.get(player.SCENE_STATE_KEY) is None
    assert player.restore_scene_state(scene) is False


def test_restore_scene_state_without_snapshot_is_a_noop():
    scene = _customized_scene()
    assert player.restore_scene_state(scene) is False
    assert scene.frame_end == 77
    assert scene.sync_mode == "FRAME_DROP"
