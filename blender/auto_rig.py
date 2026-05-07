"""
Cedarbrook Auto-Rigger
Handles Meshy.ai FBX exports with full PBR texture sets.
Imports the mesh, applies all texture maps, and auto-rigs with Rigify.

HOW TO RUN:
  Option A — Blender Scripting tab:
    1. Open Blender
    2. Go to Scripting workspace (top tab)
    3. Click Open → select this file
    4. Edit the CHARACTER_CONFIGS list below with your folder paths
    5. Click Run Script

  Option B — Claude Desktop + Blender MCP:
    Paste the full contents into Claude Desktop and say:
    "Run this script in Blender"

AFTER RUNNING:
  - Each character saved as /models/<name>.blend
  - Open the .blend, go to Properties > Object Data > Rigify
  - Click "Generate Rig" once (if not already generated)
  - Done — character is rigged and ready for Mixamo animations via BVH import
"""

import bpy
import os
import math
from pathlib import Path

# ─── CONFIGURE YOUR CHARACTERS HERE ─────────────────────────────────────────

CHARACTER_CONFIGS = [
    {
        "name":   "erin_maroni",
        "folder": "/Users/joshuawilson/Downloads/Erin_fbx",
    },
    {
        "name":   "david_callahan",
        "folder": "/Users/joshuawilson/Downloads/Pastor.fbx",
    },
    {
        "name":   "isabel_callahan",
        "folder": "/Users/joshuawilson/Downloads/Pastor's wife_fbx",
    },
    {
        "name":   "lily_maroni",
        "folder": "/Users/joshuawilson/Downloads/Lily_fbx",
    },
]

OUTPUT_DIR = "/Users/joshuawilson/Downloads/cedarbrook_models"

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def find_fbx(folder):
    for f in Path(folder).iterdir():
        if f.suffix.lower() == ".fbx":
            return str(f)
    return None


def find_texture(folder, map_type):
    """
    Meshy naming: basename_texture.png (diffuse), basename_texture_normal.png, etc.
    map_type: "diffuse" | "normal" | "roughness" | "metallic" | "emission"
    """
    suffixes = {
        "diffuse":   "_texture.png",
        "normal":    "_texture_normal.png",
        "roughness": "_texture_roughness.png",
        "metallic":  "_texture_metallic.png",
        "emission":  "_texture_emission.png",
    }
    target = suffixes.get(map_type, "")
    for f in sorted(Path(folder).iterdir()):
        name = f.name
        if map_type == "diffuse":
            # Must end with _texture.png but NOT _texture_<anything>.png
            if name.endswith("_texture.png") and not any(
                name.endswith(f"_texture_{t}.png")
                for t in ["normal", "roughness", "metallic", "emission"]
            ):
                return str(f)
        else:
            if name.endswith(target):
                return str(f)
    return None


def load_image(path, color_space="sRGB"):
    if not path or not Path(path).exists():
        return None
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = color_space
    return img


def enable_rigify():
    if "rigify" not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module="rigify")


# ─── CORE ────────────────────────────────────────────────────────────────────

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.armatures, bpy.data.cameras]:
        for item in block:
            block.remove(item)


def import_fbx(path):
    bpy.ops.import_scene.fbx(
        filepath=path,
        use_custom_normals=True,
        use_image_search=True,
        automatic_bone_orientation=True,
    )
    meshes   = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    armatures = [o for o in bpy.context.selected_objects if o.type == "ARMATURE"]
    return meshes, armatures


