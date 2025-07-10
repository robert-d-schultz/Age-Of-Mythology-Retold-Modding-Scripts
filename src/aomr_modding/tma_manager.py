#!/usr/bin/env python3
"""
TMA (Animation) File Manager

This module provides classes for managing Age of Mythology Retold TMA files.
TMA files contain animation data for armatures.
"""

from dataclasses import dataclass
import math
import os
import struct
from typing import Any

import bpy
from mathutils import Matrix, Quaternion
import numpy as np


@dataclass
class TMAHeader:
    """TMA file header information."""
    magic: int  # BTMA (1095586882)
    version: int  # Usually 12
    dp: int  # Usually 20548


@dataclass
class TMABone:
    """Represents a bone in the TMA file."""
    name: str
    parent_index: int
    parent_space_matrix: Matrix
    world_space_matrix: Matrix
    inverse_bind_matrix: Matrix


@dataclass
class TMAAnimationData:
    """Represents animation data for a bone."""
    bone_name: str
    position_mode: int  # 0=static, 1=normal
    rotation_mode: int  # 0=static, 3=normal
    translations: list[tuple[float, float, float]]
    rotations: list[Quaternion]


@dataclass
class TMAFile:
    """Complete TMA file structure."""
    header: TMAHeader
    active_bone_count: int
    frame_count: int
    animation_duration: float
    root_position: tuple[float, float, float]
    bones: list[TMABone]
    animations: list[TMAAnimationData]
    attachments: list[Any]  # TODO: Define attachment structure


