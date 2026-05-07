"""
Cedarbrook World Builder
Run this script in Blender (Scripting tab > Open > Run Script)
OR send via Claude Desktop's Blender MCP connection.

Builds the full Cedarbrook suburb with:
- GTA V-level Cycles rendering settings
- Full exterior street, two houses, church, office building
- Full interiors with furniture for every room
- HDRI lighting, PBR materials, volumetric atmosphere
"""

import bpy
import math
import os

# ─── SCENE RESET ────────────────────────────────────────────────────────────

def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for col in bpy.data.collections:
        bpy.data.collections.remove(col)

# ─── RENDER SETTINGS (GTA V level) ──────────────────────────────────────────

def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 512
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.render.resolution_x = 2560
    scene.render.resolution_y = 1440
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    # Volumetrics for atmosphere
    scene.render.use_motion_blur = True
    scene.cycles.motion_blur_position = "CENTER"

# ─── HDRI WORLD LIGHTING ────────────────────────────────────────────────────

def setup_world_lighting():
    world = bpy.context.scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.2

    env_tex = nodes.new("ShaderNodeTexEnvironment")
    # Placeholder — user should replace with a real HDRI file
    # Download free HDRIs from polyhaven.com
    # env_tex.image = bpy.data.images.load("/path/to/your/hdri.hdr")

    output = nodes.new("ShaderNodeOutputWorld")
    links.new(env_tex.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], output.inputs["Surface"])

    # Fallback: warm afternoon sky gradient
    bg.inputs["Color"].default_value = (0.42, 0.55, 0.78, 1.0)

    # Sun lamp for directional shadows
    bpy.ops.object.light_add(type="SUN", location=(20, -20, 30))
    sun = bpy.context.active_object
    sun.name = "CedarbrookSun"
    sun.data.energy = 4.0
    sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))

    # Volumetric atmosphere
    bpy.ops.mesh.primitive_cube_add(size=300, location=(0, 0, 75))
    vol = bpy.context.active_object
    vol.name = "AtmosphereVolume"
    mat = bpy.data.materials.new("Atmosphere")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    vol_node = mat.node_tree.nodes.new("ShaderNodeVolumePrincipled")
    vol_node.inputs["Density"].default_value = 0.002
    vol_node.inputs["Color"].default_value = (0.9, 0.92, 1.0, 1.0)
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(vol_node.outputs["Volume"], out.inputs["Volume"])
    vol.data.materials.append(mat)
    vol.display_type = "WIRE"

# ─── MATERIAL HELPERS ───────────────────────────────────────────────────────

def make_pbr_material(name, base_color, roughness=0.5, metallic=0.0, specular=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Specular IOR Level"].default_value = specular
    return mat

def make_skin_material(name, skin_color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*skin_color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
        bsdf.inputs["Subsurface Weight"].default_value = 0.35
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
        bsdf.inputs["Subsurface Scale"].default_value = 0.05
    return mat

def assign_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# ─── GROUND & STREET ────────────────────────────────────────────────────────

def build_ground():
    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    assign_material(ground, make_pbr_material("Grass", (0.15, 0.35, 0.12), roughness=0.9))

    # Main street (Willow Creek Lane)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.01))
    street = bpy.context.active_object
    street.name = "WillowCreekLane"
    street.scale = (60, 6, 0.02)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(street, make_pbr_material("Asphalt", (0.08, 0.08, 0.09), roughness=0.95))

    # Sidewalks
    for side in [(-3.5, 0.015), (3.5, 0.015)]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, side[0], side[1]))
        sw = bpy.context.active_object
        sw.name = f"Sidewalk_{side[0]}"
        sw.scale = (60, 1.2, 0.02)
        bpy.ops.object.transform_apply(scale=True)
        assign_material(sw, make_pbr_material("Concrete", (0.72, 0.70, 0.68), roughness=0.85))

    # Commerce Drive (office street)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -35, 0.01))
    cs = bpy.context.active_object
    cs.name = "CommerceDrive"
    cs.scale = (60, 6, 0.02)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(cs, make_pbr_material("Asphalt", (0.08, 0.08, 0.09), roughness=0.95))

# ─── BUILDING HELPERS ───────────────────────────────────────────────────────

