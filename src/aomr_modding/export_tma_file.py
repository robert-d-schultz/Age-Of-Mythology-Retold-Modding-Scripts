#!/usr/bin/env python3
import math
import os
import struct

import bpy

os.system("cls")

"""
TODO:
Remove "inactive" bones from the data list
Use "static" mode for bones that are static (this one will reduce
file size by like 50%)
Figure out the attachments thing (keyframes for when attachments turn on/off?)
"""

tma_output_filename = "./output.tma"

# Load animation onto selected armature
armature_object = bpy.context.active_object
if not armature_object:
    raise Exception("Select an armature!")
armature = armature_object.data
bones = armature.bones
pose = armature_object.pose

with open(tma_output_filename, "wb") as tma_file:
    print("Exporting animation")

    # Header
    tma_file.write(struct.pack("L", 1095586882))  # BTMA
    tma_file.write(struct.pack("L", 12))  # version
    tma_file.write(struct.pack("H", 20548))  # DP

    # "Import Crap"
    tma_file.write(
        struct.pack("L", 4)
    )  # bytelength of the imports, 4 for the int below
    tma_file.write(struct.pack("L", 0))  # (none)

    # "active_bone_count", assume all are active for now
    tma_file.write(struct.pack("L", len(bones)))

    frame_count = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
    print(f"Number of frames: {frame_count}")
    tma_file.write(struct.pack("L", frame_count))

    fps = bpy.context.scene.render.fps
    fps_base = bpy.context.scene.render.fps_base
    print(f"FPS: {fps / fps_base}")
    tma_file.write(struct.pack("f", frame_count / (fps / fps_base)))

    # Root position x2
    tma_file.write(struct.pack("fff", *bones[0].head))
    tma_file.write(struct.pack("fff", *bones[0].head))

    tma_file.write(struct.pack("L", len(bones)))

    # Attachments, TODO
    tma_file.write(struct.pack("L", 0))

    # Skeleton
    for bone in bones:
        s3 = bone.name
        s3_e = bytes(s3, "UTF-16LE")
        tma_file.write(struct.pack("<L%ds" % (len(s3_e),), len(s3), s3_e))

        parent = bone.parent
        if parent is not None:
            parent_index = list(bones).index(bones[bone.parent.name])
        else:
            parent_index = -1
        tma_file.write(struct.pack("l", parent_index))

        # 4x4 world space
        world_space_mat = bone.matrix_local
        world_space_mat_list = [f for row in world_space_mat.transposed() for f in row]

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

        # parent space 4x4
        tma_file.write(struct.pack("ffffffffffffffff", *parent_space_mat_list))
        # world space 4x4
        tma_file.write(struct.pack("ffffffffffffffff", *world_space_mat_list))
        # inverse bind pose
        tma_file.write(struct.pack("ffffffffffffffff", *inverse_bind_mat_list))

    # Animation Data

    # Dunno if this is even necessary
    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_obj_eval = armature_object.evaluated_get(depsgraph)

    for pose_bone in arm_obj_eval.pose.bones:
        print(f"Writing animation data for bone {pose_bone.name}")

        s3 = pose_bone.name
        s3_e = bytes(s3, "UTF-16LE")
        tma_file.write(struct.pack("<L%ds" % (len(s3_e),), len(s3), s3_e))
        tma_file.write(struct.pack("b", 1))  # unknown
        tma_file.write(struct.pack("b", 1))  # position_mode
        tma_file.write(struct.pack("b", 3))  # rotation_mode
        tma_file.write(struct.pack("b", 0))  # unknown

        tma_file.write(struct.pack("L", frame_count))

        # Assume normal modes, for now
        # Position
        tma_file.write(struct.pack("L", frame_count * 12))  # positiondata_bytelength
        for i in range(frame_count):
            bpy.context.scene.frame_set(i)
            # calling it twice fixes... something? maybe?
            bpy.context.scene.frame_set(i)
            # go to frame i and sample the x,y,z of the bone
            # tma_file.write(struct.pack("fff", *pose_bone.location))
            tma_file.write(struct.pack("fff", *pose_bone.matrix_basis.to_translation()))

        # Rotations
        tma_file.write(struct.pack("L", frame_count * 8))  # positiondata_bytelength
        for i in range(frame_count):
            bpy.context.scene.frame_set(i)
            # calling it twice fixes... something? maybe?
            bpy.context.scene.frame_set(i)

            # w, x, y, z = pose_bone.rotation_quaternion
            w, x, y, z = pose_bone.matrix_basis.to_quaternion()

            # Rearrange a little
            components = [w, z, y, x]

            abs_components = [abs(c) for c in components]
            # Index of largest component
            max_index = abs_components.index(max(abs_components))
            max_component = components[max_index]

            # If the largest component is negative, flip all signs
            if max_component < 0:
                components = [-c for c in components]

            # Drop the largest component
            remaining = [components[i] for i in range(4) if i != max_index]

            # Map range [-1/sqrt(2), 1/sqrt(2)] to [-1, 1]
            scale = math.sqrt(2)
            scaled = [c * scale for c in remaining]
            # Max index is actually stored backwards
            max_index = 3 - max_index

            # Encode each component: sign bit + 19-bit unsigned magnitude
            compressed = 0
            bit_offset = 0
            for i, c in enumerate(scaled):
                # Weird thing, deal with it
                c *= 1 if (i == 0 or max_index == 3) else -1
                sign_bit = 0 if c < 0 else 1
                # Map [0,1] to [0, 2^19 - 1]
                magnitude = int(min(abs(c), 1.0) * ((1 << 19) - 1))
                compressed |= (magnitude & 0x7FFFF) << bit_offset  # 19 bits
                bit_offset += 19
                compressed |= (sign_bit & 0x1) << bit_offset  # 1 bit
                bit_offset += 1

            # Add 2 bits for dropped component index
            compressed |= (max_index & 0x3) << bit_offset
            bit_offset += 2

            # Add 2 bits padding (left as 0)
            compressed |= (0 & 0x3) << bit_offset

            # Write to file
            tma_file.write(struct.pack("Q", compressed))

        tma_file.write(struct.pack("ffff", 1, 1, 1, 1))

    # Attachment things
    tma_file.write(struct.pack("L", 0))

    # Unknown
    tma_file.write(struct.pack("L", 0))

    # End of tma file