class TMAReader:
    """Reads TMA files and converts them to TMAFile objects."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> TMAFile:
        """Read and parse a TMA file."""
        with open(self.filepath, "rb") as f:
            return self._parse_file(f)

    def _parse_file(self, f) -> TMAFile:
        """Parse the TMA file content."""
        # Header
        header = self._read_header(f)

        # Import block
        self._skip_import_block(f)

        # Animation info
        active_bone_count = struct.unpack("<L", f.read(4))[0]
        frame_count = struct.unpack("<L", f.read(4))[0]
        animation_duration = struct.unpack("<f", f.read(4))[0]

        # Root position (read twice)
        root_pos1 = struct.unpack("<fff", f.read(12))
        root_pos2 = struct.unpack("<fff", f.read(12))
        root_position = root_pos1  # Use first one

        # Bone count
        bone_count = struct.unpack("<L", f.read(4))[0]
        attachment_count = struct.unpack("<L", f.read(4))[0]

        # Read bones
        bones = self._read_bones(f, bone_count)

        # Read animation data
        animations = self._read_animations(f, active_bone_count, frame_count)

        # Read attachments (placeholder)
        attachments = self._read_attachments(f, attachment_count)

        return TMAFile(
            header=header,
            active_bone_count=active_bone_count,
            frame_count=frame_count,
            animation_duration=animation_duration,
            root_position=root_position,
            bones=bones,
            animations=animations,
            attachments=attachments
        )

    def _read_header(self, f) -> TMAHeader:
        """Read the TMA file header."""
        magic = struct.unpack("<L", f.read(4))[0]
        assert magic == 1095586882, f"Invalid TMA magic: {magic}"

        version = struct.unpack("<L", f.read(4))[0]
        dp = struct.unpack("<H", f.read(2))[0]

        return TMAHeader(magic=magic, version=version, dp=dp)

    def _skip_import_block(self, f):
        """Skip the import block."""
        import_length = struct.unpack("<L", f.read(4))[0]
        f.seek(import_length, 1)

    def _read_bones(self, f, bone_count: int) -> list[TMABone]:
        """Read bone definitions."""
        bones = []
        for _ in range(bone_count):
            name_length = struct.unpack("<L", f.read(4))[0] * 2
            name = f.read(name_length).decode("UTF-16-LE")
            parent_index = struct.unpack("<l", f.read(4))[0]

            # Read matrices
            parent_space = self._read_matrix(f)
            world_space = self._read_matrix(f)
            inverse_bind = self._read_matrix(f)

            bones.append(TMABone(
                name=name,
                parent_index=parent_index,
                parent_space_matrix=parent_space,
                world_space_matrix=world_space,
                inverse_bind_matrix=inverse_bind
            ))

        return bones

    def _read_matrix(self, f) -> Matrix:
        """Read a 4x4 matrix from the file."""
        matrix_data = struct.unpack("<ffffffffffffffff", f.read(64))
        matrix = Matrix(np.array(matrix_data).reshape(4, 4))
        matrix.transpose()  # TMA matrices are stored transposed
        return matrix

    def _read_animations(self, f, active_bone_count: int, frame_count: int) -> list[TMAAnimationData]:
        """Read animation data for all active bones."""
        animations = []

        for _ in range(active_bone_count):
            # Bone name
            name_length = struct.unpack("<L", f.read(4))[0] * 2
            bone_name = f.read(name_length).decode("UTF-16-LE")

            # Animation modes
            unknown1 = struct.unpack("<B", f.read(1))[0]
            position_mode = struct.unpack("<B", f.read(1))[0]
            rotation_mode = struct.unpack("<B", f.read(1))[0]
            unknown2 = struct.unpack("<B", f.read(1))[0]

            # Frame count
            anim_frame_count = struct.unpack("<L", f.read(4))[0]
            assert anim_frame_count == frame_count

            # Read translations
            translations = self._read_translations(f, position_mode, frame_count)

            # Read rotations
            rotations = self._read_rotations(f, rotation_mode, frame_count)

            # Skip scale data
            f.read(16)  # 4 floats

            animations.append(TMAAnimationData(
                bone_name=bone_name,
                position_mode=position_mode,
                rotation_mode=rotation_mode,
                translations=translations,
                rotations=rotations
            ))

        return animations

    def _read_translations(self, f, position_mode: int, frame_count: int) -> list[tuple[float, float, float]]:
        """Read translation data."""
        if position_mode == 0:  # Static
            static_pos = struct.unpack("<fff", f.read(12))
            f.read(4)  # Skip unused
            return [static_pos] * frame_count
        if position_mode == 1:  # Normal
            f.read(4)  # Skip byte length
            translations = []
            for _ in range(frame_count):
                pos = struct.unpack("<fff", f.read(12))
                translations.append(pos)
            return translations
        raise ValueError(f"Unknown position mode: {position_mode}")

    def _read_rotations(self, f, rotation_mode: int, frame_count: int) -> list[Quaternion]:
        """Read rotation data."""
        if rotation_mode == 0:  # Static
            # Read static rotation (implementation needed)
            raise NotImplementedError("Static rotation mode not implemented")
        if rotation_mode == 3:  # Normal
            f.read(4)  # Skip byte length
            rotations = []
            for _ in range(frame_count):
                compressed = struct.unpack("<Q", f.read(8))[0]
                quat = self._decompress_quaternion(compressed)
                rotations.append(quat)
            return rotations
        raise ValueError(f"Unknown rotation mode: {rotation_mode}")

    def _decompress_quaternion(self, compressed: int) -> Quaternion:
        """Decompress a quaternion from the TMA format."""
        # Extract components
        a_chunk = (compressed >> 0) & 0xFFFFF
        b_chunk = (compressed >> 20) & 0xFFFFF
        c_chunk = (compressed >> 40) & 0xFFFFF
        max_index = (compressed >> 60) & 0x3

        # Decode components
        a = (a_chunk & 0x7FFFF) / ((1 << 19) - 1)
        b = (b_chunk & 0x7FFFF) / ((1 << 19) - 1)
        c = (c_chunk & 0x7FFFF) / ((1 << 19) - 1)

        # Apply signs
        if a_chunk & 0x80000:
            a = -a
        if b_chunk & 0x80000:
            b = -b
        if c_chunk & 0x80000:
            c = -c

        # Scale back
        scale = math.sqrt(2)
        a /= scale
        b /= scale
        c /= scale

        # Reconstruct quaternion
        components = [0.0, 0.0, 0.0, 0.0]
        remaining_indices = [i for i in range(4) if i != max_index]
        components[remaining_indices[0]] = a
        components[remaining_indices[1]] = b
        components[remaining_indices[2]] = c

        # Calculate the missing component
        sum_sq = a*a + b*b + c*c
        if sum_sq <= 1.0:
            components[max_index] = math.sqrt(1.0 - sum_sq)
        else:
            # Normalize if needed
            norm = math.sqrt(sum_sq)
            components = [x/norm for x in components]
            components[max_index] = 0.0

        # Convert to Blender quaternion (w, x, y, z)
        w, x, y, z = components
        return Quaternion((w, x, y, z))

    def _read_attachments(self, f, attachment_count: int) -> list[Any]:
        """Read attachment data (placeholder)."""
        # TODO: Implement attachment reading
        f.seek(attachment_count * 8, 1)  # Skip for now
        return []


class TMAWriter:
    """Writes TMAFile objects to TMA files."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def write(self, tma_data: TMAFile):
        """Write a TMAFile object to a TMA file."""
        with open(self.filepath, "wb") as f:
            self._write_file(f, tma_data)

    def _write_file(self, f, tma_data: TMAFile):
        """Write the TMA file content."""
        # Header
        self._write_header(f, tma_data.header)

        # Import block
        self._write_import_block(f)

        # Animation info
        f.write(struct.pack("<L", tma_data.active_bone_count))
        f.write(struct.pack("<L", tma_data.frame_count))
        f.write(struct.pack("<f", tma_data.animation_duration))

        # Root position (write twice)
        f.write(struct.pack("<fff", *tma_data.root_position))
        f.write(struct.pack("<fff", *tma_data.root_position))

        # Bone count
        f.write(struct.pack("<L", len(tma_data.bones)))
        f.write(struct.pack("<L", len(tma_data.attachments)))

        # Write bones
        self._write_bones(f, tma_data.bones)

        # Write animation data
        self._write_animations(f, tma_data.animations)

        # Write attachments
        self._write_attachments(f, tma_data.attachments)

    def _write_header(self, f, header: TMAHeader):
        """Write the TMA file header."""
        f.write(struct.pack("<L", header.magic))
        f.write(struct.pack("<L", header.version))
        f.write(struct.pack("<H", header.dp))

    def _write_import_block(self, f):
        """Write the import block."""
        f.write(struct.pack("<L", 4))  # Length
        f.write(struct.pack("<L", 0))  # No imports

    def _write_bones(self, f, bones: list[TMABone]):
        """Write bone definitions."""
        for bone in bones:
            # Write name
            name_bytes = bone.name.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(bone.name)))
            f.write(name_bytes)

            # Write parent index
            f.write(struct.pack("<l", bone.parent_index))

            # Write matrices
            self._write_matrix(f, bone.parent_space_matrix)
            self._write_matrix(f, bone.world_space_matrix)
            self._write_matrix(f, bone.inverse_bind_matrix)

    def _write_matrix(self, f, matrix: Matrix):
        """Write a 4x4 matrix to the file."""
        matrix.transpose()  # TMA matrices are stored transposed
        matrix_data = [f for row in matrix for f in row]
        f.write(struct.pack("<ffffffffffffffff", *matrix_data))
        matrix.transpose()  # Restore original orientation

    def _write_animations(self, f, animations: list[TMAAnimationData]):
        """Write animation data."""
        for anim in animations:
            # Write bone name
            name_bytes = anim.bone_name.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(anim.bone_name)))
            f.write(name_bytes)

            # Write modes
            f.write(struct.pack("<B", 1))  # Unknown
            f.write(struct.pack("<B", anim.position_mode))
            f.write(struct.pack("<B", anim.rotation_mode))
            f.write(struct.pack("<B", 0))  # Unknown

            # Write frame count
            f.write(struct.pack("<L", len(anim.translations)))

            # Write translations
            self._write_translations(f, anim.translations, anim.position_mode)

            # Write rotations
            self._write_rotations(f, anim.rotations, anim.rotation_mode)

            # Write scale data
            f.write(struct.pack("<ffff", 1.0, 1.0, 1.0, 1.0))

    def _write_translations(self, f, translations: list[tuple[float, float, float]], position_mode: int):
        """Write translation data."""
        if position_mode == 0:  # Static
            f.write(struct.pack("<fff", *translations[0]))
            f.write(struct.pack("<L", 1))  # Unused
        elif position_mode == 1:  # Normal
            f.write(struct.pack("<L", len(translations) * 12))  # Byte length
            for trans in translations:
                f.write(struct.pack("<fff", *trans))

    def _write_rotations(self, f, rotations: list[Quaternion], rotation_mode: int):
        """Write rotation data."""
        if rotation_mode == 0:  # Static
            raise NotImplementedError("Static rotation mode not implemented")
        if rotation_mode == 3:  # Normal
            f.write(struct.pack("<L", len(rotations) * 8))  # Byte length
            for quat in rotations:
                compressed = self._compress_quaternion(quat)
                f.write(struct.pack("<Q", compressed))

    def _compress_quaternion(self, quat: Quaternion) -> int:
        """Compress a quaternion to the TMA format."""
        # Convert to w, x, y, z order
        w, x, y, z = quat.w, quat.x, quat.y, quat.z

        # Find the largest component
        components = [w, x, y, z]
        abs_components = [abs(c) for c in components]
        max_index = abs_components.index(max(abs_components))
        max_component = components[max_index]

        # If largest component is negative, flip all signs
        if max_component < 0:
            components = [-c for c in components]

        # Remove the largest component
        remaining = [components[i] for i in range(4) if i != max_index]

        # Scale to [-1/sqrt(2), 1/sqrt(2)]
        scale = math.sqrt(2)
        scaled = [c * scale for c in remaining]

        # Encode components
        compressed = 0
        bit_offset = 0

        for i, c in enumerate(scaled):
            # Apply sign correction
            c *= 1 if (i == 0 or max_index == 3) else -1

            # Encode magnitude and sign
            sign_bit = 0 if c < 0 else 1
            magnitude = int(min(abs(c), 1.0) * ((1 << 19) - 1))

            compressed |= (magnitude & 0x7FFFF) << bit_offset
            bit_offset += 19
            compressed |= (sign_bit & 0x1) << bit_offset
            bit_offset += 1

        # Add max index (reversed)
        compressed |= ((3 - max_index) & 0x3) << bit_offset
        bit_offset += 2

        # Add padding
        compressed |= (0 & 0x3) << bit_offset

        return compressed

    def _write_attachments(self, f, attachments: list[Any]):
        """Write attachment data (placeholder)."""
        # TODO: Implement attachment writing


