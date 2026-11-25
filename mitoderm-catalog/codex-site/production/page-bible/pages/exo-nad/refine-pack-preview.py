"""Preview the owner's 25 Nov correction: slide the gold cover along the box.

Usage: blender -b --python refine-pack-preview.py -- source.blend output-directory
Original artwork/source model and the user's open scene are never overwritten.
This is a review candidate, not a measured manufacturing reconstruction.
"""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
source, output = Path(args[0]), Path(args[1])
output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.render.resolution_x = 720
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = 'IMAGE'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False

# Keep the original photographed print; reduce the specular veil over its ink.
for name in ['Original outside lid artwork', 'Original inside lid photograph']:
    material = bpy.data.materials.get(name)
    if material and material.use_nodes:
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Metallic'].default_value = 0
        shader.inputs['Roughness'].default_value = .48
        shader.inputs['Specular IOR Level'].default_value = .08

world = scene.world.node_tree.nodes.get('Background')
world.inputs['Color'].default_value = (.16, .13, .105, 1)
world.inputs['Strength'].default_value = .3

floor_mat = bpy.data.materials.new('NAD studio surface')
floor_mat.use_nodes = True
shader = floor_mat.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (.035, .026, .019, 1)
shader.inputs['Roughness'].default_value = .48
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.001))
bpy.context.object.name = 'Studio_surface'
bpy.context.object.data.materials.append(floor_mat)

camera = scene.camera
camera.animation_data_clear()
camera.data.lens = 48
camera.location = (.13, -.65, .77)
camera.rotation_euler = (Vector((0, .055, .025)) - camera.location).to_track_quat('-Z', 'Y').to_euler()

lid = bpy.data.objects['LID_HINGE']
scene.frame_set(1)
closed_z = lid.location.z
lid.animation_data_clear()
lid.rotation_euler = (0, 0, 0)
lid['mechanism_note'] = '25 Nov owner correction: upper gold cover slides along the box like the outer V-TECH sleeve. Review candidate; no perpendicular lift or inner hinge.'
# The former front/rear lips would cut through the stationary tray on this path.
# Open ends make the gold shell slide; preserve its original printed upper face.
for name in ['Lid_front_fold', 'Lid_back_fold']:
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
for name in ['Lid_left_fold', 'Lid_right_fold']:
    side = bpy.data.objects[name]
    side.dimensions.z = .047
    side.location.z = -.0235
for frame, travel in [(1, 0), (11, 0), (97, .386), (121, .386)]:
    lid.location = (0, travel, closed_z)
    lid.keyframe_insert(data_path='location', frame=frame)
base = bpy.data.objects['BASE_AND_TRAY']
base_transform = base.matrix_world.copy()
samples = []
for frame in range(1, 122):
    scene.frame_set(frame)
    assert max(abs(v) for v in lid.rotation_euler) < 1e-6, 'Cover must not rotate'
    assert abs(lid.location.x) < 1e-6 and abs(lid.location.z - closed_z) < 1e-6, 'Slide must stay parallel to the tray'
    assert base.matrix_world == base_transform, 'Tray must stay fixed'
    samples.append({'frame': frame, 'travel': round(lid.location.y, 6), 'height': round(lid.location.z, 6)})
assert all(b['travel'] >= a['travel'] for a, b in zip(samples, samples[1:]))
assert samples[-1]['travel'] > .286, 'Cover must fully clear the box'
(output / 'motion-check.json').write_text(json.dumps({'cover': samples, 'rotation': 0, 'axis': 'local Y, along box', 'status': 'review_candidate'}, indent=2))

bpy.ops.wm.save_as_mainfile(filepath=str(output / 'exo-nad-slide-off-preview.blend'))
for frame, name in [(1, 'closed'), (61, 'opening'), (121, 'open')]:
    scene.frame_set(frame)
    scene.render.filepath = str(output / (name + '.png'))
    bpy.ops.render.render(write_still=True)
print('PACK_PREVIEW_READY', str(output))

# Optional inexpensive motion proof: 41 frames, played at 8 fps (about 5 seconds).
# Keep it separate from final media and from any paid generation approval.
if '--animate' in args[2:]:
    scene.render.resolution_percentage = 67
    scene.cycles.samples = 8
    scene.render.fps = 8
    scene.frame_step = 3
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.filepath = str(output / 'opening-preview.mp4')
    bpy.ops.render.render(animation=True)
    print('PACK_MOTION_READY', scene.render.filepath)