def add_window(location, size=(1.2, 0.1, 1.4), name="Window"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    win = bpy.context.active_object
    win.name = name
    win.scale = size
    bpy.ops.object.transform_apply(scale=True)
    glass = make_pbr_material("Glass_Window", (0.7, 0.85, 0.95), roughness=0.05, metallic=0.0, specular=1.0)
    glass.use_nodes = True
    bsdf = glass.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Transmission Weight"].default_value = 0.92
        bsdf.inputs["IOR"].default_value = 1.45
    assign_material(win, glass)
    return win

def add_door(location, size=(0.9, 0.15, 2.1), color=(0.3, 0.18, 0.10), name="Door"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    door = bpy.context.active_object
    door.name = name
    door.scale = size
    bpy.ops.object.transform_apply(scale=True)
    assign_material(door, make_pbr_material(f"Mat_{name}", color, roughness=0.4))
    return door

def add_furniture_box(location, scale, color, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    assign_material(obj, make_pbr_material(f"Mat_{name}", color, roughness=0.6))
    return obj

# ─── MARONI HOUSE ────────────────────────────────────────────────────────────

def build_maroni_house():
    col = bpy.data.collections.new("MaroniHouse")
    bpy.context.scene.collection.children.link(col)

    ox, oy = -12, 8   # origin: front-left corner

    # Foundation
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+5, oy+5, 0.15))
    found = bpy.context.active_object
    found.name = "Maroni_Foundation"
    found.scale = (10, 10, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(found, make_pbr_material("Foundation", (0.55, 0.52, 0.50), roughness=0.9))

    # Walls
    wall_mat = make_pbr_material("MaroniWalls", (0.88, 0.84, 0.76), roughness=0.85)
    wall_configs = [
        ((ox+5, oy+0.2, 2.0), (10, 0.3, 3.8)),   # front
        ((ox+5, oy+9.8, 2.0), (10, 0.3, 3.8)),   # back
        ((ox+0.2, oy+5, 2.0), (0.3, 10, 3.8)),   # left
        ((ox+9.8, oy+5, 2.0), (0.3, 10, 3.8)),   # right
    ]
    for i, (loc, sc) in enumerate(wall_configs):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        w = bpy.context.active_object
        w.name = f"Maroni_Wall_{i}"
        w.scale = sc
        bpy.ops.object.transform_apply(scale=True)
        assign_material(w, wall_mat)
        col.objects.link(w)
        bpy.context.scene.collection.objects.unlink(w)

    # Roof
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+5, oy+5, 4.2))
    roof = bpy.context.active_object
    roof.name = "Maroni_Roof"
    roof.scale = (11, 11, 0.4)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(roof, make_pbr_material("RoofShingles", (0.25, 0.18, 0.15), roughness=0.95))

    # Front porch
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+5, oy-1.5, 0.25))
    porch = bpy.context.active_object
    porch.name = "Maroni_Porch"
    porch.scale = (5, 2, 0.2)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(porch, make_pbr_material("Porch_Wood", (0.60, 0.45, 0.30), roughness=0.7))

    # Windows and door
    add_window((ox+3, oy+0.1, 2.0), name="Maroni_Win1")
    add_window((ox+7, oy+0.1, 2.0), name="Maroni_Win2")
    add_window((ox+0.1, oy+4, 2.0), (0.1, 1.2, 1.4), name="Maroni_Win3")
    add_door((ox+5, oy+0.05, 1.2), name="Maroni_FrontDoor", color=(0.55, 0.25, 0.10))

    # ── INTERIOR: Living Room ──
    add_furniture_box((ox+3, oy+3, 0.45),   (3.5, 1.2, 0.5),  (0.30, 0.20, 0.55), "Maroni_Sofa")
    add_furniture_box((ox+3, oy+4.8, 0.3),  (2.0, 1.2, 0.4),  (0.20, 0.18, 0.16), "Maroni_CoffeeTable")
    add_furniture_box((ox+1.2, oy+2.5, 0.8),(0.15, 1.5, 1.4), (0.12, 0.12, 0.12), "Maroni_TV")
    add_furniture_box((ox+4.5, oy+6.5, 0.5),(1.2, 1.2, 0.9),  (0.45, 0.30, 0.18), "Maroni_Armchair")

    # ── INTERIOR: Kitchen ──
    add_furniture_box((ox+7.5, oy+2.5, 0.5),(1.8, 0.6, 0.9),  (0.82, 0.80, 0.78), "Maroni_Counter")
    add_furniture_box((ox+8.5, oy+4.5, 0.5),(0.6, 1.5, 0.9),  (0.82, 0.80, 0.78), "Maroni_Counter2")
    add_furniture_box((ox+8.2, oy+2.2, 1.0),(0.6, 0.6, 0.6),  (0.70, 0.70, 0.72), "Maroni_Fridge")

    # ── INTERIOR: Dining Room ──
    add_furniture_box((ox+5, oy+7.5, 0.4),  (1.5, 0.8, 0.75), (0.55, 0.38, 0.22), "Maroni_DiningTable")
    for i, xo in enumerate([-0.9, 0, 0.9]):
        add_furniture_box((ox+5+xo, oy+8.2, 0.45),(0.45, 0.45, 0.85), (0.4, 0.28, 0.15), f"Maroni_Chair_{i}")

    # ── INTERIOR: Bedroom ──
    add_furniture_box((ox+2.5, oy+7.5, 0.35),(2.0, 1.6, 0.55), (0.85, 0.82, 0.88), "Maroni_Bed")
    add_furniture_box((ox+1.2, oy+7.5, 0.5),(0.5, 0.5, 0.7),  (0.45, 0.32, 0.22), "Maroni_Nightstand")

    # Floor
    bpy.ops.mesh.primitive_plane_add(size=1, location=(ox+5, oy+5, 0.32))
    floor = bpy.context.active_object
    floor.name = "Maroni_Floor"
    floor.scale = (9.5, 9.5, 1)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(floor, make_pbr_material("HardwoodFloor", (0.55, 0.38, 0.22), roughness=0.4))

    print("[Cedarbrook] Maroni House built.")

