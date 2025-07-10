#!/usr/bin/env python3
"""
TMM (Mesh) File Manager

This module provides classes for managing Age of Mythology Retold TMM files.
TMM files contain mesh data, materials, and bone information.
"""

from collections import defaultdict
from dataclasses import dataclass
import os
import re
import struct

import bpy
from mathutils import Matrix, Vector
import numpy as np


@dataclass
class TMMHeader:
    """TMM file header information."""
    magic: int  # BTMM (1296913474)
    version: int  # Usually 35
    dp: int  # Usually 20548


@dataclass
class TMMBoundingBox:
    """Bounding box information."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float


@dataclass
class TMMBone:
    """Represents a bone in the TMM file."""
    name: str
    parent_id: int
    quaternion: tuple[float, float, float]  # Unknown purpose
    radius: float  # Collision radius
    parent_space_matrix: Matrix
    world_space_matrix: Matrix
    inverse_bind_matrix: Matrix


@dataclass
class TMMAttachment:
    """Represents an attachment point."""
    name: str
    parent_bone_id: int
    transform_matrix1: Matrix  # Parent space
    transform_matrix2: Matrix  # World space
    unknown_zero1: int
    unknown_zero2: int
    second_name: str
    unknown_ints: tuple[int, int, int, int]


@dataclass
class TMMMeshGroup:
    """Represents a mesh group (material group)."""
    verts_start: int
    tris_start: int
    num_verts: int
    num_tri_verts: int
    num_tris: int
    mat_index: int
    default_index: int


@dataclass
class TMMVertex:
    """Represents a vertex in the mesh."""
    position: Vector
    uv: tuple[float, float] | None
    normal: Vector
    tangent: Vector
    bitangent: Vector
    weights: list[tuple[int, int]]  # (bone_id, weight)


@dataclass
class TMMTriangle:
    """Represents a triangle in the mesh."""
    vertices: list[int]  # Vertex indices


@dataclass
class TMMFile:
    """Complete TMM file structure."""
    header: TMMHeader
    bounding_box: TMMBoundingBox
    bigger_bounding_box: TMMBoundingBox
    unknown_float: float
    mesh_groups: list[TMMMeshGroup]
    materials: list[str]
    defaults: list[str]  # Shader techniques
    bones: list[TMMBone]
    attachments: list[TMMAttachment]
    vertices: list[TMMVertex]
    triangles: list[TMMTriangle]
    main_matrix: Matrix


class TMMReader:
    """Reads TMM files and converts them to TMMFile objects."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> TMMFile:
        """Read and parse a TMM file."""
        with open(self.filepath, "rb") as f:
            return self._parse_file(f)

    def _parse_file(self, f) -> TMMFile:
        """Parse the TMM file content."""
        # Header
        header = self._read_header(f)

        # Import block
        self._skip_import_block(f)

        # Bounding boxes
        bounding_box = self._read_bounding_box(f)
        bigger_bounding_box = self._read_bounding_box(f)

        # Unknown float
        unknown_float = struct.unpack("<f", f.read(4))[0]

        # Counts
        num_mesh_groups = struct.unpack("<L", f.read(4))[0]
        num_materials = struct.unpack("<L", f.read(4))[0]
        num_defaults = struct.unpack("<L", f.read(4))[0]
        num_bones = struct.unpack("<L", f.read(4))[0]
        num_unknown2 = struct.unpack("<L", f.read(4))[0]
        num_attachments = struct.unpack("<L", f.read(4))[0]
        num_vertices = struct.unpack("<L", f.read(4))[0]
        num_triangle_verts = struct.unpack("<L", f.read(4))[0]

        # Block addresses and lengths
        block_info = self._read_block_info(f)

        # Unknown bools
        unknown_bools = struct.unpack("<BB", f.read(2))

        # Main matrix
        main_matrix = self._read_main_matrix(f)

        # Read data sections
        attachments = self._read_attachments(f, num_attachments)
        mesh_groups = self._read_mesh_groups(f, num_mesh_groups)
        materials = self._read_materials(f, num_materials)
        defaults = self._read_defaults(f, num_defaults)
        bones = self._read_bones(f, num_bones)

        # Read vertex and triangle data (placeholder)
        vertices = []
        triangles = []

        return TMMFile(
            header=header,
            bounding_box=bounding_box,
            bigger_bounding_box=bigger_bounding_box,
            unknown_float=unknown_float,
            mesh_groups=mesh_groups,
            materials=materials,
            defaults=defaults,
            bones=bones,
            attachments=attachments,
            vertices=vertices,
            triangles=triangles,
            main_matrix=main_matrix
        )

    def _read_header(self, f) -> TMMHeader:
        """Read the TMM file header."""
        magic = struct.unpack("<L", f.read(4))[0]
        assert magic == 1296913474, f"Invalid TMM magic: {magic}"

        version = struct.unpack("<L", f.read(4))[0]
        dp = struct.unpack("<H", f.read(2))[0]

        return TMMHeader(magic=magic, version=version, dp=dp)

    def _skip_import_block(self, f):
        """Skip the import block."""
        import_length = struct.unpack("<L", f.read(4))[0]
        num_imports = struct.unpack("<L", f.read(4))[0]
        for _ in range(num_imports):
            name_length = struct.unpack("<L", f.read(4))[0] * 2
            f.read(name_length)  # Skip name
            f.read(16)  # Skip unknown data

    def _read_bounding_box(self, f) -> TMMBoundingBox:
        """Read a bounding box."""
        coords = struct.unpack("<ffffff", f.read(24))
        return TMMBoundingBox(
            min_x=coords[0], min_y=coords[1], min_z=coords[2],
            max_x=coords[3], max_y=coords[4], max_z=coords[5]
        )

    def _read_block_info(self, f) -> dict[str, tuple[int, int]]:
        """Read block address and length information."""
        blocks = {}

        # Vertices block
        blocks["vertices"] = (
            struct.unpack("<L", f.read(4))[0],
            struct.unpack("<L", f.read(4))[0]
        )

        # Triangles block
        blocks["triangles"] = (
            struct.unpack("<L", f.read(4))[0],
            struct.unpack("<L", f.read(4))[0]
        )

        # Weights block
        blocks["weights"] = (
            struct.unpack("<L", f.read(4))[0],
            struct.unpack("<L", f.read(4))[0]
        )

        # Unknown blocks
        for i in range(1, 4):
            start = struct.unpack("<L", f.read(4))[0]
            length = struct.unpack("<L", f.read(4))[0]
            blocks[f"unknown{i}"] = (start, length)

        # Heights block
        blocks["heights"] = (
            struct.unpack("<L", f.read(4))[0],
            struct.unpack("<L", f.read(4))[0]
        )

        # Last unknown block
        start = struct.unpack("<L", f.read(4))[0]
        length = struct.unpack("<L", f.read(4))[0]
        blocks["unknown3"] = (start, length)

        return blocks

    def _read_main_matrix(self, f) -> Matrix:
        """Read the main transformation matrix."""
        matrix_data = struct.unpack("<ffffffffffff", f.read(48))  # 4x3 matrix
        matrix = Matrix(np.array(list(matrix_data) + [0, 0, 0, 1]).reshape(4, 4))
        return matrix

    def _read_attachments(self, f, num_attachments: int) -> list[TMMAttachment]:
        """Read attachment data."""
        attachments = []
        for _ in range(num_attachments):
            unknown_int = struct.unpack("<L", f.read(4))[0]
            parent_bone_id = struct.unpack("<l", f.read(4))[0]

            name_length = struct.unpack("<L", f.read(4))[0] * 2
            name = f.read(name_length).decode("UTF-16-LE")

            # Read matrices
            matrix1_data = struct.unpack("<ffffffffffff", f.read(48))
            matrix2_data = struct.unpack("<ffffffffffff", f.read(48))
            matrix1 = Matrix(np.array(list(matrix1_data) + [0, 0, 0, 1]).reshape(4, 4))
            matrix2 = Matrix(np.array(list(matrix2_data) + [0, 0, 0, 1]).reshape(4, 4))

            unknown_zero1 = struct.unpack("<L", f.read(4))[0]
            unknown_zero2 = struct.unpack("<L", f.read(4))[0]

            second_length = struct.unpack("<L", f.read(4))[0] * 2
            second_name = f.read(second_length).decode("UTF-16-LE")

            unknown_ints = struct.unpack("<llll", f.read(16))

            attachments.append(TMMAttachment(
                name=name,
                parent_bone_id=parent_bone_id,
                transform_matrix1=matrix1,
                transform_matrix2=matrix2,
                unknown_zero1=unknown_zero1,
                unknown_zero2=unknown_zero2,
                second_name=second_name,
                unknown_ints=unknown_ints
            ))

        return attachments

    def _read_mesh_groups(self, f, num_mesh_groups: int) -> list[TMMMeshGroup]:
        """Read mesh group information."""
        mesh_groups = []
        for _ in range(num_mesh_groups):
            verts_start = struct.unpack("<L", f.read(4))[0]
            tris_start = struct.unpack("<L", f.read(4))[0]
            num_verts = struct.unpack("<L", f.read(4))[0]
            num_tri_verts = struct.unpack("<L", f.read(4))[0]
            mat_index = struct.unpack("<L", f.read(4))[0]
            default_index = struct.unpack("<L", f.read(4))[0]

            mesh_groups.append(TMMMeshGroup(
                verts_start=verts_start,
                tris_start=tris_start,
                num_verts=num_verts,
                num_tri_verts=num_tri_verts,
                num_tris=num_tri_verts // 3,
                mat_index=mat_index,
                default_index=default_index
            ))

        return mesh_groups

    def _read_materials(self, f, num_materials: int) -> list[str]:
        """Read material names."""
        materials = []
        for _ in range(num_materials):
            name_length = struct.unpack("<L", f.read(4))[0] * 2
            name = f.read(name_length).decode("UTF-16-LE")
            materials.append(name)
        return materials

    def _read_defaults(self, f, num_defaults: int) -> list[str]:
        """Read default shader technique names."""
        defaults = []
        for _ in range(num_defaults):
            name_length = struct.unpack("<L", f.read(4))[0] * 2
            name = f.read(name_length).decode("UTF-16-LE")
            defaults.append(name)
        return defaults

    def _read_bones(self, f, num_bones: int) -> list[TMMBone]:
        """Read bone definitions."""
        bones = []
        for _ in range(num_bones):
            name_length = struct.unpack("<L", f.read(4))[0] * 2
            name = f.read(name_length).decode("UTF-16-LE")
            parent_id = struct.unpack("<l", f.read(4))[0]

            quaternion = struct.unpack("<fff", f.read(12))
            radius = struct.unpack("<f", f.read(4))[0]

            # Read matrices
            parent_space = self._read_matrix(f)
            world_space = self._read_matrix(f)
            inverse_bind = self._read_matrix(f)

            bones.append(TMMBone(
                name=name,
                parent_id=parent_id,
                quaternion=quaternion,
                radius=radius,
                parent_space_matrix=parent_space,
                world_space_matrix=world_space,
                inverse_bind_matrix=inverse_bind
            ))

        return bones

    def _read_matrix(self, f) -> Matrix:
        """Read a 4x4 matrix from the file."""
        matrix_data = struct.unpack("<ffffffffffffffff", f.read(64))
        matrix = Matrix(np.array(matrix_data).reshape(4, 4))
        return matrix


