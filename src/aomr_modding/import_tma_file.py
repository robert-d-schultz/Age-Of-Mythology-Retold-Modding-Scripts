#!/usr/bin/env python3
import math
import os
import struct

import bpy
import mathutils
from mathutils import Matrix
import numpy as np

os.system("cls")

tma_filename = "/path/to/tma_file.tma"


# Load animation onto selected armature, otherwise, make a new one
armature_object = bpy.context.active_object
if not armature_object:
    print("No active object selected. A new armature will be created.")
    armature_object = None
elif armature_object.type != "ARMATURE":
    print(
        f"Active object '{armature_object.name}' is not an armature. "
        f"It will be ignored and a new armature will be created."
    )
    armature_object = None
else:
    print(f"Armature '{armature_object.name}' selected. Attempting to load animation.")
    armature = armature_object.data


# Collection
try:
    anim_collection = bpy.data.collections["imported"]
except KeyError:
    anim_collection = bpy.data.collections.new("imported")
    bpy.context.scene.collection.children.link(anim_collection)


# Set-up new armature if needed
anim_name = os.path.splitext(os.path.basename(tma_filename))[0]
if armature_object is None:
    armature_name = anim_name.split("_")[0] + "_armature"  # Might be neat?
    armature = bpy.data.armatures.new(armature_name)
    armature_object = bpy.data.objects.new(armature_name, armature)
    anim_collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object

    # A nice simple solution to the axis and handedness problem (maybe?)
    armature_object.rotation_euler = (-math.pi / 2, 0, 0)  # "swap the y and z axes"
    armature_object.scale = (1, -1, 1)  # "change from left to right-handed coordinates"


# Set-up new action if needed
if anim_name in bpy.data.actions:
    print(f"  Found existing action {anim_name}")
    action = bpy.data.actions[anim_name]
else:
    print(f"  Creating new action {anim_name}")
    action = bpy.data.actions.new(anim_name)
armature_object.animation_data_create()
armature_object.animation_data.action = action


