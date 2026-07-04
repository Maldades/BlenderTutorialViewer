"""Add-on properties, stored in ``Scene.bvp``."""
import bpy
from bpy.props import EnumProperty, FloatProperty, StringProperty


class BVPProperties(bpy.types.PropertyGroup):
    source_type: EnumProperty(
        name="Source",
        items=[
            ("URL", "Internet URL", "A YouTube or other site video, or a direct link"),
            ("LOCAL", "Local file", "A video file on your computer"),
        ],
        default="URL",
    )
    url: StringProperty(
        name="URL",
        description="Video link (YouTube, Vimeo, direct link, etc.)",
        default="",
    )
    local_path: StringProperty(
        name="File",
        description="Path to a local video file",
        subtype="FILE_PATH",
        default="",
    )
    status: StringProperty(name="Status", default="")
    progress: FloatProperty(
        name="Progress", default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE"
    )
    resolved_filepath: StringProperty(default="")
