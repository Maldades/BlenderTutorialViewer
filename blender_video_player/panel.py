"""Add-on panel in the 3D viewport N-panel ('Video' tab)."""
import bpy

from . import deps


class BVP_PT_panel(bpy.types.Panel):
    bl_label = "Video Player"
    bl_idname = "BVP_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Video"

    def draw(self, context):
        layout = self.layout
        props = context.scene.bvp

        layout.prop(props, "source_type", expand=True)

        if props.source_type == "URL":
            layout.prop(props, "url", text="", icon="URL")
            layout.prop(props, "keep_local")
            if props.keep_local:
                layout.prop(props, "dest_dir", text="")
        else:
            layout.prop(props, "local_path", text="")

        layout.operator("bvp.load_video", icon="IMPORT")

        if 0.0 < props.progress < 100.0:
            layout.label(text=f"Downloading… {props.progress:.0f}%", icon="SORTTIME")
        elif props.status:
            layout.label(text=props.status, icon="INFO")

        layout.separator()
        row = layout.row(align=True)
        row.operator("bvp.play_pause", icon="PLAY")
        row.operator("bvp.unload_video", icon="TRASH", text="")

        col = layout.column(align=True)
        col.separator()
        version = deps.ytdlp_version()
        col.operator("bvp.update_ytdlp", icon="FILE_REFRESH")
        col.label(text=f"yt-dlp: {version or 'not installed'}")
        if props.source_type == "URL":
            col.operator("bvp.open_external", icon="WORLD")

            if deps.find_ffmpeg() is None:
                ff_box = layout.box()
                ff_box.label(text="ffmpeg not found", icon="ERROR")
                ff_box.label(text="Without it, quality may be limited.")
                ff_box.operator("bvp.install_ffmpeg", icon="IMPORT")

        box = layout.box()
        box.scale_y = 0.8
        box.label(text="Respect ToS and copyright.", icon="ERROR")
        box.label(text="Use your own, CC, or public-domain content.")
