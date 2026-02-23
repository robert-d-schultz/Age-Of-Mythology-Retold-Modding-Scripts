#!/usr/bin/env python3
# Export active Blender mesh to .tmm / .tmm.data (AoM: Retold format, version 35)
# Coordinate system: game uses Y-up left-handed; Blender uses Z-up right-handed.
# Conversion is applied per-vertex (swap Y/Z, flip V) and is NOT baked into the mesh.

import struct
import os
import bpy
import math
from mathutils import Matrix
import numpy as np
from collections import defaultdict
import re

os.system("cls")

# ── Config ────────────────────────────────────────────────────────────────────
tmm_output_filename = "./output.tmm"
# ─────────────────────────────────────────────────────────────────────────────

ob = bpy.context.active_object
if not ob:
    raise Exception("Select an object!")

# Resolve armature from modifier (if any)
armature_object = None
arm_mod = next((m for m in ob.modifiers if m.type == 'ARMATURE' and m.object), None)
if arm_mod:
    armature_object = arm_mod.object
    armature = armature_object.data
    bone_name_to_id = {b.name: i for i, b in enumerate(armature.bones)}

# Baked transform: Z-up RH → Y-up LH  (game convention)
zup_to_yup = Matrix(np.array([
    [1, 0, 0, 0],
    [0, 0, 1, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1]
]))


def _build_ntb_quat(loop):
    """Pack a loop's TBN frame into a compressed quaternion (w-sign in MSB of x).

    Coordinate conversion (Blender Z-up RH → game Y-up LH): swap Y↔Z on T and N.
    For B, swap Y↔Z AND negate, because the V-flip applied at export (UV.v → 1−v)
    reverses the bitangent direction in texture space — the combined effect is that
    game-space B = −swap(B_blender).

    Handedness bit (MSB of X): 1 when the game-space frame [T_g | B_g | N_g] is
    left-handed (det < 0), which happens for UV-mirrored faces.  Standard faces
    (non-mirrored UVs) have det = +1 and handedness = 0.  The game shader uses
    this bit to flip B before sampling the normal map.

    When the frame is left-handed we encode [T_g | −B_g | N_g] (det = +1) as the
    quaternion, and set handedness = 1 so the shader can recover the correct B.
    N is in col 2, confirmed by the import decoder's _quat_to_tbn."""
    t, b, n = loop.tangent, loop.bitangent, loop.normal

    # T and N: Y↔Z swap only
    tx, ty, tz = t.x, t.z, t.y
    nx, ny, nz = n.x, n.z, n.y

    # B: Y↔Z swap + negate (accounts for the V-flip: game UV.v = 1 − blender UV.v)
    bx, by, bz = -b.x, -b.z, -b.y

    # Determinant of [T_g | B_g | N_g] — +1 for normal faces, −1 for UV-mirrored.
    cx = ty*bz - tz*by
    cy = tz*bx - tx*bz
    cz = tx*by - ty*bx
    det = cx*nx + cy*ny + cz*nz
    handedness = 1 if det < 0.0 else 0  # §6.1 MSB: 1 = left-handed frame

    # Build a proper-rotation (det = +1) matrix for Shepperd extraction.
    # Flip B when det < 0 so the quaternion always encodes a right-handed frame.
    sb = -1.0 if det < 0.0 else 1.0
    m00, m10, m20 = tx,      ty,      tz    # col 0 = T_g
    m01, m11, m21 = sb*bx,   sb*by,   sb*bz # col 1 = sb·B_g
    m02, m12, m22 = nx,      ny,      nz    # col 2 = N_g

    trace = m00 + m11 + m22
    if trace > 0.0:
        s = 0.5 / math.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (m21 - m12) * s
        y = (m02 - m20) * s
        z = (m10 - m01) * s
    elif m00 > m11 and m00 > m22:
        s = 2.0 * math.sqrt(1.0 + m00 - m11 - m22)
        x = 0.25 * s;  y = (m01 + m10) / s;  z = (m02 + m20) / s;  w = (m21 - m12) / s
    elif m11 > m22:
        s = 2.0 * math.sqrt(1.0 + m11 - m00 - m22)
        x = (m01 + m10) / s;  y = 0.25 * s;  z = (m12 + m21) / s;  w = (m02 - m20) / s
    else:
        s = 2.0 * math.sqrt(1.0 + m22 - m00 - m11)
        x = (m02 + m20) / s;  y = (m12 + m21) / s;  z = 0.25 * s;  w = (m10 - m01) / s

    mag = math.sqrt(x*x + y*y + z*z + w*w)
    if mag > 0.0:
        x /= mag; y /= mag; z /= mag; w /= mag

    # The decoder does: w = sqrt(1 - |xyz|²), then if handedness: w = -w
    # So the decoded w = (+sqrt) when hand=0, or (-sqrt) when hand=1.
    # Both (-q) and (q) represent the same rotation, so we can freely negate
    # the whole quaternion.  Ensure the decoded sign matches by guaranteeing:
    #   handedness=0  →  w >= 0  (decoder leaves w positive)
    #   handedness=1  →  w <= 0  (decoder negates to make w positive → same rotation)
    if handedness == 0 and w < 0.0:
        x = -x; y = -y; z = -z; w = -w
    elif handedness == 1 and w > 0.0:
        x = -x; y = -y; z = -z; w = -w

    return (x, y, z, handedness)

