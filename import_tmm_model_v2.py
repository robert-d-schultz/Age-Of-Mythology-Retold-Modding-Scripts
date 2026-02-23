#!/usr/bin/env python3
# Import a .tmm / .tmm.data pair into Blender (AoM: Retold format, version 35)
# Coordinate system: game is Y-up left-handed; Blender is Z-up right-handed.
# The armature's rotation_euler / scale correct for this at import time.
#
# TODO: building attachments (non-bone parent) are not yet positioned correctly

import struct
import os
import bpy
import math
from mathutils import Matrix
import numpy as np

os.system("cls")

tmm_filename = "/path/to/tmm_file.tmm"  # ← set this before running


with open(tmm_filename, "rb") as tmm_file:
    # ── §5.1 Header ─────────────────────────────────────────────────────────────
    BTMM    = struct.unpack("<L", tmm_file.read(4))[0]
    assert BTMM == 1296913474, BTMM  # "BTMM"
    version = struct.unpack("<L", tmm_file.read(4))[0]
    assert version == 35, version
    DP      = struct.unpack("<H", tmm_file.read(2))[0]
    assert DP == 20548, DP           # "DP"



    # Import metadata — only used by the exporter toolchain, not the game engine
    tmm_file.read(4)  # block byte-length
    num_import_crap = struct.unpack("<L", tmm_file.read(4))[0]
    for _ in range(num_import_crap):
        name_len = struct.unpack("<L", tmm_file.read(4))[0] * 2
        tmm_file.read(name_len)  # name string (UTF-16LE)
        tmm_file.read(16)        # unknown trailing data

    # Tight (bind-pose) and extended (animated) bounding boxes
    bounding_box        = struct.unpack("<ffffff", tmm_file.read(24))
    bigger_bounding_box = struct.unpack("<ffffff", tmm_file.read(24))

    unknown_float = struct.unpack("<f", tmm_file.read(4))[0]  # approx HP-bar height

    # ── Section counts ─────────────────────────────────────────────────────────────
    num_mesh_groups    = struct.unpack("<L", tmm_file.read(4))[0]
    num_materials      = struct.unpack("<L", tmm_file.read(4))[0]
    num_defaults       = struct.unpack("<L", tmm_file.read(4))[0]  # shader techniques (usually 1: "default")
    num_bones          = struct.unpack("<L", tmm_file.read(4))[0]
    num_unknown2       = struct.unpack("<L", tmm_file.read(4))[0]  # reserved, always 0
    assert num_unknown2 == 0, num_unknown2
    num_attachments    = struct.unpack("<L", tmm_file.read(4))[0]
    num_vertices       = struct.unpack("<L", tmm_file.read(4))[0]
    num_triangle_verts = struct.unpack("<L", tmm_file.read(4))[0]
    num_triangles = num_triangle_verts // 3
    assert num_triangles * 3 == num_triangle_verts

    # ── §6 .tmm.data block layout (offsets + byte-lengths) ──────────────────────
    # These are read but not directly used — we read the .data sequentially.
    vertices_start   = struct.unpack("<L", tmm_file.read(4))[0]
    vertices_bl      = struct.unpack("<L", tmm_file.read(4))[0]
    triangles_start  = struct.unpack("<L", tmm_file.read(4))[0]
    triangles_bl     = struct.unpack("<L", tmm_file.read(4))[0]
    weights_start    = struct.unpack("<L", tmm_file.read(4))[0]
    weights_bl       = struct.unpack("<L", tmm_file.read(4))[0]

    unknown1_start = struct.unpack("<L", tmm_file.read(4))[0]  # reserved block
    assert unknown1_start == 0, unknown1_start
    tmm_file.read(4)
    unknown2_start = struct.unpack("<L", tmm_file.read(4))[0]  # reserved block
    assert unknown2_start == 0, unknown2_start
    tmm_file.read(4)

    heights_start  = struct.unpack("<L", tmm_file.read(4))[0]  # §6.6 local height
    heights_bl     = struct.unpack("<L", tmm_file.read(4))[0]

    unknown3_start = struct.unpack("<L", tmm_file.read(4))[0]  # reserved block
    assert unknown3_start == 0, unknown3_start
    tmm_file.read(4)

    unknown_bools = struct.unpack("<BB", tmm_file.read(2))
    assert unknown_bools == (0, 1), unknown_bools

    # "Main matrix": bakes the mesh-vs-animation scale mismatch so animations align.
    # Row-ordered 4×3, expanded to 4×4 for Blender.
    main_matrix = struct.unpack("<ffffffffffff", tmm_file.read(48))
    main_matrix = Matrix(np.array(list(main_matrix) + [0, 0, 0, 1]).reshape(4, 4))
    main_matrix_inverted = main_matrix.inverted()


        
    # ── §5.2 Attachments ─────────────────────────────────────────────────────────────
    attachments = []
    for _ in range(num_attachments):
        unknown_int = struct.unpack("<L", tmm_file.read(4))[0]  # attach-type flag
        assert unknown_int == 0, unknown_int

        parent_bone_id = struct.unpack("<l", tmm_file.read(4))[0]

        name_len        = struct.unpack("<L", tmm_file.read(4))[0] * 2
        attachment_name = tmm_file.read(name_len).decode('UTF-16-LE')

        # Two transform matrices (parent-space and world-space); both stored
        transform_matrix1 = struct.unpack("<ffffffffffff", tmm_file.read(48))
        transform_matrix2 = struct.unpack("<ffffffffffff", tmm_file.read(48))

        unknown_zero1 = struct.unpack("<L", tmm_file.read(4))[0]  # 0 normally, 2 for relics/riders
        assert unknown_zero1 == 0 or unknown_zero1 == 2, unknown_zero1
        unknown_zero2 = struct.unpack("<L", tmm_file.read(4))[0]
        assert unknown_zero2 == 0, unknown_zero2

        second_len  = struct.unpack("<L", tmm_file.read(4))[0] * 2  # optional second name
        second_name = tmm_file.read(second_len).decode('UTF-16-LE')

        unknown_ints = struct.unpack("<llll", tmm_file.read(16))  # terminator quad
        assert unknown_ints == (-1, 0, 0, 0), unknown_ints

        attachments.append((attachment_name, parent_bone_id, transform_matrix1))
        

    
    # ── §5.3 Mesh groups ─────────────────────────────────────────────────────────────
    mesh_group_list = []
    for _ in range(num_mesh_groups):
        verts_start    = struct.unpack("<L", tmm_file.read(4))[0]
        tris_start     = struct.unpack("<L", tmm_file.read(4))[0]
        num_verts      = struct.unpack("<L", tmm_file.read(4))[0]
        num_tri_verts  = struct.unpack("<L", tmm_file.read(4))[0]
        num_tris       = num_tri_verts // 3
        mat_index      = struct.unpack("<L", tmm_file.read(4))[0]
        shader_index   = struct.unpack("<L", tmm_file.read(4))[0]  # index into shader techniques list
        mesh_group_list.append((num_verts, num_tris, mat_index))

    # ── §5.4 Materials ─────────────────────────────────────────────────────────────
    material_list = []
    for _ in range(num_materials):
        mat_len  = struct.unpack("<L", tmm_file.read(4))[0] * 2
        mat_name = tmm_file.read(mat_len).decode('UTF-16-LE')
        material_list.append(mat_name)

    # Shader techniques (usually just "default", skip content)
    for _ in range(num_defaults):
        tech_len = struct.unpack("<L", tmm_file.read(4))[0] * 2
        tmm_file.read(tech_len)
    
    
    
    # ── §5.6 Bones / bind-pose skeleton ─────────────────────────────────────────────
    # May be a subset of the full animation skeleton (unused bones omitted).
    bone_list = []
    for _ in range(num_bones):
        bone_len  = struct.unpack("<L", tmm_file.read(4))[0] * 2
        bone_name = tmm_file.read(bone_len).decode('UTF-16-LE')
        bone_parent_id = struct.unpack("<l", tmm_file.read(4))[0]

        bone_collision_offset = struct.unpack("<fff", tmm_file.read(12))  # XYZ offset for click/collision sphere
        radius = struct.unpack("<f", tmm_file.read(4))[0]                  # click/collision sphere radius

        # Three 4×4 matrices stored column-major (transpose when converting to Blender)
        parent_space_matrix  = struct.unpack("<ffffffffffffffff", tmm_file.read(64))
        world_space_matrix   = struct.unpack("<ffffffffffffffff", tmm_file.read(64))
        inverse_bind_matrix  = struct.unpack("<ffffffffffffffff", tmm_file.read(64))

        bone_list.append((bone_name, bone_parent_id, world_space_matrix, radius))

    # Everything after this point is destruction/click-volume data; not needed for import.
    