class TMMWriter:
    """Writes TMMFile objects to TMM files."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def write(self, tmm_data: TMMFile):
        """Write a TMMFile object to a TMM file."""
        with open(self.filepath, "wb") as f:
            self._write_file(f, tmm_data)

    def _write_file(self, f, tmm_data: TMMFile):
        """Write the TMM file content."""
        # Header
        self._write_header(f, tmm_data.header)

        # Import block
        self._write_import_block(f)

        # Bounding boxes
        self._write_bounding_box(f, tmm_data.bounding_box)
        self._write_bounding_box(f, tmm_data.bigger_bounding_box)

        # Unknown float
        f.write(struct.pack("<f", tmm_data.unknown_float))

        # Write counts
        f.write(struct.pack("<L", len(tmm_data.mesh_groups)))
        f.write(struct.pack("<L", len(tmm_data.materials)))
        f.write(struct.pack("<L", len(tmm_data.defaults)))
        f.write(struct.pack("<L", len(tmm_data.bones)))
        f.write(struct.pack("<L", 0))  # num_unknown2
        f.write(struct.pack("<L", len(tmm_data.attachments)))
        f.write(struct.pack("<L", len(tmm_data.vertices)))
        f.write(struct.pack("<L", len(tmm_data.triangles) * 3))

        # Write block info (placeholder)
        self._write_block_info(f)

        # Unknown bools
        f.write(struct.pack("<BB", 0, 1))

        # Main matrix
        self._write_main_matrix(f, tmm_data.main_matrix)

        # Write data sections
        self._write_attachments(f, tmm_data.attachments)
        self._write_mesh_groups(f, tmm_data.mesh_groups)
        self._write_materials(f, tmm_data.materials)
        self._write_defaults(f, tmm_data.defaults)
        self._write_bones(f, tmm_data.bones)

    def _write_header(self, f, header: TMMHeader):
        """Write the TMM file header."""
        f.write(struct.pack("<L", header.magic))
        f.write(struct.pack("<L", header.version))
        f.write(struct.pack("<H", header.dp))

    def _write_import_block(self, f):
        """Write the import block."""
        f.write(struct.pack("<L", 4))  # Length
        f.write(struct.pack("<L", 0))  # No imports

    def _write_bounding_box(self, f, bbox: TMMBoundingBox):
        """Write a bounding box."""
        f.write(struct.pack("<ffffff",
                           bbox.min_x, bbox.min_y, bbox.min_z,
                           bbox.max_x, bbox.max_y, bbox.max_z))

    def _write_block_info(self, f):
        """Write block address and length information (placeholder)."""
        # Write placeholder values for all blocks
        for _ in range(8):  # 8 blocks total
            f.write(struct.pack("<LL", 0, 0))  # start, length

    def _write_main_matrix(self, f, matrix: Matrix):
        """Write the main transformation matrix."""
        # Extract 4x3 part
        matrix_4x3 = [matrix[i][j] for i in range(4) for j in range(3)]
        f.write(struct.pack("<ffffffffffff", *matrix_4x3))

    def _write_attachments(self, f, attachments: list[TMMAttachment]):
        """Write attachment data."""
        for attachment in attachments:
            f.write(struct.pack("<L", 0))  # unknown_int
            f.write(struct.pack("<l", attachment.parent_bone_id))

            # Write name
            name_bytes = attachment.name.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(attachment.name)))
            f.write(name_bytes)

            # Write matrices
            self._write_matrix_4x3(f, attachment.transform_matrix1)
            self._write_matrix_4x3(f, attachment.transform_matrix2)

            f.write(struct.pack("<LL", attachment.unknown_zero1, attachment.unknown_zero2))

            # Write second name
            second_name_bytes = attachment.second_name.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(attachment.second_name)))
            f.write(second_name_bytes)

            f.write(struct.pack("<llll", *attachment.unknown_ints))

    def _write_matrix_4x3(self, f, matrix: Matrix):
        """Write a 4x3 matrix."""
        matrix_4x3 = [matrix[i][j] for i in range(4) for j in range(3)]
        f.write(struct.pack("<ffffffffffff", *matrix_4x3))

    def _write_mesh_groups(self, f, mesh_groups: list[TMMMeshGroup]):
        """Write mesh group information."""
        for group in mesh_groups:
            f.write(struct.pack("<LLLLLL",
                               group.verts_start, group.tris_start,
                               group.num_verts, group.num_tri_verts,
                               group.mat_index, group.default_index))

    def _write_materials(self, f, materials: list[str]):
        """Write material names."""
        for material in materials:
            name_bytes = material.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(material)))
            f.write(name_bytes)

    def _write_defaults(self, f, defaults: list[str]):
        """Write default shader technique names."""
        for default in defaults:
            name_bytes = default.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(default)))
            f.write(name_bytes)

    def _write_bones(self, f, bones: list[TMMBone]):
        """Write bone definitions."""
        for bone in bones:
            # Write name
            name_bytes = bone.name.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(bone.name)))
            f.write(name_bytes)

            f.write(struct.pack("<l", bone.parent_id))
            f.write(struct.pack("<fff", *bone.quaternion))
            f.write(struct.pack("<f", bone.radius))

            # Write matrices
            self._write_matrix(f, bone.parent_space_matrix)
            self._write_matrix(f, bone.world_space_matrix)
            self._write_matrix(f, bone.inverse_bind_matrix)

    def _write_matrix(self, f, matrix: Matrix):
        """Write a 4x4 matrix."""
        matrix_data = [f for row in matrix for f in row]
        f.write(struct.pack("<ffffffffffffffff", *matrix_data))


class TMMManager:
    """High-level manager for TMM file operations."""

    @staticmethod
    def read_tmm(filepath: str) -> TMMFile:
        """Read a TMM file and return a TMMFile object."""
        reader = TMMReader(filepath)
        return reader.read()

    @staticmethod
    def write_tmm(filepath: str, tmm_data: TMMFile):
        """Write a TMMFile object to a TMM file."""
        writer = TMMWriter(filepath)
        writer.write(tmm_data)

    @staticmethod
    def create_from_blender_mesh(mesh_object: bpy.types.Object,
                               output_path: str,
                               armature_object: bpy.types.Object | None = None) -> TMMFile:
        """Create a TMMFile from a Blender mesh."""
        if not mesh_object or mesh_object.type != "MESH":
            raise ValueError("Selected object must be a mesh")

        mesh = mesh_object.data
        mesh.calc_loop_triangles()
        mesh.calc_tangents()

        # Find armature if not provided
        if armature_object is None:
            arm_mod = next((m for m in mesh_object.modifiers if m.type == "ARMATURE" and m.object), None)
            if arm_mod:
                armature_object = arm_mod.object

        # Create header
        header = TMMHeader(magic=1296913474, version=35, dp=20548)

        # Calculate bounding boxes
        bbox = TMMManager._calculate_bounding_box(mesh_object)
        bigger_bbox = TMMManager._calculate_bigger_bounding_box(mesh_object, armature_object)

        # Get attachments
        attachments = TMMManager._get_attachments(armature_object) if armature_object else []

        # Process mesh data
        mesh_groups, materials, vertices, triangles = TMMManager._process_mesh_data(
            mesh_object, armature_object
        )

        # Get bones
        bones = TMMManager._get_bones(armature_object) if armature_object else []

        # Create main matrix
        main_matrix = Matrix.Identity(4)

        # Create TMMFile
        tmm_file = TMMFile(
            header=header,
            bounding_box=bbox,
            bigger_bounding_box=bigger_bbox,
            unknown_float=bbox.max_z,  # Usually height
            mesh_groups=mesh_groups,
            materials=materials,
            defaults=["default"],  # Usually just "default"
            bones=bones,
            attachments=attachments,
            vertices=vertices,
            triangles=triangles,
            main_matrix=main_matrix
        )

        # Write to file
        TMMManager.write_tmm(output_path, tmm_file)

        return tmm_file

    @staticmethod
    def import_to_blender(filepath: str,
                         collection_name: str = "imported",
                         create_new_mesh: bool = True) -> bpy.types.Object:
        """Import a TMM file into Blender."""
        tmm_data = TMMManager.read_tmm(filepath)

        # Get or create collection
        try:
            collection = bpy.data.collections[collection_name]
        except KeyError:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)

        # Get or create mesh object
        mesh_object = None
        if not create_new_mesh:
            mesh_object = bpy.context.active_object
            if mesh_object and mesh_object.type == "MESH":
                mesh = mesh_object.data
            else:
                mesh_object = None

        if mesh_object is None:
            # Create new mesh
            mesh_name = os.path.splitext(os.path.basename(filepath))[0]
            mesh = bpy.data.meshes.new(mesh_name)
            mesh_object = bpy.data.objects.new(mesh_name, mesh)
            collection.objects.link(mesh_object)

        # Create mesh data
        TMMManager._create_blender_mesh(mesh_object, tmm_data)

        # Create materials
        TMMManager._create_blender_materials(mesh_object, tmm_data.materials)

        # Create armature if bones exist
        if tmm_data.bones:
            armature_object = TMMManager._create_blender_armature(tmm_data.bones, collection)
            TMMManager._create_blender_armature_modifier(mesh_object, armature_object)

        return mesh_object

    @staticmethod
    def _calculate_bounding_box(mesh_object: bpy.types.Object) -> TMMBoundingBox:
        """Calculate the bounding box of a mesh object."""
        bbox = mesh_object.bound_box
        return TMMBoundingBox(
            min_x=bbox[0][0], min_y=bbox[0][2], min_z=bbox[0][1],
            max_x=bbox[-2][0], max_y=bbox[-2][2], max_z=bbox[-2][1]
        )

    @staticmethod
    def _calculate_bigger_bounding_box(mesh_object: bpy.types.Object,
                                     armature_object: bpy.types.Object | None) -> TMMBoundingBox:
        """Calculate the bigger bounding box for animated meshes."""
        bbox = TMMManager._calculate_bounding_box(mesh_object)

        if armature_object is None:
            return bbox
        # For animated meshes, use a larger bounding box
        big_size = 3 * bbox.max_z
        return TMMBoundingBox(
            min_x=-big_size, min_y=-big_size, min_z=-big_size,
            max_x=big_size, max_y=big_size, max_z=big_size
        )

    @staticmethod
    def _get_attachments(armature_object: bpy.types.Object) -> list[TMMAttachment]:
        """Get attachment points from armature children."""
        attachments = []

        for empty in armature_object.children:
            if empty.data is None and empty.parent_type == "BONE":
                parent_bone_id = -1
                if empty.parent_bone:
                    try:
                        parent_bone_id = list(armature_object.data.bones).index(
                            armature_object.data.bones[empty.parent_bone]
                        )
                    except (ValueError, KeyError):
                        pass

                # Clean attachment name
                clean_name = re.sub(r"\.\d{3}$", "", empty.name)

                attachments.append(TMMAttachment(
                    name=clean_name,
                    parent_bone_id=parent_bone_id,
                    transform_matrix1=empty.matrix_local,
                    transform_matrix2=empty.matrix_world,
                    unknown_zero1=0,
                    unknown_zero2=0,
                    second_name="",
                    unknown_ints=(-1, 0, 0, 0)
                ))

        return attachments

    @staticmethod
    def _process_mesh_data(mesh_object: bpy.types.Object,
                          armature_object: bpy.types.Object | None) -> tuple[list[TMMMeshGroup], list[str], list[TMMVertex], list[TMMTriangle]]:
        """Process mesh data into TMM format."""
        mesh = mesh_object.data

        # Build material groups
        material_groups = defaultdict(list)
        for tri in mesh.polygons:
            material_groups[tri.material_index].append(tri.index)

        mesh_groups = []
        all_vertices = []
        all_triangles = []
        vertex_offset = 0

        for mat_index, tri_indices in material_groups.items():
            # Process this material group
            vertices, triangles = TMMManager._process_material_group(
                mesh_object, tri_indices, armature_object
            )

            mesh_groups.append(TMMMeshGroup(
                verts_start=vertex_offset,
                tris_start=len(all_triangles) * 3,
                num_verts=len(vertices),
                num_tri_verts=len(triangles) * 3,
                num_tris=len(triangles),
                mat_index=mat_index,
                default_index=0
            ))

            all_vertices.extend(vertices)
            all_triangles.extend(triangles)
            vertex_offset += len(vertices)

        # Get material names
        materials = []
        for mat in mesh_object.material_slots:
            if mat.material:
                materials.append(mat.material.name)
            else:
                materials.append("")

        return mesh_groups, materials, all_vertices, all_triangles

    @staticmethod
    def _process_material_group(mesh_object: bpy.types.Object,
                              tri_indices: list[int],
                              armature_object: bpy.types.Object | None) -> tuple[list[TMMVertex], list[TMMTriangle]]:
        """Process a material group into vertices and triangles."""
        mesh = mesh_object.data
        vertices = []
        triangles = []

        # Create vertex lookup
        vertex_lookup = {}

        for tri_index in tri_indices:
            tri = mesh.polygons[tri_index]
            triangle_vertices = []

            for i, loop_index in enumerate(tri.loop_indices):
                loop = mesh.loops[loop_index]
                vert_index = loop.vertex_index
                vert = mesh.vertices[vert_index]

                # Get UV coordinates
                uv = None
                if mesh.uv_layers.active:
                    uv = mesh.uv_layers.active.data[loop_index].uv

                # Get normal, tangent, bitangent
                normal = loop.normal
                tangent = loop.tangent
                bitangent = loop.bitangent

                # Get weights
                weights = []
                if armature_object:
                    bone_name_to_id = {b.name: i for i, b in enumerate(armature_object.data.bones)}
                    for group in vert.groups:
                        vg = mesh_object.vertex_groups[group.group]
                        bone_id = bone_name_to_id.get(vg.name)
                        if bone_id is not None:
                            weights.append((bone_id, int(round(group.weight * 255))))
                    weights.sort(key=lambda x: x[1], reverse=True)
                    weights = weights[:4]  # Max 4 weights

                # Create vertex
                vertex = TMMVertex(
                    position=vert.co,
                    uv=uv,
                    normal=normal,
                    tangent=tangent,
                    bitangent=bitangent,
                    weights=weights
                )

                # Check if vertex already exists
                vertex_key = (vert.co, uv, normal, tangent, bitangent, tuple(weights))
                if vertex_key in vertex_lookup:
                    triangle_vertices.append(vertex_lookup[vertex_key])
                else:
                    vertex_lookup[vertex_key] = len(vertices)
                    vertices.append(vertex)
                    triangle_vertices.append(len(vertices) - 1)

            triangles.append(TMMTriangle(vertices=triangle_vertices))

        return vertices, triangles

    @staticmethod
    def _get_bones(armature_object: bpy.types.Object) -> list[TMMBone]:
        """Get bone data from armature."""
        bones = []
        armature = armature_object.data

        for bone in armature.bones:
            parent_id = -1
            if bone.parent:
                parent_id = list(armature.bones).index(bone.parent)

            bones.append(TMMBone(
                name=bone.name,
                parent_id=parent_id,
                quaternion=(0.0, 0.0, 0.0),  # Unknown purpose
                radius=bone.head_radius if hasattr(bone, "head_radius") else 0.1,
                parent_space_matrix=bone.matrix_local,
                world_space_matrix=bone.matrix_local,
                inverse_bind_matrix=bone.matrix_local.inverted()
            ))

        return bones

    @staticmethod
    def _create_blender_mesh(mesh_object: bpy.types.Object, tmm_data: TMMFile):
        """Create Blender mesh data from TMM data."""
        mesh = mesh_object.data

        # Clear existing data
        mesh.clear_geometry()

        # Create vertices
        for tmm_vertex in tmm_data.vertices:
            mesh.vertices.new(tmm_vertex.position)

        # Create faces
        for tmm_triangle in tmm_data.triangles:
            mesh.faces.new([mesh.vertices[i] for i in tmm_triangle.vertices])

        # Update mesh
        mesh.update()

    @staticmethod
    def _create_blender_materials(mesh_object: bpy.types.Object, material_names: list[str]):
        """Create Blender materials from TMM material names."""
        for material_name in material_names:
            if material_name and material_name not in bpy.data.materials:
                material = bpy.data.materials.new(material_name)
            elif material_name:
                material = bpy.data.materials[material_name]
            else:
                material = bpy.data.materials.new("Material")

            mesh_object.data.materials.append(material)

    @staticmethod
    def _create_blender_armature(bones: list[TMMBone], collection: bpy.types.Collection) -> bpy.types.Object:
        """Create Blender armature from TMM bone data."""
        armature = bpy.data.armatures.new("Armature")
        armature_object = bpy.data.objects.new("Armature", armature)
        collection.objects.link(armature_object)

        # Enter edit mode
        bpy.context.view_layer.objects.active = armature_object
        bpy.ops.object.mode_set(mode="EDIT")

        # Create bones
        for tmm_bone in bones:
            eb = armature.edit_bones.new(tmm_bone.name)
            eb.matrix = tmm_bone.world_space_matrix

            if tmm_bone.parent_id >= 0:
                parent_name = bones[tmm_bone.parent_id].name
                try:
                    eb.parent = armature.edit_bones[parent_name]
                except KeyError:
                    pass

        # Exit edit mode
        bpy.ops.object.mode_set(mode="OBJECT")

        return armature_object

    @staticmethod
    def _create_blender_armature_modifier(mesh_object: bpy.types.Object, armature_object: bpy.types.Object):
        """Create armature modifier on mesh object."""
        modifier = mesh_object.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = armature_object