with open(tmm_output_filename, "wb") as tmm_file:
    me = ob.data
    me.calc_loop_triangles()
    me.calc_tangents()

    # ── Gather attachment empties parented to the armature ────────────────
    attachments = []
    if armature_object:
        for empty in armature_object.children:
            if empty.data is None:  # empties have no mesh data
                parent_id = (list(armature.bones).index(armature.bones[empty.parent_bone])
                             if empty.parent_type == 'BONE' else -1)
                clean_name = re.sub(r'\.\d{3}$', '', empty.name)  # strip .001 suffixes
                attachments.append((clean_name, parent_id, empty.matrix_local))
        

    # ── Build per-material geometry groups ────────────────────────────────
    # Vertex key is a fully-hashable tuple so we can use a dict for O(1) dedup
    # instead of list.index() which is O(n) per vertex.
    material_groups = defaultdict(list)
    for tri in me.polygons:
        material_groups[tri.material_index].append(tri.index)

    total_vertices  = 0
    total_triangles = 0
    mesh_groups     = []

    for mat_index, tri_indices in material_groups.items():
        vertex_map        = {}   # hashable key → index in canon_vertex_list
        canon_vertex_list = []
        triangle_list     = []

        for tri_index in tri_indices:
            tri = me.polygons[tri_index]
            triangle_vert_indices = [0, 0, 0]

            for i, loop_index in enumerate(tri.loop_indices):
                loop = me.loops[loop_index]
                vert = me.vertices[loop.vertex_index]

                # UV — convert to plain tuple (Vector is not hashable)
                if me.uv_layers.active is not None:
                    uv = tuple(me.uv_layers.active.data[loop_index].uv)
                else:
                    uv = (0.0, 0.0)

                ntb_quat = _build_ntb_quat(loop)

                # Bone weights: up to 4, sorted by weight desc, normalised to 0-255
                weight_items = ()
                if armature_object is not None:
                    raw = [(bone_name_to_id[ob.vertex_groups[g.group].name], g.weight)
                           for g in vert.groups
                           if ob.vertex_groups[g.group].name in bone_name_to_id]
                    raw.sort(key=lambda x: x[1], reverse=True)
                    raw = raw[:4]
                    total_w = sum(w for _, w in raw)
                    if total_w > 0:
                        raw = [(b, int(round(w / total_w * 255))) for b, w in raw]
                    weight_items = tuple(raw)  # tuple = hashable

                # Vertex key: co as plain tuple (Vector is not hashable)
                key = (tuple(vert.co), uv, ntb_quat, weight_items)

                if key in vertex_map:
                    triangle_vert_indices[i] = vertex_map[key]
                else:
                    idx = len(canon_vertex_list)
                    vertex_map[key] = idx
                    canon_vertex_list.append(key)
                    triangle_vert_indices[i] = idx

            triangle_list.append(triangle_vert_indices)

        mesh_groups.append((mat_index, canon_vertex_list, triangle_list))
        total_vertices  += len(canon_vertex_list)
        total_triangles += len(triangle_list)


    # ── .tmm header ───────────────────────────────────────────────────────
    tmm_file.write(struct.pack("L",  1296913474))  # "BTMM" magic
    tmm_file.write(struct.pack("L",  35))           # format version
    tmm_file.write(struct.pack("H",  20548))        # "DP" marker

    # Import metadata block (unused at runtime, write empty)
    tmm_file.write(struct.pack("L", 4))  # block byte-length (just the count DWORD below)
    tmm_file.write(struct.pack("L", 0))  # entry count = 0

    # Tight bounding box (bind-pose).  Game is Y-up so Blender Y/Z are swapped.
    bb = (ob.bound_box[0][0], ob.bound_box[0][2],
          ob.bound_box[0][1], ob.bound_box[-2][0],
          ob.bound_box[-2][2], ob.bound_box[-2][1])
    tmm_file.write(struct.pack("<ffffff", *bb))

    # Larger bounding box that should enclose the full animated range
    if armature_object is None:
        tmm_file.write(struct.pack("<ffffff", *bb))
    else:
        r = 3 * ob.bound_box[-2][2]
        tmm_file.write(struct.pack("<ffffff", -r, -r, -r, r, r, r))

    # Bounds radius / HP-bar height (approximate from mesh height)
    tmm_file.write(struct.pack("f", ob.bound_box[-2][2]))

    # Section counts
    tmm_file.write(struct.pack("L", len(mesh_groups)))
    tmm_file.write(struct.pack("L", len(material_groups)))
    tmm_file.write(struct.pack("L", 1))  # shader technique count (always "default")
    tmm_file.write(struct.pack("L", 0 if armature_object is None else len(armature.bones)))
    tmm_file.write(struct.pack("L", 0))  # reserved, always 0
    tmm_file.write(struct.pack("L", len(attachments)))
    tmm_file.write(struct.pack("L", total_vertices))
    tmm_file.write(struct.pack("L", total_triangles * 3))  # stored as index count

    print(f"Total vertices:  {total_vertices}")
    print(f"Total triangles: {total_triangles}")

    # .tmm.data block layout — offsets + byte-lengths (§6 of TMModel docs)
    # Layout: [vertices | indices | skin weights | (2× reserved) | heights | (1× reserved)]
    v_bytes  = total_vertices  * 16   # 3×pos(f16) + 2×uv(f16) + 3×quat(u16) = 16 bytes
    i_bytes  = total_triangles * 3 * 2
    sk_bytes = total_vertices  * 8    # 4 weight bytes + 4 bone-index bytes
    h_bytes  = total_vertices  * 2    # local height: 1× f16 per vertex

    tmm_file.write(struct.pack("LL", 0,          v_bytes))                        # vertices
    tmm_file.write(struct.pack("LL", v_bytes,    i_bytes))                        # indices
    tmm_file.write(struct.pack("LL", v_bytes + i_bytes, sk_bytes))                # skin
    tmm_file.write(struct.pack("LLLL", 0, 0, 0, 0))                              # 2× reserved
    tmm_file.write(struct.pack("LL",   v_bytes + i_bytes + sk_bytes, h_bytes))   # heights
    tmm_file.write(struct.pack("LL", 0, 0))                                       # 1× reserved

    tmm_file.write(struct.pack("BB", 0, 1))  # two flag bytes (observed constant)

    # 4×3 "main matrix": bakes the armature transform so exported animations align to
    # this mesh's scale.  Apply zup_to_yup first to push into game-space.
    if armature_object:
        main_matrix      = armature_object.matrix_basis @ zup_to_yup
        main_matrix_list = [f for row in main_matrix for f in row][:12]
    else:
        main_matrix_list = [1, 0, 0, 0,  0, 1, 0, 0,  0, 0, 1, 0]
    tmm_file.write(struct.pack("ffffffffffff", *main_matrix_list))

    # ── Attachments (§5.2) ────────────────────────────────────────────────
    print("Attachments:")
    for name, parent_id, mat_local in attachments:
        print(f"  {name}")
        tmm_file.write(struct.pack("L", 0))            # attach-type flag (0 = default)
        tmm_file.write(struct.pack("l", parent_id))    # parent bone index (-1 = none)

        name_enc = name.encode("UTF-16LE")
        tmm_file.write(struct.pack("<L%ds" % len(name_enc), len(name), name_enc))

        # Both transform matrix slots contain the same value in all observed files
        mat_list = [f for row in mat_local for f in row][:12]
        tmm_file.write(struct.pack("ffffffffffff", *mat_list))
        tmm_file.write(struct.pack("ffffffffffff", *mat_list))

        tmm_file.write(struct.pack("LL", 0, 0))    # two reserved DWORD fields
        tmm_file.write(struct.pack("L", 0))         # second string: empty (length = 0)
        tmm_file.write(struct.pack("llll", -1, 0, 0, 0))  # terminator quad

    # ── Mesh groups (§5.3) ───────────────────────────────────────────────
    verts_offset = 0
    tris_offset  = 0
    for mat_index, verts, tris in mesh_groups:
        tmm_file.write(struct.pack("L", verts_offset))
        tmm_file.write(struct.pack("L", tris_offset))
        tmm_file.write(struct.pack("L", len(verts)))
        tmm_file.write(struct.pack("L", len(tris) * 3))
        tmm_file.write(struct.pack("L", mat_index))
        tmm_file.write(struct.pack("L", 1))  # shader technique index (1 = "default")
        verts_offset += len(verts)
        tris_offset  += len(tris) * 3

    # ── Materials (§5.4) ─────────────────────────────────────────────────
    for mat in ob.data.materials:
        enc = mat.name.encode("UTF-16LE")
        tmm_file.write(struct.pack("<L%ds" % len(enc), len(mat.name), enc))

    # ── Shader technique — always just "default" ──────────────────────────
    enc = "default".encode("UTF-16LE")
    tmm_file.write(struct.pack("<L%ds" % len(enc), len("default"), enc))

    # ── Bones / bind-pose skeleton (§5.6) ────────────────────────────────
    print("Exporting bind-pose skeleton:")
    if armature_object is not None:
        bones = armature.bones
        for bone in bones:
            print(f"  {bone.name}")
            clean = re.sub(r'\.\d{3}$', '', bone.name)  # strip .001 suffixes added by importer
            enc   = clean.encode("UTF-16LE")
            tmm_file.write(struct.pack("<L%ds" % len(enc), len(clean), enc))

            parent       = bone.parent
            parent_index = list(bones).index(bones[parent.name]) if parent else -1
            tmm_file.write(struct.pack("l",  parent_index))
            tmm_file.write(struct.pack("fff", 0, 0, 0))          # bone collision offset (XYZ)
            tmm_file.write(struct.pack("f",  bone.head_radius))  # click/collision radius

            # World-space matrix with main_matrix applied so it matches animation space
            ws = main_matrix @ bone.matrix_local
            ws_flat  = [f for row in ws.transposed()  for f in row]
            inv_flat = [f for row in ws.inverted().transposed() for f in row]

            # Parent-space: bone local relative to its parent (root bones fall back to WS)
            try:
                parent_space_mat = parent.matrix_local.inverted() @ bone.matrix_local
            except AttributeError:
                parent_space_mat = ws
            ps_flat = [f for row in parent_space_mat.transposed() for f in row]

            tmm_file.write(struct.pack("ffffffffffffffff", *ps_flat))   # parent space
            tmm_file.write(struct.pack("ffffffffffffffff", *ws_flat))   # world space
            tmm_file.write(struct.pack("ffffffffffffffff", *inv_flat))  # inverse bind pose

    # ── Trailing sections ─────────────────────────────────────────────────
    tmm_file.write(struct.pack("L", 0))  # sound/animation reference list: empty

    if armature_object is not None:
        tmm_file.write(struct.pack("BBBB", 0, 0, 0, 0))  # padding present only on skinned models

    tmm_file.write(struct.pack("B",  0))      # reserved
    tmm_file.write(struct.pack("H",  22614))  # "VX" marker
    tmm_file.write(struct.pack("L",  1))      # always 1
    tmm_file.write(struct.pack("B",  0))      # terrain height-projection flag (disabled)

    # ── .tmm.data file (§6) ───────────────────────────────────────────────
    with open(tmm_output_filename + ".data", "wb") as tmm_data_file:

        # §6.1 Vertex buffer — 16 bytes/vertex:
        #   pos:  3× f16  (Z/Y swapped for game Y-up)
        #   uv:   2× f16  (V flipped)
        #   quat: 3× u16  (15-bit signed component + 1-bit w-sign in MSB of X)
        for _, verts, _ in mesh_groups:
            for co, uv, ntb_quat, _ in verts:
                x, y, z = co
                u, v    = uv

                xq, yq, zq, w_sign = ntb_quat
                xq_u16 = (int(round(((xq + 1.0) * 0.5) * 32767.0)) & 0x7FFF) | (0x8000 if w_sign else 0)
                yq_u16 =  int(round(((yq + 1.0) * 0.5) * 32767.0)) & 0x7FFF
                zq_u16 =  int(round(((zq + 1.0) * 0.5) * 32767.0)) & 0x7FFF

                tmm_data_file.write(struct.pack('<eee',  x, z, y))      # Y/Z swap
                tmm_data_file.write(struct.pack('<ee',   u, 1 - v))     # V flip
                tmm_data_file.write(struct.pack('<HHH',  xq_u16, yq_u16, zq_u16))

        # §6.2 Index buffer — u16 triangle indices; winding flipped for LH convention
        for _, _, tris in mesh_groups:
            for tri in tris:
                tmm_data_file.write(struct.pack('<HHH', tri[0], tri[2], tri[1]))

        # §6.3 Skinning buffer — 4 weights + 4 bone-indices, 8 bytes/vertex
        if armature_object is not None:
            for _, verts, _ in mesh_groups:
                for _, _, _, weights in verts:
                    padded = [(0, 0)] * (4 - len(weights)) + list(weights)
                    for _, w in padded:
                        tmm_data_file.write(struct.pack('<B', w))
                    for b, _ in padded:
                        tmm_data_file.write(struct.pack('<B', b))

        # §6.6 Local height buffer — f16 Y value per vertex (used by terrain embellishment)
        for _, verts, _ in mesh_groups:
            for co, _, _, _ in verts:
                tmm_data_file.write(struct.pack('<e', co[1]))  # Blender Y = game height