# ── Armature / mesh assembly ─────────────────────────────────────────────────────────

def setup_armature(tmm_data_filename, bone_list):
    """Create an armature from the tmm bind-pose skeleton.
    Returns the armature Object, or False if bone_list is empty."""
    print("Setting up armature")
    try:
        anim_collection = bpy.data.collections["imported"]
    except KeyError:
        anim_collection = bpy.data.collections.new("imported")
        bpy.context.scene.collection.children.link(anim_collection)

    if not bone_list:
        return False

    arm_name = os.path.splitext(os.path.basename(tmm_data_filename))[0] + "_armature"

    #Set up armature
    armature = bpy.data.armatures.new(arm_name)
    armature_object = bpy.data.objects.new(arm_name, armature)
    anim_collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    
    # Correct for game Y-up LH → Blender Z-up RH
    armature_object.rotation_euler = (-math.pi / 2, 0, 0)
    armature_object.scale = (1, -1, 1)
    # Apply main_matrix so animations (which carry the same matrix) will align
    armature_object.matrix_basis = armature_object.matrix_basis @ main_matrix
    
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    for i, bone in enumerate(bone_list):
        bone_name, parent_index, world_space_mat, radius = bone
        print(f"  Bone: {bone_name}")

        world_space_mat = Matrix(np.array(world_space_mat).reshape(4, 4))
        world_space_mat.transpose()

        ebs = armature.edit_bones

        # find all existing bones with this name
        candidates = [b for b in ebs if b.name == bone_name]

        eb = None

        if not candidates:
            # no bone with this name at all
            print("    Not in the armature, adding")
            eb = ebs.new(bone_name)

        else:
            # at least one bone with this name exists → check parent
            print("    Found bone(s) with same name, checking parent")

            expected_parent = None
            if parent_index >= 0:
                try:
                    expected_parent = armature.edit_bones[parent_index]
                except Exception:
                    expected_parent = None

            for c in candidates:
                if c.parent is expected_parent:
                    eb = c
                    print("    Parent matches, overwriting existing bone")
                    break

            if eb is None:
                # same name exists, but none match the parent → different bone
                eb = ebs.new(bone_name)
                print(f"    Parent does not match, creating new bone '{eb.name}'")

        eb.head_radius = radius
        eb.tail_radius = radius
        eb.tail = (0.0, 0.2, 0.0)

        if parent_index >= 0:
            try:
                eb.parent = armature.edit_bones[parent_index]
            except Exception:
                pass

        eb.matrix = main_matrix_inverted @ world_space_mat

    bpy.ops.object.mode_set(mode='OBJECT')
    
    return armature_object



