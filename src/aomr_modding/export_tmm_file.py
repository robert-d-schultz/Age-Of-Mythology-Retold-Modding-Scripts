#!/usr/bin/env python3
from collections import defaultdict
import os
import re
import struct

import bpy
from mathutils import Matrix
import numpy as np

os.system("cls")

# TODO
# Normal vectors are not understooad, so I'm forced to export junk
# Vertex optimization needs to be looked at once normal vectors are understood


tmm_output_filename = "./output.tmm"


# Exported mesh is the one selected
ob = bpy.context.active_object
if not ob:
    raise Exception("Select an object!")

# Find armature modifier
armature_object = None
arm_mod = next((m for m in ob.modifiers if m.type == "ARMATURE" and m.object), None)
if arm_mod:
    armature_object = arm_mod.object
    armature = armature_object.data
    bone_name_to_id = {b.name: i for i, b in enumerate(armature.bones)}


# Convert between z-up, righthanded and y-up, lefthanded
zup_to_yup = Matrix(
    np.array(
        [
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
        ]
    )
)


with open(tmm_output_filename, "wb") as tmm_file:
    me = ob.data
    me.calc_loop_triangles()
    me.calc_tangents()

    # Calculate some stuff first

    # Figure out the attachments
    attachments = []
    if armature_object:
        for empty in armature_object.children:
            if empty.data is None:
                if empty.parent_type == "BONE":
                    parent_id = list(armature.bones).index(
                        armature.bones[empty.parent_bone]
                    )
                else:
                    parent_id = -1

                attachments.append(
                    (re.sub(r"\.\d{3}$", "", empty.name), parent_id, empty.matrix_local)
                )

    # Build per-material tri groups
    material_groups = defaultdict(list)  # material_index -> list of polygon indices
    for tri in me.polygons:
        material_groups[tri.material_index].append(tri.index)

    total_vertices = 0
    total_triangles = 0
    mesh_groups = []
    for mat_index, tri_indices in material_groups.items():
        canon_vertex_list = []
        triangle_list = []
        for tri_index in tri_indices:
            tri = me.polygons[tri_index]

            winding_order = (
                (
                    (tri.vertices[0] > tri.vertices[1])
                    and (tri.vertices[1] > tri.vertices[2])
                )
                or (
                    (tri.vertices[1] > tri.vertices[2])
                    and (tri.vertices[2] > tri.vertices[0])
                )
                or (
                    (tri.vertices[2] > tri.vertices[0])
                    and (tri.vertices[0] > tri.vertices[1])
                )
            )

            triangle_vert_indices = [0, 0, 0]
            for i, loop_index in enumerate(tri.loop_indices):
                loop = me.loops[loop_index]
                vert_index = loop.vertex_index
                vert = me.vertices[vert_index]

                # uv
                uv = None
                if me.uv_layers.active is not None:
                    uv = me.uv_layers.active.data[loop_index].uv

                # normals, I don't understand
                n = loop.normal
                t = loop.tangent
                b = loop.bitangent

                # weights
                weight_items = []
                if armature_object is not None:
                    for g in vert.groups:
                        vg = ob.vertex_groups[g.group]
                        bone_id = bone_name_to_id.get(vg.name)
                        if bone_id is not None:
                            weight_items.append((bone_id, g.weight))
                    weight_items.sort(key=lambda x: x[1], reverse=True)
                    weight_items = weight_items[:4]
                    total_weight = sum(w for _, w in weight_items)
                    if total_weight > 0:
                        weight_items = [
                            (b, int(round(w / total_weight * 255)))
                            for b, w in weight_items
                        ]
                    else:
                        weight_items = []

                # candidate
                canon_vertex_candidate = (vert.co, uv, n, t, b, weight_items)
                # print(canon_vertex_candidate)

                # see if already exists
                try:
                    index_value = canon_vertex_list.index(canon_vertex_candidate)
                    triangle_vert_indices[i] = index_value
                except ValueError:
                    canon_vertex_list.append(canon_vertex_candidate)
                    triangle_vert_indices[i] = len(canon_vertex_list) - 1

            triangle_list.append(triangle_vert_indices)

        mesh_groups.append((mat_index, canon_vertex_list, triangle_list))
        total_vertices += len(canon_vertex_list)
        total_triangles += len(triangle_list)

    # Write the file

    # Header
    tmm_file.write(struct.pack("L", 1296913474))  # BTMM
    tmm_file.write(struct.pack("L", 35))  # version
    tmm_file.write(struct.pack("H", 20548))  # DP

    # "Import Crap"
    tmm_file.write(
        struct.pack("L", 4)
    )  # bytelength of the imports, 4 for the int below
    tmm_file.write(struct.pack("L", 0))  # (none)

    # Bounding Box(s)
    bb = (
        ob.bound_box[0][0],
        ob.bound_box[0][2],
        ob.bound_box[0][1],
        ob.bound_box[-2][0],
        ob.bound_box[-2][2],
        ob.bound_box[-2][1],
    )
    tmm_file.write(struct.pack("<ffffff", *bb))

    # bigger bounding box, probably depends on animations
    if armature_object is None:
        # no animations = same bb as above
        tmm_file.write(struct.pack("<ffffff", *bb))
    else:
        # looks like it could also be 3x height seems ok for animated
        big_bb_size = 3 * ob.bound_box[-2][2]
        tmm_file.write(
            struct.pack(
                "<ffffff",
                -big_bb_size,
                -big_bb_size,
                -big_bb_size,
                big_bb_size,
                big_bb_size,
                big_bb_size,
            )
        )

    # Unknown
    # Do the bounding box height for now
    tmm_file.write(struct.pack("f", ob.bound_box[-2][2]))  # unknown, some float

    tmm_file.write(struct.pack("L", len(mesh_groups)))  # mesh_groups
    tmm_file.write(struct.pack("L", len(material_groups)))  # materials
    tmm_file.write(struct.pack("L", 1))  # shader techniques
    tmm_file.write(
        struct.pack("L", 0 if armature_object is None else len(armature.bones))
    )  # bones
    tmm_file.write(struct.pack("L", 0))  # something
    tmm_file.write(struct.pack("L", len(attachments)))  # attachments
    tmm_file.write(struct.pack("L", total_vertices))  # vertices
    print(f"Total vertices: {total_vertices}")
    tmm_file.write(struct.pack("L", total_triangles * 3))  # triangle *vertices*
    print(f"Total triangles: {total_triangles}")

    # Block addresses and lengths in the tmm.data file
    tmm_file.write(struct.pack("L", 0))  # vertices_start
    tmm_file.write(struct.pack("L", total_vertices * 16))  # vertices_bytelength
    tmm_file.write(struct.pack("L", total_vertices * 16))  # triangles_start
    tmm_file.write(struct.pack("L", total_triangles * 3 * 2))  # triangles_bytelength
    tmm_file.write(
        struct.pack("L", total_vertices * 16 + total_triangles * 3 * 2)
    )  # weights_start
    tmm_file.write(struct.pack("L", total_vertices * 8))  # weights_bytelength
    tmm_file.write(struct.pack("LLLL", 0, 0, 0, 0))  # unknown blocks
    tmm_file.write(
        struct.pack(
            "L", total_vertices * 16 + total_triangles * 3 * 2 + total_vertices * 8
        )
    )  # heights_start
    tmm_file.write(struct.pack("L", total_vertices * 2))  # heights_bytelength
    tmm_file.write(struct.pack("LL", 0, 0))  # unknown block

    tmm_file.write(struct.pack("BB", 0, 1))  # bools maybe

    # 4x3 Transform matrix
    # Armature's transformation matrix gives this one
    # Also need to undo the righthanded/lefthanded correction thing...
    if armature_object:
        main_matrix = armature_object.matrix_basis @ zup_to_yup
        main_matrix_list = [f for row in main_matrix for f in row][:12]

        # main_matrix_inverted = main_matrix.inverted()
    else:
        main_matrix_list = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]
    tmm_file.write(struct.pack("ffffffffffff", *main_matrix_list))

    # Attachments
    print("Attachments:")
    for attachment in attachments:
        print(attachment[0])
        tmm_file.write(struct.pack("L", 0))  # some zero

        tmm_file.write(struct.pack("l", attachment[1]))  # parent_bone_id

        s = attachment[0]
        s_e = bytes(s, "UTF-16LE")
        tmm_file.write(struct.pack("<L%ds" % (len(s_e),), len(s), s_e))

        parent = armature.bones[attachment[1]]
        # print(parent.matrix_local)

        # 4x3 matrices
        # world and then parent?
        world_space_mat = attachment[2].copy()
        # print(world_space_mat)
        world_space_mat_list = [f for row in world_space_mat for f in row][:12]

        # Apparently it's just two of the same matrices?
        # Hey, I'm not complaining

        tmm_file.write(struct.pack("ffffffffffff", *world_space_mat_list))
        tmm_file.write(struct.pack("ffffffffffff", *world_space_mat_list))

        tmm_file.write(struct.pack("L", 0))  # some zero
        tmm_file.write(struct.pack("L", 0))  # some zero

        # duplicate of above string, not clear when it should be here though
        tmm_file.write(struct.pack("L", 0))
        # tmm_file.write(struct.pack("<L%ds" % (len(s_e),), len(s), s_e))

        tmm_file.write(struct.pack("llll", -1, 0, 0, 0))  # some weird thing

    # Mesh groups
    verts_offset = 0
    tris_offset = 0
    for mesh_group in mesh_groups:
        tmm_file.write(struct.pack("L", verts_offset))  # vertices start
        tmm_file.write(struct.pack("L", tris_offset))  # triangles start

        tmm_file.write(struct.pack("L", len(mesh_group[1])))  # num vertices in group
        tmm_file.write(
            struct.pack("L", len(mesh_group[2]) * 3)
        )  # num triangle *vertice* in group

        tmm_file.write(struct.pack("L", mesh_group[0]))  # material index
        tmm_file.write(struct.pack("L", 1))  # shader technique index (1 for default)

        verts_offset += len(mesh_group[1])
        tris_offset += len(mesh_group[2]) * 3

    # Materials
    materials = ob.data.materials
    for material in materials:
        s = material.name
        s_e = bytes(s, "UTF-16LE")
        tmm_file.write(struct.pack("<L%ds" % (len(s_e),), len(s), s_e))

    # Shader techniques
    # "default" only, for simplicity
    techs = ["default"]
    for tech in techs:
        s2 = tech
        s2_e = bytes(s2, "UTF-16LE")
        tmm_file.write(struct.pack("<L%ds" % (len(s2_e),), len(s2), s2_e))

    # Bones
    # These can be different from the animation's skeleton, factoring in scale
    print("Exporting bind pose skeleton:")
    if armature_object is not None:
        # Apply the armature's transformation
        # armature.transform(main_matrix)

        bones = armature.bones
        for bone in bones:
            print(f"  Bone: {bone.name}")
            s3 = bone.name
            s3_e = bytes(s3, "UTF-16LE")
            tmm_file.write(struct.pack("<L%ds" % (len(s3_e),), len(s3), s3_e))

            parent = bone.parent
            if parent is not None:
                parent_index = list(bones).index(bones[bone.parent.name])
            else:
                parent_index = -1
            tmm_file.write(struct.pack("l", parent_index))  # parent_id

            tmm_file.write(
                struct.pack("fff", 0, 0, 0)
            )  # possibly bone collision offset (xyz)
            tmm_file.write(
                struct.pack("f", bone.head_radius)
            )  # bone radius, used for collision

            # 4x4 world space
            world_space_mat = bone.matrix_local

            # I don't really get it, but apply this to the root bones
            # if parent_index == -1:
            print(world_space_mat)
            print(main_matrix)
            print(world_space_mat @ main_matrix)
            world_space_mat = main_matrix @ world_space_mat

            world_space_mat_list = [
                f for row in world_space_mat.transposed() for f in row
            ]

            # this is giving the wrong thing, the locations are too big
            # it's like we want this without the armature's transformation applied...
            # 4x4 parent space
            try:
                parent_space_mat = parent.matrix_local.inverted() @ bone.matrix_local
            except AttributeError:
                parent_space_mat = world_space_mat
            parent_space_mat_list = [
                f for row in parent_space_mat.transposed() for f in row
            ]

            # 4x4 inverse bind pose
            inverse_bind_mat = world_space_mat.inverted()
            inverse_bind_mat_list = [
                f for row in inverse_bind_mat.transposed() for f in row
            ]

            # parent(?) space 4x4
            tmm_file.write(struct.pack("ffffffffffffffff", *parent_space_mat_list))
            # world(?) space 4x4
            tmm_file.write(struct.pack("ffffffffffffffff", *world_space_mat_list))
            # inverse bind pose
            tmm_file.write(struct.pack("ffffffffffffffff", *inverse_bind_mat_list))

    # Some List, Sound positions maybe? References to animations?
    tmm_file.write(struct.pack("L", 0))  # (none) for now

    # There's a bool in here and it's a whole thing
    # Don't really understand it, but I'm pretty sure only weighted models have it
    if armature_object is not None:
        tmm_file.write(struct.pack("BBBB", 0, 0, 0, 0))

    tmm_file.write(struct.pack("B", 0))  # unknown, zero
    tmm_file.write(struct.pack("H", 22614))  # VX
    tmm_file.write(struct.pack("L", 1))  # unknown, one

    # this is a boolean that leads into the weirdest *side*-projected heightmap thing (for buildings)
    # I really hope it's not necessary, because that's probably going to involve some texture baking
    tmm_file.write(struct.pack("B", 0))

    # End of tmm file

    # And then write the .tmm.data file
    with open(tmm_output_filename + ".data", "wb") as tmm_data_file:
        # Vertices
        for mesh_group in mesh_groups:
            vert_list = mesh_group[1]
            for vert in vert_list:
                (coord, uv, _, _, _, _) = vert

                # position
                x, y, z = coord

                # uv
                u, v = 0, 0
                if uv is not None:
                    u, v = uv

                # n, t, bt = 16383,16383,16383 #blender-y-facing
                n, t, bt = 8191, 24575, 24575  # blender-z-facing
                # I dunno what's going on here, but this supposedly z-facing thing looks pretty good in-game (okay, not really)

                tmm_data_file.write(struct.pack("<eee", x, z, y))  # -x, y and z swapped
                tmm_data_file.write(struct.pack("<ee", u, 1 - v))  # v inverted
                tmm_data_file.write(struct.pack("<HHH", n, t, bt))

        # Triangles
        for mesh_group in mesh_groups:
            tri_list = mesh_group[2]
            for tri in tri_list:
                tri_flipped = (tri[0], tri[2], tri[1])
                tmm_data_file.write(struct.pack("<HHH", *tri_flipped))

        # Weights
        if armature_object is not None:
            for mesh_group in mesh_groups:
                vert_list = mesh_group[1]
                for vert in vert_list:
                    (_, _, _, _, _, weights) = vert

                    padded_bws = [(0, 0)] * (4 - len(weights)) + weights

                    for _, w in padded_bws:
                        tmm_data_file.write(struct.pack("<B", w))
                    for b, _ in padded_bws:
                        tmm_data_file.write(struct.pack("<B", b))

        # Vertex heights
        for mesh_group in mesh_groups:
            vert_list = mesh_group[1]
            for vert in vert_list:
                (coord, _, _, _, _, _) = vert
                tmm_data_file.write(struct.pack("<e", coord[1]))
