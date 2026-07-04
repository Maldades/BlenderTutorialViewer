"""pytest configuration.

Inserts the add-on directory into sys.path so the pure-logic modules
(`source`, `downloader`, `deps`) can be imported directly, without running the
package ``__init__.py`` (which imports ``bpy`` and only exists inside Blender).
"""
import os
import sys

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ADDON_DIR not in sys.path:
    sys.path.insert(0, ADDON_DIR)

# The integration test imports ``bpy`` and only runs via
# ``blender --background --python``; pytest (without Blender) must ignore it.
collect_ignore = ["test_player_integration.py"]
