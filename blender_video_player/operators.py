"""Add-on operators: load/play, play/pause, update yt-dlp, install ffmpeg, browser."""
import os
import tempfile
import threading
import webbrowser

import bpy

from . import deps, downloader, player, source


def _defer_finalize():
    """Fit the video and start playback, after mounting (main thread)."""
    context = bpy.context
    screen = getattr(context, "screen", None)
    if screen is None:
        return None
    try:
        player.fit_view()
    except Exception:  # noqa: BLE001 - best-effort
        pass
    try:
        area = player.get_image_editor_area(screen)
        if area is not None and not screen.is_animation_playing:
            player.toggle_play(context, area)
    except Exception:  # noqa: BLE001 - autoplay is best-effort
        pass
    return None  # do not repeat the timer


def _mount_and_play(context, filepath, fps):
    props = context.scene.bvp
    props.resolved_filepath = filepath
    image, _sound = player.add_video(context.scene, filepath, fps=fps)
    player.open_player_area(context, image)
    # Monitor that re-fits when the player area is resized.
    player.start_autofit_monitor()
    # Defer the initial fit + play so we don't overlap modal operators.
    if not bpy.app.timers.is_registered(_defer_finalize):
        bpy.app.timers.register(_defer_finalize, first_interval=0.15)


class BVP_OT_load_video(bpy.types.Operator):
    bl_idname = "bvp.load_video"
    bl_label = "Load & Play"
    bl_description = "Load a local file, or download a URL, and open it in the player"

    _timer = None
    _thread = None
    _result = None
    _error = None
    _progress_pct = 0.0

    def execute(self, context):
        props = context.scene.bvp
        if props.source_type == "LOCAL":
            return self._load_local(context, props)
        return self._start_download(context, props)

    # --- local file: immediate ---
    def _load_local(self, context, props):
        path = bpy.path.abspath(props.local_path)
        if not path or not os.path.isfile(path):
            self.report({"ERROR"}, "Local file does not exist")
            return {"CANCELLED"}
        if not source.is_probably_video_file(path):
            self.report({"WARNING"}, "File doesn't look like a video; trying anyway")
        _mount_and_play(context, path, fps=None)
        props.status = "Playing (local file)"
        return {"FINISHED"}

    # --- URL: threaded download + modal operator ---
    def _start_download(self, context, props):
        url = props.url.strip()
        try:
            if source.classify_source(url) != "url":
                self.report({"ERROR"}, "That doesn't look like a URL (use http:// or https://)")
                return {"CANCELLED"}
        except ValueError:
            self.report({"ERROR"}, "Enter a URL")
            return {"CANCELLED"}

        if deps.ensure_ytdlp() is None:
            self.report(
                {"ERROR"}, "yt-dlp unavailable. Click 'Update yt-dlp'."
            )
            return {"CANCELLED"}

        if props.keep_local and props.dest_dir:
            out_dir = bpy.path.abspath(props.dest_dir)
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as exc:
                self.report({"ERROR"}, f"Invalid destination folder: {exc}")
                return {"CANCELLED"}
        else:
            out_dir = tempfile.mkdtemp(prefix="bvp_")

        self._result = None
        self._error = None
        self._progress_pct = 0.0
        props.progress = 0.0
        props.status = "Downloading…"

        def hook(data):
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                got = data.get("downloaded_bytes", 0)
                if total:
                    self._progress_pct = min(99.0, got / total * 100.0)
            elif status == "finished":
                self._progress_pct = 100.0

        ffmpeg = deps.find_ffmpeg()

        def worker():
            try:
                self._result = downloader.download(
                    url, out_dir, progress_hook=hook, ffmpeg_location=ffmpeg
                )
            except Exception as exc:  # noqa: BLE001 - reported in the modal
                self._error = str(exc)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
        self._timer = context.window_manager.event_timer_add(0.3, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        props = context.scene.bvp
        props.progress = self._progress_pct
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        if self._thread.is_alive():
            return {"PASS_THROUGH"}

        # Download finished.
        self._finish(context)
        if self._error:
            props.status = f"Error: {self._error}"
            self.report({"ERROR"}, self._error)
            return {"CANCELLED"}

        result = self._result or {}
        path = result.get("filepath")
        if not path or not os.path.isfile(path):
            props.status = "Error: downloaded file not found"
            self.report({"ERROR"}, "Downloaded file not found")
            return {"CANCELLED"}

        _mount_and_play(context, path, fps=result.get("fps"))
        title = result.get("title") or os.path.basename(path)
        props.status = f"Playing: {title}"
        props.progress = 0.0
        return {"FINISHED"}

    def _finish(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def cancel(self, context):
        self._finish(context)


class BVP_OT_play_pause(bpy.types.Operator):
    bl_idname = "bvp.play_pause"
    bl_label = "Play / Pause"
    bl_description = "Toggle video playback (with audio)"

    def execute(self, context):
        area = player.get_image_editor_area(context.screen)
        player.toggle_play(context, area)
        return {"FINISHED"}


class BVP_OT_unload_video(bpy.types.Operator):
    bl_idname = "bvp.unload_video"
    bl_label = "Unload Video"
    bl_description = (
        "Stop playback, remove the video and its audio strip from the scene, "
        "and restore the timeline and sync settings from before the load"
    )

    @classmethod
    def poll(cls, context):
        return player.has_video_state(context.scene)

    def execute(self, context):
        # An autoplay may still be pending right after a load.
        if bpy.app.timers.is_registered(_defer_finalize):
            bpy.app.timers.unregister(_defer_finalize)
        restored = player.unload_video(context)
        props = context.scene.bvp
        props.status = "Video unloaded" + (" (timeline restored)" if restored else "")
        self.report({"INFO"}, props.status)
        return {"FINISHED"}


class BVP_OT_update_ytdlp(bpy.types.Operator):
    bl_idname = "bvp.update_ytdlp"
    bl_label = "Update yt-dlp"
    bl_description = "Download the latest version of yt-dlp (requires internet)"

    def execute(self, context):
        props = context.scene.bvp
        props.status = "Updating yt-dlp…"
        ok, message = deps.update_ytdlp()
        props.status = message
        if ok:
            self.report({"INFO"}, message)
            return {"FINISHED"}
        self.report({"ERROR"}, message)
        return {"CANCELLED"}


class BVP_OT_install_ffmpeg(bpy.types.Operator):
    bl_idname = "bvp.install_ffmpeg"
    bl_label = "Install ffmpeg"
    bl_description = (
        "Download ffmpeg (imageio-ffmpeg) so video and audio from YouTube can be "
        "merged in high quality. Requires internet"
    )

    def execute(self, context):
        props = context.scene.bvp
        props.status = "Installing ffmpeg…"
        ok, message = deps.install_ffmpeg()
        props.status = message
        if ok:
            self.report({"INFO"}, message)
            return {"FINISHED"}
        self.report({"ERROR"}, message)
        return {"CANCELLED"}


class BVP_OT_open_external(bpy.types.Operator):
    bl_idname = "bvp.open_external"
    bl_label = "Open in Browser"
    bl_description = "Open the URL in the external browser (fallback)"

    def execute(self, context):
        url = context.scene.bvp.url.strip()
        if not url:
            self.report({"ERROR"}, "No URL")
            return {"CANCELLED"}
        webbrowser.open(url)
        return {"FINISHED"}