# ── TBN quaternion helpers (§6.1) ─────────────────────────────────────────

def _u15_to_float(v):
    """Map unsigned 15-bit value (0..32767) to signed float (-1..+1)."""
    return (v / 32767.0) * 2.0 - 1.0


def _quat_from_packed(u16_x, u16_y, u16_z):
    """Unpack a TBN quaternion from three u16 values.
    Low 15 bits per channel are the xyz components; MSB of x is the handedness bit.
    Returns (x, y, z, w, handedness) — handedness is passed on to _quat_to_tbn
    so it can flip B back for UV-mirrored faces."""
    handedness = (u16_x >> 15) & 0x1
    x = _u15_to_float(u16_x & 0x7FFF)
    y = _u15_to_float(u16_y & 0x7FFF)
    z = _u15_to_float(u16_z & 0x7FFF)

    w_sq = max(0.0, 1.0 - (x*x + y*y + z*z))
    w = math.sqrt(w_sq)
    if handedness:
        w = -w

    mag = math.sqrt(x*x + y*y + z*z + w*w)
    if mag > 0.0:
        x /= mag; y /= mag; z /= mag; w /= mag

    return (x, y, z, w, handedness)


def _quat_to_tbn(q, handedness=0):
    """Decode a TBN quaternion into Blender Z-up tangent, bitangent and normal vectors.

    The packed quaternion always encodes a proper-rotation (det = +1) frame:
      hand=0 → [T_g | B_g | N_g]   (standard / non-mirrored UV face)
      hand=1 → [T_g | −B_g | N_g]  (UV-mirrored face; B was negated before packing)
    We flip B back when hand=1 to recover the true game-space B.

    Inverse coordinate conversion (game Y-up → Blender Z-up):
      T, N : swap Y↔Z
      B    : swap Y↔Z then negate  (inverse of export's negate-then-swap)"""
    x, y, z, w = q[:4]
    xx = x*x; yy = y*y; zz = z*z
    xy = x*y; xz = x*z; yz = y*z
    wx = w*x; wy = w*y; wz = w*z

    # Game-space column vectors (Y-up)
    tg = (1 - 2*(yy + zz),  2*(xy + wz),      2*(xz - wy))
    bg = (2*(xy - wz),       1 - 2*(xx + zz),  2*(yz + wx))
    ng = (2*(xz + wy),       2*(yz - wx),       1 - 2*(xx + yy))

    # Recover true B for UV-mirrored faces (hand=1 means B was negated before packing)
    if handedness:
        bg = (-bg[0], -bg[1], -bg[2])

    # Convert to Blender Z-up: T,N swap Y↔Z; B swap Y↔Z then negate
    tangent   = ( tg[0],  tg[2],  tg[1])
    bitangent = (-bg[0], -bg[2], -bg[1])
    normal    = ( ng[0],  ng[2],  ng[1])
    return tangent, bitangent, normal