# ─── CALLAHAN HOUSE ──────────────────────────────────────────────────────────

def build_callahan_house():
    col = bpy.data.collections.new("CallahanHouse")
    bpy.context.scene.collection.children.link(col)

    ox, oy = 5, 8  # larger house

    wall_mat = make_pbr_material("CallahanWalls", (0.78, 0.72, 0.65), roughness=0.85)
    wall_configs = [
        ((ox+6, oy+0.2, 2.2), (12, 0.3, 4.2)),
        ((ox+6, oy+11.8, 2.2), (12, 0.3, 4.2)),
        ((ox+0.2, oy+6, 2.2), (0.3, 12, 4.2)),
        ((ox+11.8, oy+6, 2.2), (0.3, 12, 4.2)),
    ]
    for i, (loc, sc) in enumerate(wall_configs):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        w = bpy.context.active_object
        w.name = f"Callahan_Wall_{i}"
        w.scale = sc
        bpy.ops.object.transform_apply(scale=True)
        assign_material(w, wall_mat)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+6, oy+6, 4.6))
    roof = bpy.context.active_object
    roof.name = "Callahan_Roof"
    roof.scale = (13, 13, 0.4)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(roof, make_pbr_material("CallahanRoof", (0.30, 0.22, 0.18), roughness=0.95))

    add_window((ox+3.5, oy+0.1, 2.2), name="Callahan_Win1")
    add_window((ox+8.5, oy+0.1, 2.2), name="Callahan_Win2")
    add_window((ox+0.1, oy+5, 2.2),   (0.1, 1.4, 1.6), name="Callahan_Win3")
    add_door((ox+6, oy+0.05, 1.3), name="Callahan_FrontDoor", color=(0.15, 0.20, 0.35))

    # Living room — open, welcoming (always has guests)
    add_furniture_box((ox+4, oy+4, 0.5),   (4.0, 1.4, 0.55), (0.45, 0.38, 0.60), "Callahan_Sofa")
    add_furniture_box((ox+6, oy+6, 0.35),  (2.2, 1.2, 0.4),  (0.55, 0.45, 0.32), "Callahan_CoffeeTable")
    add_furniture_box((ox+1.5, oy+3.5, 0.5),(1.3, 1.3, 0.95),(0.42, 0.32, 0.22), "Callahan_Armchair1")
    add_furniture_box((ox+1.5, oy+5.5, 0.5),(1.3, 1.3, 0.95),(0.42, 0.32, 0.22), "Callahan_Armchair2")

    # Study (David's)
    add_furniture_box((ox+9, oy+9.5, 0.4), (2.0, 0.8, 0.75), (0.28, 0.22, 0.18), "Callahan_Desk")
    add_furniture_box((ox+9, oy+9.5, 0.8), (1.8, 0.15, 1.2), (0.18, 0.14, 0.10), "Callahan_Bookshelf")
    add_furniture_box((ox+8.5, oy+8.8, 0.5),(0.5, 0.5, 0.9), (0.38, 0.28, 0.18), "Callahan_DeskChair")

    # Bedroom
    add_furniture_box((ox+3, oy+9.5, 0.4), (2.2, 1.8, 0.55), (0.78, 0.75, 0.82), "Callahan_Bed")
    add_furniture_box((ox+1.5, oy+9, 0.5), (0.5, 0.5, 0.7),  (0.48, 0.35, 0.22), "Callahan_NS1")
    add_furniture_box((ox+1.5, oy+10, 0.5),(0.5, 0.5, 0.7),  (0.48, 0.35, 0.22), "Callahan_NS2")

    bpy.ops.mesh.primitive_plane_add(size=1, location=(ox+6, oy+6, 0.32))
    floor = bpy.context.active_object
    floor.name = "Callahan_Floor"
    floor.scale = (11.5, 11.5, 1)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(floor, make_pbr_material("CallahanFloor", (0.62, 0.44, 0.26), roughness=0.45))

    print("[Cedarbrook] Callahan House built.")

