"""
Character Importer for Cedarbrook
Run AFTER setup_world.py and AFTER placing your rigged FBX files in /models/

This script imports your Mixamo-rigged character models into the Blender world
and positions them at their home locations with proper scale and materials.
"""

import bpy
import os
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"

CHARACTER_SPAWN_POINTS = {
    "erin_maroni":     {"location": (-7, 10, 0.35),  "rotation": (0, 0, 0)},
    "lily_maroni":     {"location": (-9, 10, 0.35),  "rotation": (0, 0, 0)},
    "david_callahan":  {"location": (10, 10, 0.35),  "rotation": (0, 0, 0)},
    "isabel_callahan": {"location": (12, 10, 0.35),  "rotation": (0, 0, 0)},
}

SKIN_COLORS = {
    "erin_maroni":     (0.72, 0.52, 0.42),
    "lily_maroni":     (0.68, 0.48, 0.38),
    "david_callahan":  (0.82, 0.68, 0.58),
    "isabel_callahan": (0.65, 0.48, 0.35),
}


def import_character(character_id):
    fbx_path = MODELS_DIR / f"{character_id}.fbx"
    glb_path = MODELS_DIR / f"{character_id}.glb"

    if fbx_path.exists():
        bpy.ops.import_scene.fbx(filepath=str(fbx_path))
        print(f"[Import] Loaded {character_id}.fbx")
    elif glb_path.exists():
        bpy.ops.import_scene.gltf(filepath=str(glb_path))
        print(f"[Import] Loaded {character_id}.glb")
    else:
        print(f"[Import] WARNING: No model found for {character_id} in {MODELS_DIR}")
        print(f"         Expected: {fbx_path} or {glb_path}")
        return None

    # Get the newly imported armature/object
    imported = bpy.context.selected_objects
    root = next((o for o in imported if o.type == "ARMATURE"), None)
    if not root:
        root = imported[0] if imported else None
    if not root:
        return None

    root.name = character_id

    # Position
    spawn = CHARACTER_SPAWN_POINTS.get(character_id, {})
    root.location = spawn.get("location", (0, 0, 0))
    root.rotation_euler = spawn.get("rotation", (0, 0, 0))

    # Scale — Mixamo exports at 1 unit = 1cm, Blender default is 1 unit = 1m
    # Adjust if your character appears giant or tiny
    root.scale = (0.01, 0.01, 0.01)
    bpy.ops.object.transform_apply(scale=True)

    # Apply subsurface skin material to mesh children
    skin_color = SKIN_COLORS.get(character_id, (0.75, 0.58, 0.48))
    skin_mat = bpy.data.materials.new(f"{character_id}_Skin")
    skin_mat.use_nodes = True
    bsdf = skin_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*skin_color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
        bsdf.inputs["Subsurface Weight"].default_value = 0.3
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
        bsdf.inputs["Subsurface Scale"].default_value = 0.05

    for child in root.children:
        if child.type == "MESH" and "body" in child.name.lower() or "skin" in child.name.lower():
            if child.data.materials:
                child.data.materials[0] = skin_mat
            else:
                child.data.materials.append(skin_mat)

    print(f"[Import] {character_id} placed at {spawn.get('location')}")
    return root


def import_all():
    print("[Cedarbrook] Importing characters...")
    for cid in ["erin_maroni", "lily_maroni", "david_callahan", "isabel_callahan"]:
        import_character(cid)
    print("[Cedarbrook] Character import complete.")
    print("  Tip: If characters appear tiny or huge, adjust 'root.scale' in this script.")
    print("  Tip: Use Mixamo animations: download .bvh, import via File > Import > BVH")


import_all()