def read_tmm_data(tmm_data_filename, num_vertices, num_triangles, mesh_group_list, armature_object):
    """Read .tmm.data, build the Blender mesh, apply UVs/normals, rig to armature."""
    with open(tmm_data_filename + ".data", "rb") as tmm_data_file:
        # ── §6.1 Vertex buffer ─────────────────────────────────────────────
        print(os.path.basename(tmm_data_filename) + ".data")
        print(f"{num_vertices} vertices, {num_triangles} triangles")
        vertex_list = []
        uv_list = []
        norm_list = []
        for i, mesh_group in enumerate(mesh_group_list):
            print(f"Mesh group {i}, {mesh_group[0]} vertices")
            for j in range(mesh_group[0]):
                x, y, z, u, v = struct.unpack("<eeeee", tmm_data_file.read(10))
                vertex_list.append((x, z, y))  # swap Z/Y for Blender Z-up
                uv_list.append((u, 1 - v))     # flip V

                raw = tmm_data_file.read(6)
                if len(raw) != 6:
                    raise EOFError("not enough vertex data")
                u16_x, u16_y, u16_z = struct.unpack('<HHH', raw)
                *q, hand = _quat_from_packed(u16_x, u16_y, u16_z)
                _, _, normal = _quat_to_tbn(q, hand)  # returns Blender Z-up vectors
                norm_list.append(normal)
                
        
        # ── §6.2 Index buffer ──────────────────────────────────────────────────
        triangle_list = []
        vert_index_offset = 0
        for j, mesh_group in enumerate(mesh_group_list):
            print(f"Mesh group {j}, {mesh_group[1]} triangles")
            for _ in range(mesh_group[1]):
                a, b, c = struct.unpack("<HHH", tmm_data_file.read(6))
                offset_indices = (a + vert_index_offset, b + vert_index_offset, c + vert_index_offset)
                tri_vert_indices = (offset_indices[0], offset_indices[2], offset_indices[1])
                triangle_list.append(tri_vert_indices)
            
            vert_index_offset += mesh_group[0]
        
        
        
        # ── §6.3 Skinning buffer ─────────────────────────────────────────────────
        weighted_bone_data = []
        if armature_object is not False:
            for vertex in range(num_vertices):
                weights  = struct.unpack("<BBBB", tmm_data_file.read(4))
                bone_ids = struct.unpack("<BBBB", tmm_data_file.read(4))
                # zip weights+ids, drop zero-weight slots
                weighted_bones = [(bid, w) for bid, w in zip(bone_ids, weights) if w != 0]
                weighted_bone_data.append(weighted_bones)

        # §6.6 heights skipped (not needed for mesh import)

        # ── Build Blender mesh ───────────────────────────────────────────────────
        model_name = os.path.splitext(os.path.basename(tmm_data_filename))[0]
        current_mesh = bpy.data.meshes.new(model_name)
        current_mesh.from_pydata(vertex_list, [], triangle_list)
        current_mesh.update()

        # UV
        current_mesh.uv_layers.new()
        current_mesh.uv_layers[-1].data.foreach_set(
            "uv", [uv for pair in [uv_list[l.vertex_index] for l in current_mesh.loops] for uv in pair])

        # Per-loop split normals — modern replacement for the deprecated
        # normals_split_custom_set_from_vertices.  Because TMM stores fully split
        # vertices (unique position+UV+normal per entry) each vertex has exactly
        # one normal, so expanding to per-loop is safe and correct.
        loop_normals = [norm_list[l.vertex_index] for l in current_mesh.loops]
        current_mesh.normals_split_custom_set(loop_normals)
        
        # Place in shared "imported" collection
        try:
            collection = bpy.data.collections["imported"]
        except KeyError:
            collection = bpy.data.collections.new("imported")
            bpy.context.scene.collection.children.link(collection)
        current_object = bpy.data.objects.new(model_name, current_mesh)
        collection.objects.link(current_object)

        # Rig to armature
        if armature_object is not False:
            print("Rigging to " + armature_object.name)
            for v_idx, bone_weights in enumerate(weighted_bone_data):
                for bone_id, weight in bone_weights:
                    bone_name = armature_object.data.bones[bone_id].name
                    # Create vertex group if it doesn't exist
                    if bone_name not in current_object.vertex_groups:
                        current_object.vertex_groups.new(name=bone_name)
                    group = current_object.vertex_groups[bone_name]
                    group.add([v_idx], weight / 255.0, 'ADD')

            # Add armature modifier
            mod = current_object.modifiers.new(type='ARMATURE', name="Armature")
            mod.object = armature_object
            
    return current_object
    
    