# ─── CORNERSTONE CHURCH ──────────────────────────────────────────────────────

def build_church():
    ox, oy = -20, -20

    # Main structure
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+10, 4.0))
    body = bpy.context.active_object
    body.name = "Church_Body"
    body.scale = (16, 20, 7.5)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(body, make_pbr_material("ChurchWalls", (0.94, 0.92, 0.88), roughness=0.85))

    # Bell tower
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+0.5, 8.0))
    tower = bpy.context.active_object
    tower.name = "Church_Tower"
    tower.scale = (4, 4, 8)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(tower, make_pbr_material("ChurchTower", (0.90, 0.88, 0.84), roughness=0.85))

    # Steeple
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=2.2, radius2=0, depth=5, location=(ox+8, oy+0.5, 16))
    steeple = bpy.context.active_object
    steeple.name = "Church_Steeple"
    steeple.rotation_euler[2] = math.radians(45)
    assign_material(steeple, make_pbr_material("Steeple", (0.35, 0.30, 0.28), roughness=0.7))

    # Cross on steeple
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+0.5, 19.5))
    cross_v = bpy.context.active_object
    cross_v.name = "Church_Cross_V"
    cross_v.scale = (0.2, 0.2, 2.0)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(cross_v, make_pbr_material("Cross", (0.65, 0.45, 0.25), roughness=0.5, metallic=0.1))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+0.5, 20.5))
    cross_h = bpy.context.active_object
    cross_h.name = "Church_Cross_H"
    cross_h.scale = (1.4, 0.2, 0.2)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(cross_h, make_pbr_material("Cross", (0.65, 0.45, 0.25), roughness=0.5, metallic=0.1))

    # Arched windows (stained glass effect)
    glass_mat = make_pbr_material("StainedGlass", (0.3, 0.5, 0.9), roughness=0.05)
    glass_mat.use_nodes = True
    bsdf = glass_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Transmission Weight"].default_value = 0.7
        bsdf.inputs["Base Color"].default_value = (0.3, 0.5, 0.95, 1.0)

    for xi in [ox+4, ox+8, ox+12]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(xi, oy+0.15, 4.5))
        win = bpy.context.active_object
        win.name = f"Church_Window_{xi}"
        win.scale = (1.0, 0.1, 2.5)
        bpy.ops.object.transform_apply(scale=True)
        assign_material(win, glass_mat)

    add_door((ox+8, oy+0.1, 1.5), (1.2, 0.15, 2.8), (0.35, 0.22, 0.12), "Church_MainDoor")

    # Interior: Sanctuary
    add_furniture_box((ox+5, oy+12, 0.5),  (1.5, 0.8, 0.9),  (0.40, 0.28, 0.15), "Church_Pew1")
    add_furniture_box((ox+8, oy+12, 0.5),  (1.5, 0.8, 0.9),  (0.40, 0.28, 0.15), "Church_Pew2")
    add_furniture_box((ox+11, oy+12, 0.5), (1.5, 0.8, 0.9),  (0.40, 0.28, 0.15), "Church_Pew3")
    add_furniture_box((ox+5, oy+15, 0.5),  (1.5, 0.8, 0.9),  (0.40, 0.28, 0.15), "Church_Pew4")
    add_furniture_box((ox+8, oy+15, 0.5),  (1.5, 0.8, 0.9),  (0.40, 0.28, 0.15), "Church_Pew5")
    add_furniture_box((ox+11, oy+15, 0.5), (1.5, 0.8, 0.9),  (0.40, 0.28, 0.15), "Church_Pew6")

    # Pulpit
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+7.5, 0.65))
    pulpit = bpy.context.active_object
    pulpit.name = "Church_Pulpit"
    pulpit.scale = (1.2, 0.8, 1.2)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(pulpit, make_pbr_material("Pulpit_Wood", (0.35, 0.22, 0.12), roughness=0.4))

    # Altar cross (wall)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+19.5, 5.0))
    altar_cross_v = bpy.context.active_object
    altar_cross_v.name = "Altar_Cross_V"
    altar_cross_v.scale = (0.3, 0.1, 3.0)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(altar_cross_v, make_pbr_material("AltarCross", (0.55, 0.38, 0.18), roughness=0.4, metallic=0.1))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+8, oy+19.5, 6.0))
    altar_cross_h = bpy.context.active_object
    altar_cross_h.name = "Altar_Cross_H"
    altar_cross_h.scale = (1.8, 0.1, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(altar_cross_h, make_pbr_material("AltarCross", (0.55, 0.38, 0.18), roughness=0.4, metallic=0.1))

    bpy.ops.mesh.primitive_plane_add(size=1, location=(ox+8, oy+10, 0.32))
    floor = bpy.context.active_object
    floor.name = "Church_Floor"
    floor.scale = (15.5, 19.5, 1)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(floor, make_pbr_material("Church_Floor", (0.62, 0.58, 0.50), roughness=0.5))

    print("[Cedarbrook] Cornerstone Church built.")

# ─── MARONI FASHION HQ ───────────────────────────────────────────────────────

def build_office():
    ox, oy = -10, -48

    # Modern building — glass and concrete
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+10, oy+8, 5.0))
    body = bpy.context.active_object
    body.name = "Office_Body"
    body.scale = (20, 16, 9.5)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(body, make_pbr_material("OfficeConcrete", (0.75, 0.75, 0.78), roughness=0.6))

    # Glass facade (front)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+10, oy+0.2, 5.0))
    facade = bpy.context.active_object
    facade.name = "Office_GlassFacade"
    facade.scale = (18, 0.2, 9.0)
    bpy.ops.object.transform_apply(scale=True)
    glass = make_pbr_material("OfficeGlass", (0.55, 0.70, 0.85), roughness=0.05)
    glass.use_nodes = True
    bsdf = glass.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Transmission Weight"].default_value = 0.85
    assign_material(facade, glass)

    add_door((ox+10, oy+0.1, 1.2), (1.5, 0.1, 2.4), (0.60, 0.62, 0.65), "Office_Door")

    # Logo sign
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+10, oy+0.05, 8.5))
    sign = bpy.context.active_object
    sign.name = "Office_Sign"
    sign.scale = (5, 0.15, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(sign, make_pbr_material("Sign", (0.08, 0.06, 0.12), roughness=0.3, metallic=0.6))

    # Interior: Open office
    for i in range(6):
        xi = ox + 2 + (i % 3) * 5
        yi = oy + 5 + (i // 3) * 4
        add_furniture_box((xi, yi, 0.4), (1.4, 0.7, 0.75), (0.88, 0.88, 0.90), f"Office_Desk_{i}")
        add_furniture_box((xi, yi+1.0, 0.45), (0.5, 0.5, 0.88), (0.3, 0.35, 0.55), f"Office_Chair_{i}")

    # Erin's private office
    add_furniture_box((ox+17, oy+10, 0.4), (2.2, 1.0, 0.75), (0.45, 0.32, 0.22), "Erin_Desk")
    add_furniture_box((ox+17, oy+11.2, 0.45), (0.6, 0.6, 0.95), (0.25, 0.22, 0.42), "Erin_Chair")
    add_furniture_box((ox+15, oy+10, 0.8), (0.2, 2.5, 2.0), (0.55, 0.42, 0.30), "Erin_Bookshelf")

    # Sample/design room — fabric boards
    for i in range(4):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(ox+2+i*3, oy+13, 1.5))
        board = bpy.context.active_object
        board.name = f"DesignBoard_{i}"
        board.scale = (1.0, 0.1, 1.8)
        bpy.ops.object.transform_apply(scale=True)
        colors = [(0.9,0.2,0.4), (0.2,0.4,0.8), (0.9,0.6,0.1), (0.3,0.6,0.3)]
        assign_material(board, make_pbr_material(f"Fabric_{i}", colors[i], roughness=0.95))

    bpy.ops.mesh.primitive_plane_add(size=1, location=(ox+10, oy+8, 0.32))
    floor = bpy.context.active_object
    floor.name = "Office_Floor"
    floor.scale = (19.5, 15.5, 1)
    bpy.ops.object.transform_apply(scale=True)
    assign_material(floor, make_pbr_material("OfficeFloor", (0.82, 0.80, 0.82), roughness=0.3))

    print("[Cedarbrook] Maroni Fashion HQ built.")

# ─── LANDSCAPING ─────────────────────────────────────────────────────────────

def add_trees():
    tree_positions = [
        (-18, 6), (-18, 14), (18, 6), (18, 14),
        (-5, 6),  (-5, 14),  (3, 6),  (3, 14),
        (-22, -18), (-14, -18), (-8, -44), (12, -44),
    ]
    trunk_mat  = make_pbr_material("TreeTrunk",   (0.28, 0.18, 0.10), roughness=0.9)
    leaves_mat = make_pbr_material("TreeLeaves",  (0.12, 0.32, 0.10), roughness=0.95)

    for i, (tx, ty) in enumerate(tree_positions):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=3.5, location=(tx, ty, 1.75))
        trunk = bpy.context.active_object
        trunk.name = f"Tree_Trunk_{i}"
        assign_material(trunk, trunk_mat)

        bpy.ops.mesh.primitive_ico_sphere_add(radius=1.8, location=(tx, ty, 4.8))
        canopy = bpy.context.active_object
        canopy.name = f"Tree_Canopy_{i}"
        assign_material(canopy, leaves_mat)

