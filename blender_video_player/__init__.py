"""Video player (internet + local) inside Blender.

Blender 4.2+ extension (metadata in ``blender_manifest.toml``).
Registers a panel under VIEW_3D > N-panel > "Video" tab.
"""
import bpy

from . import operators, panel, player, properties

classes = (
    properties.BVPProperties,
    operators.BVP_OT_load_video,
    operators.BVP_OT_play_pause,
    operators.BVP_OT_unload_video,
    operators.BVP_OT_update_ytdlp,
    operators.BVP_OT_install_ffmpeg,
    operators.BVP_OT_open_external,
    panel.BVP_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bvp = bpy.props.PointerProperty(type=properties.BVPProperties)


def unregister():
    player.stop_autofit_monitor()
    if hasattr(bpy.types.Scene, "bvp"):
        del bpy.types.Scene.bvp
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
