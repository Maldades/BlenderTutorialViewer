"""Integration test for the player mount.

Runs INSIDE Blender:

    blender --background --python tests/test_player_integration.py

Generates an offline test clip with ffmpeg (video + audio), mounts it with
``player.add_video`` and checks that the movie image and sound strip are created
and that the scene is set up for synchronized playback.
"""
import os
import subprocess
import sys
import tempfile

import bpy

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ADDON_DIR not in sys.path:
    sys.path.insert(0, ADDON_DIR)

import player  # noqa: E402


def make_sample(path):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440",
            "-t", "2", "-pix_fmt", "yuv420p",
            path,
        ],
        check=True,
        capture_output=True,
    )


def main():
    tmp = tempfile.mkdtemp()
    sample = os.path.join(tmp, "sample.mp4")
    make_sample(sample)
    assert os.path.isfile(sample), "ffmpeg did not generate the test clip"

    scene = bpy.context.scene
    image, sound = player.add_video(scene, sample, fps=25)

    # Video loaded as a movie image.
    assert image is not None, "image was not created"
    assert image.source == "MOVIE", f"source={image.source}"
    assert image.get("bvp_owned"), "image was not tagged as owned"

    # Audio as a sound strip in the VSE.
    assert scene.sequence_editor is not None, "sequence_editor was not created"
    sound_strips = [s for s in scene.sequence_editor.strips if s.type == "SOUND"]
    assert len(sound_strips) == 1, f"expected 1 sound strip, got {len(sound_strips)}"
    assert sound is not None, "audio strip was not created"

    # Scene set up.
    assert scene.frame_end > 1, f"frame_end not set: {scene.frame_end}"
    assert scene.sync_mode == "AUDIO_SYNC", f"sync_mode={scene.sync_mode}"
    assert scene.render.fps == 25, f"fps={scene.render.fps}"

    # clear_video removes image + sound.
    player.clear_video(scene)
    assert len([s for s in scene.sequence_editor.strips if s.type == "SOUND"]) == 0, \
        "clear_video did not remove the sound"
    assert not any(i.get("bvp_owned") for i in bpy.data.images), \
        "clear_video did not remove the image"

    # --- Unload: restores the scene state prior to loading ---

    # Custom pre-video state, distinct from both defaults and the video's.
    player.restore_scene_state(scene)  # drop any leftover snapshot
    scene.frame_start = 3
    scene.frame_end = 77
    scene.frame_current = 5
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    scene.sync_mode = "NONE"

    image, sound = player.add_video(scene, sample, fps=25)
    assert scene.get(player.SCENE_STATE_KEY) is not None, "state was not saved on load"
    assert scene.frame_end == image.frame_duration, "timeline was not hijacked by the video"
    assert scene.sync_mode == "AUDIO_SYNC"
    if sound is not None:
        assert sound.sound.get("bvp_owned"), "sound datablock was not tagged as owned"

    # A second load (replace) must keep the ORIGINAL snapshot.
    player.add_video(scene, sample, fps=25)
    assert scene.get(player.SCENE_STATE_KEY)["frame_end"] == 77, \
        "second load overwrote the pre-video snapshot"

    restored = player.unload_video(bpy.context)
    assert restored is True, "unload_video did not restore the saved state"
    assert scene.frame_start == 3, f"frame_start={scene.frame_start}"
    assert scene.frame_end == 77, f"frame_end={scene.frame_end}"
    assert scene.frame_current == 5, f"frame_current={scene.frame_current}"
    assert scene.render.fps == 24, f"fps={scene.render.fps}"
    assert scene.sync_mode == "NONE", f"sync_mode={scene.sync_mode}"
    assert scene.get(player.SCENE_STATE_KEY) is None, "snapshot was not consumed"
    assert not any(i.get("bvp_owned") for i in bpy.data.images), \
        "unload_video did not remove the image"
    assert not any(s.name.startswith(player.STRIP_PREFIX)
                   for s in scene.sequence_editor.strips), \
        "unload_video did not remove the strip"
    assert not any(s.get("bvp_owned") for s in bpy.data.sounds), \
        "unload_video did not remove the orphan sound datablock"

    # Unload with nothing loaded: harmless no-op.
    assert player.unload_video(bpy.context) is False

    print("PLAYER_INTEGRATION_OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"PLAYER_INTEGRATION_FAIL: {exc}")
        sys.exit(1)
    sys.exit(0)
