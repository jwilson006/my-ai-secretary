# Character Models

Drop your Meshy.ai exported model files here.

## Expected files
- `erin_maroni.glb` or `erin_maroni.fbx`
- `lily_maroni.glb` or `lily_maroni.fbx`
- `david_callahan.glb` or `david_callahan.fbx`
- `isabel_callahan.glb` or `isabel_callahan.fbx`

## Rigging pipeline
1. Export from Meshy.ai as FBX or OBJ
2. Upload to mixamo.com → Upload Character → auto-rig
3. Download from Mixamo as FBX (with rig)
4. Drop the rigged FBX here
5. Run: `python blender/import_characters.py` to import into the Blender world
