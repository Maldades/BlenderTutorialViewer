"""Mounting and playback of the video inside Blender.

Design (verified live in Blender 5.1):

- **Video**: the file is loaded as a ``MOVIE`` image datablock and shown in an
  **Image Editor**. That editor auto-fits the image and advances frames with the
  timeline (``image_user.use_auto_refresh``).
- **Audio**: a **sound strip** is added in the Video Sequence Editor, which plays
  during timeline playback (``screen.animation_play`` with
  ``sync_mode='AUDIO_SYNC'``), even when the VSE is not visible.

The VSE preview was ruled out because its 2D view cannot be reliably auto-fitted
from a script (it stays black).
"""
import bpy

#: Name prefix to identify elements created by this add-on.
STRIP_PREFIX = "BVP_"

#: Scene id-prop holding the timeline/sync snapshot taken before the first load.
SCENE_STATE_KEY = "bvp_prev_state"
#: Scene id-prop marking that the add-on split an area to create the player.
SPLIT_AREA_KEY = "bvp_split_area"

#: Interval (s) of the auto-fit monitor.
_AUTOFIT_INTERVAL = 0.25
#: Last known size of each area, keyed by ``area.as_pointer()``.
_autofit_last_sizes = {}


def _strips(se):
    """Strip collection, compatible with 5.x (``strips``) and 4.x (``sequences``).

    ``or`` can't be used: an empty collection is "falsy".
    """
    if hasattr(se, "strips"):
        return se.strips
    return se.sequences


def ensure_sequence_editor(scene):
    if scene.sequence_editor is None:
        scene.sequence_editor_create()
    return scene.sequence_editor


def save_scene_state(scene):
    """Snapshot the timeline/sync settings that :func:`add_video` hijacks.

    Only the FIRST load takes the snapshot: replacing the video keeps the
    original, pre-video state.
    """
    if scene.get(SCENE_STATE_KEY) is not None:
        return
    scene[SCENE_STATE_KEY] = {
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_current": scene.frame_current,
        "fps": scene.render.fps,
        "fps_base": scene.render.fps_base,
        "sync_mode": scene.sync_mode,
    }


def restore_scene_state(scene):
    """Restore (and consume) the snapshot taken by :func:`save_scene_state`.

    :returns: ``True`` if there was a snapshot to restore.
    """
    state = scene.get(SCENE_STATE_KEY)
    if state is None:
        return False
    # RNA clamps frame_start/frame_end against each other, so a single
    # assignment can be silently clamped; the start-end-start order is safe
    # for any combination of old and new ranges.
    scene.frame_start = int(state["frame_start"])
    scene.frame_end = int(state["frame_end"])
    scene.frame_start = int(state["frame_start"])
    scene.frame_current = int(state["frame_current"])
    scene.render.fps = int(state["fps"])
    scene.render.fps_base = float(state["fps_base"])
    scene.sync_mode = str(state["sync_mode"])
    del scene[SCENE_STATE_KEY]
    return True


def clear_video(scene):
    """Remove the sound strip, images and sounds created by this add-on."""
    se = scene.sequence_editor
    if se is not None:
        strips = _strips(se)
        for strip in list(strips):
            if strip.name.startswith(STRIP_PREFIX):
                strips.remove(strip)
    for image in list(bpy.data.images):
        if image.get("bvp_owned"):
            bpy.data.images.remove(image)
    for sound in list(bpy.data.sounds):
        if sound.get("bvp_owned") and sound.users == 0:
            bpy.data.sounds.remove(sound)


def add_video(scene, filepath, fps=None, replace=True):
    """Load ``filepath`` as a movie image + sound strip, and set up the scene.

    Returns ``(image, sound_or_None)``.
    """
    save_scene_state(scene)
    if replace:
        clear_video(scene)

    image = bpy.data.images.load(filepath, check_existing=False)
    if image.source != "MOVIE":
        # Force movie interpretation (in case the heuristic fails).
        try:
            image.source = "MOVIE"
        except (TypeError, ValueError):
            pass
    image["bvp_owned"] = True

    se = ensure_sequence_editor(scene)
    strips = _strips(se)
    sound = None
    try:
        sound = strips.new_sound(
            name=STRIP_PREFIX + "Audio", filepath=filepath, channel=1, frame_start=1
        )
    except (RuntimeError, TypeError):
        sound = None  # the file may have no audio track
    if sound is not None and sound.sound is not None:
        sound.sound["bvp_owned"] = True

    duration = image.frame_duration
    if not duration and sound is not None:
        duration = sound.frame_final_duration

    scene.frame_start = 1
    scene.frame_end = max(1, duration or 1)
    scene.frame_current = 1
    if fps:
        scene.render.fps = max(1, round(fps))
    scene.sync_mode = "AUDIO_SYNC"
    return image, sound


# --- Interface (requires a window; tested live) ---