def assign_materials(mesh_object, mesh_group_list, material_list):
    """Create materials (if needed) and assign them to the correct polygon ranges."""
    current_mesh = mesh_object.data

    for mat_name in material_list:
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        mesh_object.data.materials.append(mat)

    tri_index = 0
    for _, tri_count, mat_index in mesh_group_list:
        for _ in range(tri_count):
            if tri_index < len(current_mesh.polygons):
                current_mesh.polygons[tri_index].material_index = mat_index
                tri_index += 1
    return True
    
    


# ── Main execution ─────────────────────────────────────────────────────────────
armature_obj = setup_armature(tmm_filename, bone_list)
mesh_obj     = read_tmm_data(tmm_filename, num_vertices, num_triangles, mesh_group_list, armature_obj)
assign_materials(mesh_obj, mesh_group_list, material_list)

# Attachments — parented to bones when possible
print("Attachments:")
for attachment in attachments:
    print(f"  {attachment[0]}")
    empty = bpy.data.objects.new(attachment[0], None)
    bpy.data.collections["imported"].objects.link(empty)
    empty.empty_display_size = 0.25

    if armature_obj:
        empty.parent = armature_obj
        if attachment[1] >= 0:  # valid bone parent
            empty.parent_type = 'BONE'
            empty.parent_bone = armature_obj.data.bones[attachment[1]].name
    # else: building attachment — parent/position not yet handled (TODO)

    # Local transform from the first matrix slot (no main_matrix adjustment needed)
    empty.matrix_local = Matrix(np.array(list(attachment[2]) + [0, 0, 0, 1]).reshape(4, 4))