with open(tma_filename, "rb") as anim_file:
    # Header
    BTMA = struct.unpack("<L", anim_file.read(4))[0]
    assert BTMA == 1095586882, BTMA
    version = struct.unpack("<L", anim_file.read(4))[0]
    assert version == 12, version
    DP = struct.unpack("<H", anim_file.read(2))[0]
    assert DP == 20548, DP

    # "Import Crap", probably things like export dates and WIP filenames, truly not important
    import_block_length = struct.unpack("<L", anim_file.read(4))[0]  # byte length
    anim_file.seek(import_block_length, 1)

    # Useful Stuff
    num_active_bones = struct.unpack("<L", anim_file.read(4))[0]

    num_frames_global = struct.unpack("<L", anim_file.read(4))[0]
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = num_frames_global - 1

    animation_playtime = struct.unpack("<f", anim_file.read(4))[0]
    bpy.context.scene.render.fps = num_frames_global
    bpy.context.scene.render.fps_base = animation_playtime

    # position of the root bone, x2
    _, _, _ = struct.unpack("<fff", anim_file.read(12))
    _, _, _ = struct.unpack("<fff", anim_file.read(12))

    num_bones = struct.unpack("<L", anim_file.read(4))[0]
    assert num_active_bones <= num_bones, (
        f"More active bones ({num_active_bones}) "
        f"than total bones ({num_bones}), impossible."
    )

    # number of attachment things at the very end, we don't support this yet
    num_attachs = struct.unpack("<L", anim_file.read(4))[0]

    # Bind Pose
    print("Setting up armature")
    bone_list = []
    for i in range(num_bones):
        bone_name_length = struct.unpack("<L", anim_file.read(4))[0] * 2
        bone_name = anim_file.read(bone_name_length).decode("UTF-16-LE")
        bone_parent_index = struct.unpack("<L", anim_file.read(4))[0]
        try:
            bone_list.append((bone_name, bone_list[bone_parent_index][0]))
        except IndexError:
            bone_list.append((bone_name, ""))

        parent_space_matrix = struct.unpack("<ffffffffffffffff", anim_file.read(64))
        world_space_matrix = struct.unpack("<ffffffffffffffff", anim_file.read(64))
        inverse_bind_matrix = struct.unpack("<ffffffffffffffff", anim_file.read(64))

        print(f"  Bone {bone_name}")

        world_space_matrix = Matrix(np.array(world_space_matrix).reshape(4, 4))
        world_space_matrix.transpose()

        bpy.ops.object.mode_set(mode="EDIT", toggle=False)  # Enter edit mode
        ebs = armature.edit_bones
        try:
            eb = ebs[bone_name]
            print("    Already in armature, skipping")
        except KeyError:
            print("    Not in the armature, adding")
            eb = ebs.new(bone_name)
            if i > 0:
                try:
                    eb.parent = armature.edit_bones[bone_list[i][1]]
                except KeyError:
                    raise Exception("    No parent found, impossible.")
            else:
                pass

            # These have proper values in the .tmm, but not here in the .tma
            eb.head_radius = -1
            eb.tail_radius = -1

            eb.tail = (0.0, 0.2, 0.0)

            eb.matrix = world_space_matrix

        bpy.ops.object.mode_set(mode="OBJECT")  # Exit edit mode

    # Keyframe Data
    print("Reading keyframe data")
    for _ in range(num_active_bones):
        bone_name_length = struct.unpack("<L", anim_file.read(4))[0] * 2
        bone_name = anim_file.read(bone_name_length).decode("UTF-16-LE")
        print(f"  Bone: {bone_name}")

        unknown_one = struct.unpack("<B", anim_file.read(1))[0]
        assert unknown_one == 1, "  Shouldn't this always be 1? byte: " + str(
            anim_file.tell()
        )

        position_mode = struct.unpack("<B", anim_file.read(1))[
            0
        ]  # 1=normal, 0=static position
        rotation_mode = struct.unpack("<B", anim_file.read(1))[
            0
        ]  # 3=normal, 0=static rotation

        unknown_zero = struct.unpack("<B", anim_file.read(1))[0]
        assert unknown_zero == 0, "  Shouldn't this always be 0? byte: " + str(
            anim_file.tell()
        )

        num_frames = struct.unpack("<L", anim_file.read(4))[0]
        assert num_frames == num_frames_global, (
            "  num_frames doesn't match num_frames_global"
        )

        # Positions
        translations = []
        if position_mode == 0:
            static_x, static_y, static_z = struct.unpack("fff", anim_file.read(12))
            anim_file.read(4)  # seems to always be 1, unused?
            translations.extend([(static_x, static_y, static_z)] * num_frames)
        elif position_mode == 1:
            anim_file.read(4)  # position bytelength
            for frame_num in range(num_frames):
                (x_pos, y_pos, z_pos) = struct.unpack("<fff", anim_file.read(12))
                translations.append((x_pos, y_pos, z_pos))
        else:
            raise Exception("  Unknown position mode")

        # Rotations
        def read_rotation(raw):
            # There's two bits at the end that seem to just be padding (always 0)
            a_chunk = (raw >> 0) & 0xFFFFF  # bits 0–19
            b_chunk = (raw >> 20) & 0xFFFFF  # bits 20–39
            c_chunk = (raw >> 40) & 0xFFFFF  # bits 40–59
            recon = (raw >> 60) & 0x3  # index of w,x,y,z to reconstruct

            a = a_chunk & 0x7FFFF
            b = b_chunk & 0x7FFFF
            c = c_chunk & 0x7FFFF

            # print(a,b,c)
            norm_scale = 1 / ((2**19) - 1)
            quat_factor = 1 / math.sqrt(2)
            a, b, c = (
                min(a * norm_scale * quat_factor, 1),
                min(b * norm_scale * quat_factor, 1),
                min(c * norm_scale * quat_factor, 1),
            )

            sign_a = 1 if (a_chunk & 0x80000) else -1
            sign_b = 1 if (b_chunk & 0x80000) else -1
            sign_c = 1 if (c_chunk & 0x80000) else -1
            a *= sign_a
            b *= sign_b
            c *= sign_c

            # print(a,b,c)
            d = min(math.sqrt(max(0.0, 1.0 - (a**2) - (b**2) - (c**2))), 1)

            # I'm not sure what's up with these negative signs
            # Negating B and C fixes everything? Except the last case?
            w, z, y, x = 0, 0, 0, 0
            if recon == 0:  # reconstructed x
                w, z, y, x = a, -b, -c, d
            elif recon == 1:  # reconstructed y
                w, z, y, x = a, -b, d, -c
            elif recon == 2:  # reconstructed z
                w, z, y, x = a, d, -b, -c
            elif recon == 3:  # reconstructed w
                w, z, y, x = d, a, b, c

            # print(w,x,y,z)

            quaternion = mathutils.Quaternion((w, x, y, z))

            return quaternion

        rotations = []
        if rotation_mode == 0:
            static_z, static_y, static_x, static_w = struct.unpack(
                "ffff", anim_file.read(16)
            )
            rotations.extend(
                [mathutils.Quaternion((-static_w, static_z, static_y, static_x))]
                * num_frames
            )
        elif rotation_mode == 3:
            anim_file.read(4)  # rotation bytelength
            for i in range(num_frames):
                raw = struct.unpack("Q", anim_file.read(8))[0]
                rot = read_rotation(raw)

                # Do this to clean-up how the graphs look
                # Negating a quaternion otherwise does nothing
                try:
                    if rotations[i - 1].dot(rot) < 0:
                        rot.negate()
                except Exception:
                    pass

                rotations.append(rot)
        else:
            raise Exception("  Unknown rotation mode")

        # Weird floats at end
        struct.unpack("<ffff", anim_file.read(16))

        assert len(translations) == len(rotations)

        # Put it together
        try:
            pb = armature_object.pose.bones[bone_name]
            for frame_num in range(num_frames):
                bpy.context.scene.frame_set(frame_num)
                bpy.context.scene.frame_set(frame_num)

                pb.location = translations[frame_num]

                pb.rotation_quaternion = rotations[frame_num]

                pb.keyframe_insert(data_path="location", frame=frame_num)
                pb.keyframe_insert(data_path="rotation_quaternion", frame=frame_num)
        except KeyError:
            # Not even sure how'd you get in this position
            print(f"  No bone {bone_name} in the armature")

    # Attachment Keyframes (not supported yet)
    # As far as I can tell, these are like "attachment A is disabled at 0.35 seconds"
    # I haven't looked into this very well, and I'm not sure the best way to implement here in Blender
    num_attachs = struct.unpack("<L", anim_file.read(4))[0]
    for _ in range(num_attachs):
        parent_bone_id = struct.unpack("<L", anim_file.read(4))[0]  # possibly
        time = struct.unpack("<f", anim_file.read(4))[
            0
        ]  # doesn't make sense as time in seconds, could be % of frames
        anim_file.read(4)  # zero
        anim_file.read(4)  # zero
        anim_file.read(1)  # bool? visibility? who knows
        attach_name_length = struct.unpack("<L", anim_file.read(4))[0] * 2
        attach_name = anim_file.read(attach_name_length).decode("UTF-16-LE")

    # And another list of something or other, haven't seen what it is yet
    unknown_zero = struct.unpack("<L", anim_file.read(4))[0]  # unknown
    assert unknown_zero == 0

    # End of .tma file