def get_image_editor_area(screen):
    for area in screen.areas:
        if area.type == "IMAGE_EDITOR":
            return area
    return None


def open_player_area(context, image):
    """Open (or reuse) an Image Editor showing ``image``.

    If there is none, split the largest area. Returns the area, or ``None`` in
    background mode (no screen).
    """
    screen = getattr(context, "screen", None)
    if screen is None:
        return None

    area = get_image_editor_area(screen)
    if area is None:
        biggest = max(screen.areas, key=lambda a: a.width * a.height)
        before = set(screen.areas)
        with context.temp_override(area=biggest):
            bpy.ops.screen.area_split(direction="VERTICAL", factor=0.5)
        new_areas = [a for a in screen.areas if a not in before]
        area = new_areas[0] if new_areas else biggest
        area.type = "IMAGE_EDITOR"
        # Remember that WE created this area, so unload can close it.
        context.scene[SPLIT_AREA_KEY] = True

    space = area.spaces.active
    space.image = image
    image_user = space.image_user
    image_user.frame_duration = image.frame_duration or 1
    image_user.frame_start = 1
    image_user.frame_offset = 0
    image_user.use_auto_refresh = True
    area.tag_redraw()
    return area


def close_player_area(context):
    """Close the Image Editor(s) the add-on split off, if any. Best-effort.

    Only closes areas when :data:`SPLIT_AREA_KEY` says the add-on created one;
    a pre-existing Image Editor reused as player is left open.
    """
    scene = context.scene
    if scene.get(SPLIT_AREA_KEY) is None:
        return
    for win, area in list(_iter_target_areas()):
        try:
            with context.temp_override(window=win, area=area):
                bpy.ops.screen.area_close()
        except Exception:  # noqa: BLE001 - layout-dependent, best-effort
            pass
    del scene[SPLIT_AREA_KEY]


def has_video_state(scene):
    """Whether the add-on has anything to unload in ``scene``."""
    if scene.get(SCENE_STATE_KEY) is not None:
        return True
    se = scene.sequence_editor
    if se is not None and any(s.name.startswith(STRIP_PREFIX) for s in _strips(se)):
        return True
    return any(i.get("bvp_owned") for i in bpy.data.images)


def unload_video(context):
    """Stop playback, remove everything BVP created and restore the scene.

    :returns: ``True`` if the pre-video timeline/sync snapshot was restored.
    """
    scene = context.scene
    if is_playing(context):
        toggle_play(context)
    stop_autofit_monitor()
    close_player_area(context)
    clear_video(scene)
    return restore_scene_state(scene)


def is_playing(context):
    screen = getattr(context, "screen", None)
    return bool(screen and screen.is_animation_playing)


def toggle_play(context, area=None):
    """Toggle timeline playback (video + audio)."""
    screen = getattr(context, "screen", None)
    area = area or (get_image_editor_area(screen) if screen else None)
    if area is not None:
        with context.temp_override(area=area):
            bpy.ops.screen.animation_play()
    else:
        bpy.ops.screen.animation_play()


# --- Auto-fit on load and on area resize ---

def _iter_target_areas():
    """Yield ``(window, area)`` for each Image Editor showing our image."""
    wm = bpy.context.window_manager
    if wm is None:
        return
    for win in wm.windows:
        screen = win.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "IMAGE_EDITOR":
                continue
            space = area.spaces.active
            image = getattr(space, "image", None)
            if image is not None and image.get("bvp_owned"):
                yield win, area


def fit_view(area=None, window=None):
    """Fit the video in the add-on's Image Editor(s). Best-effort."""
    context = bpy.context
    if area is not None:
        pairs = [(window or getattr(context, "window", None), area)]
    else:
        pairs = list(_iter_target_areas())
    for win, target in pairs:
        if win is None or target is None:
            continue
        region = next((r for r in target.regions if r.type == "WINDOW"), None)
        if region is None:
            continue
        try:
            with context.temp_override(window=win, area=target, region=region):
                bpy.ops.image.view_all(fit_view=True)
        except Exception:  # noqa: BLE001 - best-effort
            pass


def _autofit_tick():
    """Poller: re-fit when the player area size changes."""
    found = False
    for win, area in _iter_target_areas():
        found = True
        key = area.as_pointer()
        size = (area.width, area.height)
        if _autofit_last_sizes.get(key) != size:
            _autofit_last_sizes[key] = size
            fit_view(area=area, window=win)
    if not found:
        _autofit_last_sizes.clear()
        return None  # no player: stop the monitor
    return _AUTOFIT_INTERVAL


def start_autofit_monitor():
    if not bpy.app.timers.is_registered(_autofit_tick):
        _autofit_last_sizes.clear()
        bpy.app.timers.register(_autofit_tick, first_interval=0.1)


def stop_autofit_monitor():
    if bpy.app.timers.is_registered(_autofit_tick):
        bpy.app.timers.unregister(_autofit_tick)
    _autofit_last_sizes.clear()