class TMAManager:
    """High-level manager for TMA file operations."""

    @staticmethod
    def read_tma(filepath: str) -> TMAFile:
        """Read a TMA file and return a TMAFile object."""
        reader = TMAReader(filepath)
        return reader.read()

    @staticmethod
    def write_tma(filepath: str, tma_data: TMAFile):
        """Write a TMAFile object to a TMA file."""
        writer = TMAWriter(filepath)
        writer.write(tma_data)

    @staticmethod
    def create_from_blender_armature(armature_object: bpy.types.Object,
                                   output_path: str,
                                   frame_start: int | None = None,
                                   frame_end: int | None = None) -> TMAFile:
        """Create a TMAFile from a Blender armature."""
        if not armature_object or armature_object.type != "ARMATURE":
            raise ValueError("Selected object must be an armature")

        armature = armature_object.data
        bones = armature.bones
        pose = armature_object.pose

        # Get frame range
        if frame_start is None:
            frame_start = bpy.context.scene.frame_start
        if frame_end is None:
            frame_end = bpy.context.scene.frame_end

        frame_count = frame_end - frame_start + 1

        # Get FPS
        fps = bpy.context.scene.render.fps
        fps_base = bpy.context.scene.render.fps_base
        animation_duration = frame_count / (fps / fps_base)

        # Create header
        header = TMAHeader(magic=1095586882, version=12, dp=20548)

        # Create bones
        tma_bones = []
        for bone in bones:
            parent_index = -1
            if bone.parent:
                parent_index = list(bones).index(bone.parent)

            # Get matrices
            world_space = bone.matrix_local
            parent_space = world_space
            if bone.parent:
                parent_space = bone.parent.matrix_local.inverted() @ world_space
            inverse_bind = world_space.inverted()

            tma_bones.append(TMABone(
                name=bone.name,
                parent_index=parent_index,
                parent_space_matrix=parent_space,
                world_space_matrix=world_space,
                inverse_bind_matrix=inverse_bind
            ))

        # Create animation data
        animations = []
        depsgraph = bpy.context.evaluated_depsgraph_get()
        arm_obj_eval = armature_object.evaluated_get(depsgraph)

        for pose_bone in arm_obj_eval.pose.bones:
            translations = []
            rotations = []

            for frame in range(frame_start, frame_end + 1):
                bpy.context.scene.frame_set(frame)
                bpy.context.scene.frame_set(frame)  # Call twice for stability

                # Get translation
                trans = pose_bone.matrix_basis.to_translation()
                translations.append((trans.x, trans.y, trans.z))

                # Get rotation
                quat = pose_bone.matrix_basis.to_quaternion()
                rotations.append(quat)

            animations.append(TMAAnimationData(
                bone_name=pose_bone.name,
                position_mode=1,  # Normal
                rotation_mode=3,  # Normal
                translations=translations,
                rotations=rotations
            ))

        # Create TMAFile
        tma_file = TMAFile(
            header=header,
            active_bone_count=len(bones),
            frame_count=frame_count,
            animation_duration=animation_duration,
            root_position=bones[0].head,
            bones=tma_bones,
            animations=animations,
            attachments=[]
        )

        # Write to file
        TMAManager.write_tma(output_path, tma_file)

        return tma_file

    @staticmethod
    def import_to_blender(filepath: str,
                         collection_name: str = "imported",
                         create_new_armature: bool = True) -> bpy.types.Object:
        """Import a TMA file into Blender."""
        tma_data = TMAManager.read_tma(filepath)

        # Get or create collection
        try:
            collection = bpy.data.collections[collection_name]
        except KeyError:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)

        # Get or create armature
        armature_object = None
        if not create_new_armature:
            armature_object = bpy.context.active_object
            if armature_object and armature_object.type == "ARMATURE":
                armature = armature_object.data
            else:
                armature_object = None

        if armature_object is None:
            # Create new armature
            anim_name = os.path.splitext(os.path.basename(filepath))[0]
            armature_name = f"{anim_name}_armature"
            armature = bpy.data.armatures.new(armature_name)
            armature_object = bpy.data.objects.new(armature_name, armature)
            collection.objects.link(armature_object)

            # Set up coordinate system
            armature_object.rotation_euler = (-math.pi / 2, 0, 0)
            armature_object.scale = (1, -1, 1)

        # Set up animation
        anim_name = os.path.splitext(os.path.basename(filepath))[0]
        if anim_name in bpy.data.actions:
            action = bpy.data.actions[anim_name]
        else:
            action = bpy.data.actions.new(anim_name)

        armature_object.animation_data_create()
        armature_object.animation_data.action = action

        # Set frame range
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = tma_data.frame_count - 1
        bpy.context.scene.render.fps = tma_data.frame_count
        bpy.context.scene.render.fps_base = tma_data.animation_duration

        # Create bones
        TMAManager._create_blender_bones(armature_object, tma_data.bones)

        # Create keyframes
        TMAManager._create_blender_keyframes(armature_object, tma_data.animations)

        return armature_object

    @staticmethod
    def _create_blender_bones(armature_object: bpy.types.Object, bones: list[TMABone]):
        """Create Blender bones from TMA bone data."""
        armature = armature_object.data

        # Enter edit mode
        bpy.context.view_layer.objects.active = armature_object
        bpy.ops.object.mode_set(mode="EDIT")

        # Create bones
        for i, tma_bone in enumerate(bones):
            try:
                eb = armature.edit_bones[tma_bone.name]
                print(f"Bone {tma_bone.name} already exists, skipping")
            except KeyError:
                eb = armature.edit_bones.new(tma_bone.name)

                # Set parent
                if tma_bone.parent_index >= 0:
                    parent_name = bones[tma_bone.parent_index].name
                    try:
                        eb.parent = armature.edit_bones[parent_name]
                    except KeyError:
                        print(f"Warning: Parent bone {parent_name} not found")

                # Set matrix
                eb.matrix = tma_bone.world_space_matrix

                # Set default tail
                eb.tail = (0.0, 0.2, 0.0)

        # Exit edit mode
        bpy.ops.object.mode_set(mode="OBJECT")

    @staticmethod
    def _create_blender_keyframes(armature_object: bpy.types.Object,
                                 animations: list[TMAAnimationData]):
        """Create Blender keyframes from TMA animation data."""
        action = armature_object.animation_data.action

        for anim in animations:
            try:
                pose_bone = armature_object.pose.bones[anim.bone_name]
            except KeyError:
                print(f"Warning: Pose bone {anim.bone_name} not found")
                continue

            # Create location keyframes
            if anim.position_mode == 1:  # Normal mode
                fcurve_loc_x = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].location', index=0)
                fcurve_loc_y = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].location', index=1)
                fcurve_loc_z = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].location', index=2)

                for frame, (x, y, z) in enumerate(anim.translations):
                    fcurve_loc_x.keyframe_points.insert(frame, x)
                    fcurve_loc_y.keyframe_points.insert(frame, y)
                    fcurve_loc_z.keyframe_points.insert(frame, z)

            # Create rotation keyframes
            if anim.rotation_mode == 3:  # Normal mode
                fcurve_rot_w = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].rotation_quaternion', index=0)
                fcurve_rot_x = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].rotation_quaternion', index=1)
                fcurve_rot_y = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].rotation_quaternion', index=2)
                fcurve_rot_z = action.fcurves.new(data_path=f'pose.bones["{anim.bone_name}"].rotation_quaternion', index=3)

                for frame, quat in enumerate(anim.rotations):
                    fcurve_rot_w.keyframe_points.insert(frame, quat.w)
                    fcurve_rot_x.keyframe_points.insert(frame, quat.x)
                    fcurve_rot_y.keyframe_points.insert(frame, quat.y)
                    fcurve_rot_z.keyframe_points.insert(frame, quat.z)
