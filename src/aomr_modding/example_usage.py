"""
Example usage of Age of Mythology Retold Modding Tools.

This script demonstrates how to use the TMA and TMM managers for various tasks.
"""

import os

import bpy

from .config import AOMRConfig
from .tma_manager import TMAManager
from .tmm_manager import TMMManager
from .utils import PerformanceMonitor


def example_import_animation():
    """Example: Import a TMA animation file."""
    print("=== Importing TMA Animation ===")

    # Example file path (replace with actual path)
    tma_file = "path/to/your/animation.tma"

    if not os.path.exists(tma_file):
        print(f"File not found: {tma_file}")
        return

    with PerformanceMonitor("TMA Import"):
        try:
            # Import the animation
            armature_object = TMAManager.import_to_blender(
                filepath=tma_file,
                collection_name="imported_animations",
                create_new_armature=True
            )

            print(f"Successfully imported animation: {armature_object.name}")
            print(f"Armature has {len(armature_object.data.bones)} bones")

            # Set as active object
            bpy.context.view_layer.objects.active = armature_object

        except Exception as e:
            print(f"Import failed: {e}")


def example_export_animation():
    """Example: Export an armature to TMA file."""
    print("=== Exporting TMA Animation ===")

    # Get the active object
    armature_object = bpy.context.active_object

    if not armature_object or armature_object.type != "ARMATURE":
        print("Please select an armature object")
        return

    # Create output path
    output_path = AOMRConfig.ensure_export_path()
    output_file = os.path.join(output_path, f"{armature_object.name}.tma")

    with PerformanceMonitor("TMA Export"):
        try:
            # Export the animation
            tma_data = TMAManager.create_from_blender_armature(
                armature_object=armature_object,
                output_path=output_file,
                frame_start=1,
                frame_end=60,
                optimize_static=True
            )

            print(f"Successfully exported animation to: {output_file}")
            print(f"Animation has {tma_data.frame_count} frames")
            print(f"Duration: {tma_data.animation_duration} seconds")

        except Exception as e:
            print(f"Export failed: {e}")


def example_import_mesh():
    """Example: Import a TMM mesh file."""
    print("=== Importing TMM Mesh ===")

    # Example file path (replace with actual path)
    tmm_file = "path/to/your/mesh.tmm"

    if not os.path.exists(tmm_file):
        print(f"File not found: {tmm_file}")
        return

    with PerformanceMonitor("TMM Import"):
        try:
            # Import the mesh
            mesh_object = TMMManager.import_to_blender(
                filepath=tmm_file,
                collection_name="imported_meshes",
                create_new_mesh=True,
                create_materials=True
            )

            print(f"Successfully imported mesh: {mesh_object.name}")
            print(f"Mesh has {len(mesh_object.data.vertices)} vertices")
            print(f"Mesh has {len(mesh_object.data.polygons)} faces")

            # Set as active object
            bpy.context.view_layer.objects.active = mesh_object

        except Exception as e:
            print(f"Import failed: {e}")


def example_export_mesh():
    """Example: Export a mesh to TMM file."""
    print("=== Exporting TMM Mesh ===")

    # Get the active object
    mesh_object = bpy.context.active_object

    if not mesh_object or mesh_object.type != "MESH":
        print("Please select a mesh object")
        return

    # Find associated armature
    armature_object = None
    for modifier in mesh_object.modifiers:
        if modifier.type == "ARMATURE" and modifier.object:
            armature_object = modifier.object
            break

    # Create output path
    output_path = AOMRConfig.ensure_export_path()
    output_file = os.path.join(output_path, f"{mesh_object.name}.tmm")

    with PerformanceMonitor("TMM Export"):
        try:
            # Export the mesh
            tmm_data = TMMManager.create_from_blender_mesh(
                mesh_object=mesh_object,
                output_path=output_file,
                armature_object=armature_object
            )

            print(f"Successfully exported mesh to: {output_file}")
            print(f"Mesh has {len(tmm_data.vertices)} vertices")
            print(f"Mesh has {len(tmm_data.triangles)} triangles")
            print(f"Materials: {tmm_data.materials}")

        except Exception as e:
            print(f"Export failed: {e}")