# ─── CAMERAS ─────────────────────────────────────────────────────────────────

def setup_cameras():
    # Overview camera
    bpy.ops.object.camera_add(location=(30, -55, 45))
    cam = bpy.context.active_object
    cam.name = "Cam_Overview"
    cam.rotation_euler = (math.radians(55), 0, math.radians(40))
    cam.data.lens = 35

    # Street-level camera
    bpy.ops.object.camera_add(location=(-5, -5, 2.2))
    cam2 = bpy.context.active_object
    cam2.name = "Cam_Street"
    cam2.rotation_euler = (math.radians(85), 0, math.radians(180))
    cam2.data.lens = 50
    cam2.data.dof.use_dof = True
    cam2.data.dof.aperture_fstop = 2.8

    # Church interior camera
    bpy.ops.object.camera_add(location=(-13, -32, 2.5))
    cam3 = bpy.context.active_object
    cam3.name = "Cam_Church_Interior"
    cam3.rotation_euler = (math.radians(85), 0, math.radians(180))
    cam3.data.lens = 24

    bpy.context.scene.camera = bpy.data.objects["Cam_Overview"]

# ─── MAIN ────────────────────────────────────────────────────────────────────

def build_cedarbrook():
    print("[Cedarbrook] Starting world build...")
    reset_scene()
    setup_render()
    setup_world_lighting()
    build_ground()
    build_maroni_house()
    build_callahan_house()
    build_church()
    build_office()
    add_trees()
    setup_cameras()
    bpy.ops.object.select_all(action="DESELECT")
    print("[Cedarbrook] World build complete.")
    print("  → Maroni House:    -12, 8")
    print("  → Callahan House:   5, 8")
    print("  → Church:         -20, -20")
    print("  → Fashion HQ:     -10, -48")
    print("  → Replace HDRI: Edit setup_world_lighting() with your .hdr path")
    print("  → Download free HDRIs: polyhaven.com")

build_cedarbrook()