def build_pbr_material(name, folder):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Principled BSDF
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)

    # Output
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (550, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # UV Map node (shared)
    uv = nodes.new("ShaderNodeTexCoord")
    uv.location = (-900, 0)

    def tex_node(map_type, loc, color_space="Non-Color"):
        path = find_texture(folder, map_type)
        img = load_image(path, color_space)
        if img is None:
            return None
        n = nodes.new("ShaderNodeTexImage")
        n.image = img
        n.location = loc
        n.label = map_type.capitalize()
        links.new(uv.outputs["UV"], n.inputs["Vector"])
        return n

    # Diffuse / Albedo (sRGB)
    diff = tex_node("diffuse", (-500, 400), "sRGB")
    if diff:
        links.new(diff.outputs["Color"], bsdf.inputs["Base Color"])

    # Normal map
    norm_tex = tex_node("normal", (-500, 0))
    if norm_tex:
        nm = nodes.new("ShaderNodeNormalMap")
        nm.location = (-100, -100)
        nm.inputs["Strength"].default_value = 1.0
        links.new(norm_tex.outputs["Color"], nm.inputs["Color"])
        links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

    # Roughness
    rough = tex_node("roughness", (-500, -300))
    if rough:
        links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])

    # Metallic
    metal = tex_node("metallic", (-500, -600))
    if metal:
        links.new(metal.outputs["Color"], bsdf.inputs["Metallic"])

    # Emission
    emis = tex_node("emission", (-500, -900), "sRGB")
    if emis:
        links.new(emis.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0

    # Subsurface scattering for realistic skin
    bsdf.inputs["Subsurface Weight"].default_value = 0.12
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
    bsdf.inputs["Subsurface Scale"].default_value = 0.05

    return mat


def assign_material_to_meshes(meshes, mat):
    for mesh in meshes:
        mesh.data.materials.clear()
        mesh.data.materials.append(mat)


def rig_character(meshes, character_name):
    if not meshes:
        print(f"[Rig] No meshes found for {character_name}")
        return None

    # Merge meshes if multiple
    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    mesh_obj = bpy.context.active_object
    mesh_obj.name = f"{character_name}_mesh"

    # Apply transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Get character dimensions
    dims = mesh_obj.dimensions
    height = dims.z
    cx = mesh_obj.location.x
    cy = mesh_obj.location.y
    foot_z = mesh_obj.location.z - (dims.z / 2)

    print(f"[Rig] Character height: {height:.2f}m, base Z: {foot_z:.2f}")

    # Add Rigify human metarig
    enable_rigify()
    bpy.ops.object.armature_human_metarig_add()
    metarig = bpy.context.active_object
    metarig.name = f"{character_name}_metarig"
    metarig.display_type = "WIRE"

    # Scale metarig to match character height
    # Default Rigify metarig is 2.013m
    default_rig_height = 2.013
    scale = height / default_rig_height
    metarig.scale = (scale, scale, scale)
    metarig.location = (cx, cy, foot_z)
    bpy.ops.object.transform_apply(location=True, scale=True)

    # Generate the full rig from the metarig
    bpy.context.view_layer.objects.active = metarig
    try:
        bpy.ops.pose.rigify_generate()
        print(f"[Rig] Rigify generated successfully for {character_name}")
    except Exception as e:
        print(f"[Rig] Rigify generate failed: {e}")
        print(f"[Rig] Open Blender, select the metarig, and click 'Generate Rig' in the Rigify panel manually.")
        return metarig

    # Find the generated rig object
    rig = bpy.data.objects.get("rig")
    if not rig:
        rig = next(
            (o for o in bpy.data.objects
             if o.type == "ARMATURE" and o.name != metarig.name),
            None
        )

    if rig is None:
        print(f"[Rig] Could not find generated rig. Rig manually in Blender.")
        return metarig

    rig.name = f"{character_name}_rig"

    # Parent mesh to rig with automatic weights
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    print(f"[Rig] Mesh parented to rig with automatic weights.")

    # Clean up metarig
    bpy.data.objects.remove(metarig)

    return rig


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 256
    scene.cycles.use_denoising = True


def process_character(config):
    name   = config["name"]
    folder = config["folder"]

    print(f"\n{'='*50}")
    print(f"[Cedarbrook] Processing: {name}")
    print(f"[Cedarbrook] Folder: {folder}")

    if not Path(folder).exists():
        print(f"[ERROR] Folder not found: {folder}")
        return

    fbx_path = find_fbx(folder)
    if not fbx_path:
        print(f"[ERROR] No FBX found in {folder}")
        return

    print(f"[Rig] FBX: {Path(fbx_path).name}")

    clear_scene()
    setup_render()

    # Import
    print(f"[Rig] Importing FBX...")
    meshes, existing_armatures = import_fbx(fbx_path)
    print(f"[Rig] Found {len(meshes)} mesh(es), {len(existing_armatures)} armature(s)")

    # If Meshy already embedded a skeleton, remove it
    for arm in existing_armatures:
        bpy.data.objects.remove(arm)

    # Build and apply PBR material
    print(f"[Rig] Building PBR material...")
    mat = build_pbr_material(f"{name}_mat", folder)
    assign_material_to_meshes(meshes, mat)

    # Rig
    print(f"[Rig] Rigging with Rigify...")
    rig = rig_character(meshes, name)

    # Save .blend
    out_path = str(Path(OUTPUT_DIR) / f"{name}.blend")
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_path)
    print(f"[Rig] Saved: {out_path}")
    print(f"[Rig] Done: {name}")


# ─── RUN ─────────────────────────────────────────────────────────────────────

for config in CHARACTER_CONFIGS:
    process_character(config)

print("\n[Cedarbrook] Auto-rig complete for all characters.")
print("Next steps:")
print("  1. Open each .blend file in /models/")
print("  2. Import Mixamo animations: File > Import > BVH")
print("  3. Run blender/setup_world.py to build Cedarbrook")
print("  4. Run blender/import_characters.py to place characters in the world")