def example_batch_export():
    """Example: Batch export multiple objects."""
    print("=== Batch Export ===")

    # Get selected objects
    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("Please select objects to export")
        return

    # Create output path
    output_path = AOMRConfig.ensure_export_path()

    exported_count = 0
    errors = []

    with PerformanceMonitor("Batch Export"):
        for obj in selected_objects:
            try:
                if obj.type == "ARMATURE":
                    # Export TMA
                    output_file = os.path.join(output_path, f"{obj.name}.tma")
                    TMAManager.create_from_blender_armature(
                        armature_object=obj,
                        output_path=output_file
                    )
                    exported_count += 1
                    print(f"Exported armature: {obj.name}")

                elif obj.type == "MESH":
                    # Export TMM
                    output_file = os.path.join(output_path, f"{obj.name}.tmm")
                    TMMManager.create_from_blender_mesh(
                        mesh_object=obj,
                        output_path=output_file
                    )
                    exported_count += 1
                    print(f"Exported mesh: {obj.name}")

            except Exception as e:
                errors.append(f"{obj.name}: {e}")
                print(f"Failed to export {obj.name}: {e}")

    print(f"Batch export completed: {exported_count} objects exported")
    if errors:
        print(f"Errors: {len(errors)} objects failed")


def example_file_analysis():
    """Example: Analyze TMA and TMM files without importing."""
    print("=== File Analysis ===")

    # Example file paths (replace with actual paths)
    tma_file = "path/to/your/animation.tma"
    tmm_file = "path/to/your/mesh.tmm"

    # Analyze TMA file
    if os.path.exists(tma_file):
        try:
            tma_data = TMAManager.read_tma(tma_file)
            print(f"TMA Analysis for {tma_file}:")
            print(f"  Frame count: {tma_data.frame_count}")
            print(f"  Duration: {tma_data.animation_duration} seconds")
            print(f"  Bones: {len(tma_data.bones)}")
            print(f"  Animations: {len(tma_data.animations)}")
            print(f"  Attachments: {len(tma_data.attachments)}")

            # Show bone names
            print("  Bone names:")
            for bone in tma_data.bones:
                print(f"    - {bone.name}")

        except Exception as e:
            print(f"TMA analysis failed: {e}")

    # Analyze TMM file
    if os.path.exists(tmm_file):
        try:
            tmm_data = TMMManager.read_tmm(tmm_file)
            print(f"TMM Analysis for {tmm_file}:")
            print(f"  Vertices: {len(tmm_data.vertices)}")
            print(f"  Triangles: {len(tmm_data.triangles)}")
            print(f"  Materials: {tmm_data.materials}")
            print(f"  Bones: {len(tmm_data.bones)}")
            print(f"  Attachments: {len(tmm_data.attachments)}")

        except Exception as e:
            print(f"TMM analysis failed: {e}")


def example_create_test_data():
    """Example: Create test data for development."""
    print("=== Creating Test Data ===")

    # Create a simple armature
    bpy.ops.object.armature_add(location=(0, 0, 0))
    armature = bpy.context.active_object
    armature.name = "TestArmature"

    # Enter edit mode to add bones
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature.data.edit_bones

    # Add some bones
    bone1 = edit_bones.new("Bone1")
    bone1.head = (0, 0, 0)
    bone1.tail = (0, 0, 1)

    bone2 = edit_bones.new("Bone2")
    bone2.head = (0, 0, 1)
    bone2.tail = (0, 0, 2)
    bone2.parent = bone1

    # Return to object mode
    bpy.ops.object.mode_set(mode="OBJECT")

    # Create a simple mesh
    bpy.ops.mesh.primitive_cube_add(location=(2, 0, 0))
    mesh = bpy.context.active_object
    mesh.name = "TestMesh"

    # Add armature modifier to mesh
    modifier = mesh.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = armature

    print("Created test data:")
    print(f"  Armature: {armature.name}")
    print(f"  Mesh: {mesh.name}")
    print("You can now test export functionality")


def example_cleanup_imports():
    """Example: Clean up imported objects."""
    print("=== Cleaning Up Imports ===")

    # Remove objects with specific prefixes
    prefixes_to_remove = ["AOMR_", "imported_"]

    removed_count = 0
    for obj in bpy.data.objects:
        if any(obj.name.startswith(prefix) for prefix in prefixes_to_remove):
            bpy.data.objects.remove(obj, do_unlink=True)
            removed_count += 1

    # Remove orphaned data
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    for armature in bpy.data.armatures:
        if armature.users == 0:
            bpy.data.armatures.remove(armature)

    for material in bpy.data.materials:
        if material.users == 0:
            bpy.data.materials.remove(material)

    print(f"Cleaned up {removed_count} objects")


def main():
    """Main function to run examples."""
    print("Age of Mythology Retold Modding Tools - Examples")
    print("=" * 50)

    # Uncomment the examples you want to run

    # example_create_test_data()
    # example_export_animation()
    # example_export_mesh()
    # example_batch_export()
    # example_file_analysis()
    # example_cleanup_imports()

    print("\nTo run examples, uncomment them in the main() function")
    print("Make sure you have the appropriate files or test data ready")


if __name__ == "__main__":
    main()
