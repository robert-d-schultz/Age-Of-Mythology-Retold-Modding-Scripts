"""
Age of Mythology Retold Modding Tools

A Blender addon for importing and exporting TMA (animation) and TMM (mesh) files
used in Age of Mythology Retold modding.
"""

import logging
import struct

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

try:
    from .config import AOMRConfig
    from .tma_manager import TMAManager
    from .tmm_manager import TMMManager
    from .utils import AOMRError, handle_errors, setup_logging
except ImportError:
    # Fallback for when running as standalone script
    from config import AOMRConfig
    from tma_manager import TMAManager
    from tmm_manager import TMMManager
    from utils import AOMRError, handle_errors, setup_logging

# Set up logging
logger = setup_logging(__name__)

bl_info = {
    "name": "Age of Mythology Retold Modding Tools",
    "author": "Robert Shultz",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "File > Import/Export",
    "description": "Import and export TMA/TMM files for Age of Mythology Retold modding",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}


class AOMRAddonPreferences(bpy.types.AddonPreferences):
    """Addon preferences panel."""
    bl_idname = __name__

    # Default paths
    default_export_path: StringProperty(
        name="Default Export Path",
        description="Default directory for exported files",
        default="",
        subtype="DIR_PATH"
    )

    # Export options
    auto_create_collections: BoolProperty(
        name="Auto-create Collections",
        description="Automatically create collections for imported objects",
        default=True
    )

    preserve_original_names: BoolProperty(
        name="Preserve Original Names",
        description="Keep original file names when importing",
        default=True
    )

    compression_enabled: BoolProperty(
        name="Enable Compression",
        description="Enable compression for exported files",
        default=True
    )

    optimize_static_bones: BoolProperty(
        name="Optimize Static Bones",
        description="Use static mode for bones that don't move",
        default=True
    )

    # Import options
    create_materials: BoolProperty(
        name="Create Materials",
        description="Automatically create materials for imported meshes",
        default=True
    )

    # Logging
    enable_debug_logging: BoolProperty(
        name="Enable Debug Logging",
        description="Enable detailed logging for debugging",
        default=False
    )

    def draw(self, context):
        layout = self.layout

        # Export settings
        box = layout.box()
        box.label(text="Export Settings")
        box.prop(self, "default_export_path")
        box.prop(self, "auto_create_collections")
        box.prop(self, "preserve_original_names")
        box.prop(self, "compression_enabled")
        box.prop(self, "optimize_static_bones")

        # Import settings
        box = layout.box()
        box.label(text="Import Settings")
        box.prop(self, "create_materials")

        # Debug settings
        box = layout.box()
        box.label(text="Debug Settings")
        box.prop(self, "enable_debug_logging")


class ImportTMAOperator(bpy.types.Operator, ImportHelper):
    """Import TMA animation file"""
    bl_idname = "import_animation.tma"
    bl_label = "Import TMA Animation"
    bl_description = "Import animation data from TMA file"

    filename_ext = ".tma"
    filter_glob: StringProperty(
        default="*.tma",
        options={"HIDDEN"},
    )

    create_new_armature: BoolProperty(
        name="Create New Armature",
        description="Create a new armature object instead of using active object",
        default=True,
    )

    collection_name: StringProperty(
        name="Collection Name",
        description="Name of collection to import into",
        default="imported_animations",
    )

    @handle_errors
    def execute(self, context):
        logger.info(f"Starting TMA import from {self.filepath}")

        # Validate file
        is_valid, message = self.validate_tma_file(self.filepath)
        if not is_valid:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}

        # Import with progress
        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            armature_object = TMAManager.import_to_blender(
                filepath=self.filepath,
                collection_name=self.collection_name,
                create_new_armature=self.create_new_armature
            )

            # Set as active object
            bpy.context.view_layer.objects.active = armature_object

            wm.progress_end()
            self.report({"INFO"}, f"Successfully imported animation from {self.filepath}")
            logger.info("TMA import completed successfully")
            return {"FINISHED"}

        except Exception as e:
            wm.progress_end()
            logger.error(f"TMA import failed: {e}")
            self.report({"ERROR"}, f"Import failed: {e!s}")
            return {"CANCELLED"}

    def validate_tma_file(self, filepath):
        """Validate TMA file before import."""
        try:
            with open(filepath, "rb") as f:
                magic = struct.unpack("<L", f.read(4))[0]
                if magic != AOMRConfig.TMA_MAGIC:
                    return False, "Invalid TMA file format"

                version = struct.unpack("<L", f.read(4))[0]
                if version != AOMRConfig.TMA_VERSION:
                    return False, f"Unsupported TMA version: {version}"

            return True, "File is valid"
        except Exception as e:
            return False, f"File validation failed: {e}"


class ExportTMAOperator(bpy.types.Operator, ExportHelper):
    """Export TMA animation file"""
    bl_idname = "export_animation.tma"
    bl_label = "Export TMA Animation"
    bl_description = "Export animation data to TMA file"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".tma"
    filter_glob: StringProperty(
        default="*.tma",
        options={"HIDDEN"},
    )

    frame_start: IntProperty(
        name="Frame Start",
        description="First frame to export",
        default=1,
        min=1,
    )

    frame_end: IntProperty(
        name="Frame End",
        description="Last frame to export",
        default=60,
        min=1,
    )

    optimize_static_bones: BoolProperty(
        name="Optimize Static Bones",
        description="Use static mode for bones that don't move",
        default=True,
    )

    @handle_errors
    def execute(self, context):
        armature_object = context.active_object

        if not armature_object or armature_object.type != "ARMATURE":
            self.report({"ERROR"}, "Please select an armature object")
            return {"CANCELLED"}

        logger.info(f"Starting TMA export to {self.filepath}")

        # Save state for undo
        old_frame_start = context.scene.frame_start
        old_frame_end = context.scene.frame_end

        # Progress reporting
        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            tma_data = TMAManager.create_from_blender_armature(
                armature_object=armature_object,
                output_path=self.filepath,
                frame_start=self.frame_start,
                frame_end=self.frame_end,
                optimize_static=self.optimize_static_bones
            )

            wm.progress_end()
            self.report({"INFO"},
                       f"Successfully exported animation with {tma_data.frame_count} frames")
            logger.info("TMA export completed successfully")
            return {"FINISHED"}

        except Exception as e:
            wm.progress_end()
            # Restore state on error
            context.scene.frame_start = old_frame_start
            context.scene.frame_end = old_frame_end
            logger.error(f"TMA export failed: {e}")
            self.report({"ERROR"}, f"Export failed: {e!s}")
            return {"CANCELLED"}


class ImportTMMOperator(bpy.types.Operator, ImportHelper):
    """Import TMM mesh file"""
    bl_idname = "import_mesh.tmm"
    bl_label = "Import TMM Mesh"
    bl_description = "Import mesh data from TMM file"

    filename_ext = ".tmm"
    filter_glob: StringProperty(
        default="*.tmm",
        options={"HIDDEN"},
    )

    create_new_mesh: BoolProperty(
        name="Create New Mesh",
        description="Create a new mesh object instead of using active object",
        default=True,
    )

    collection_name: StringProperty(
        name="Collection Name",
        description="Name of collection to import into",
        default="imported_meshes",
    )

    create_materials: BoolProperty(
        name="Create Materials",
        description="Automatically create materials for imported meshes",
        default=True,
    )

    @handle_errors
    def execute(self, context):
        logger.info(f"Starting TMM import from {self.filepath}")

        # Validate file
        is_valid, message = self.validate_tmm_file(self.filepath)
        if not is_valid:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}

        # Import with progress
        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            mesh_object = TMMManager.import_to_blender(
                filepath=self.filepath,
                collection_name=self.collection_name,
                create_new_mesh=self.create_new_mesh,
                create_materials=self.create_materials
            )

            # Set as active object
            bpy.context.view_layer.objects.active = mesh_object

            wm.progress_end()
            self.report({"INFO"}, f"Successfully imported mesh from {self.filepath}")
            logger.info("TMM import completed successfully")
            return {"FINISHED"}

        except Exception as e:
            wm.progress_end()
            logger.error(f"TMM import failed: {e}")
            self.report({"ERROR"}, f"Import failed: {e!s}")
            return {"CANCELLED"}

    def validate_tmm_file(self, filepath):
        """Validate TMM file before import."""
        try:
            with open(filepath, "rb") as f:
                magic = struct.unpack("<L", f.read(4))[0]
                if magic != AOMRConfig.TMM_MAGIC:
                    return False, "Invalid TMM file format"

                version = struct.unpack("<L", f.read(4))[0]
                if version != AOMRConfig.TMM_VERSION:
                    return False, f"Unsupported TMM version: {version}"

            return True, "File is valid"
        except Exception as e:
            return False, f"File validation failed: {e}"


class ExportTMMOperator(bpy.types.Operator, ExportHelper):
    """Export TMM mesh file"""
    bl_idname = "export_mesh.tmm"
    bl_label = "Export TMM Mesh"
    bl_description = "Export mesh data to TMM file"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".tmm"
    filter_glob: StringProperty(
        default="*.tmm",
        options={"HIDDEN"},
    )

    include_armature: BoolProperty(
        name="Include Armature",
        description="Include armature data if present",
        default=True,
    )

    @handle_errors
    def execute(self, context):
        mesh_object = context.active_object

        if not mesh_object or mesh_object.type != "MESH":
            self.report({"ERROR"}, "Please select a mesh object")
            return {"CANCELLED"}

        logger.info(f"Starting TMM export to {self.filepath}")

        # Progress reporting
        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            # Find associated armature
            armature_object = None
            if self.include_armature:
                for modifier in mesh_object.modifiers:
                    if modifier.type == "ARMATURE" and modifier.object:
                        armature_object = modifier.object
                        break

            tmm_data = TMMManager.create_from_blender_mesh(
                mesh_object=mesh_object,
                output_path=self.filepath,
                armature_object=armature_object
            )

            wm.progress_end()
            self.report({"INFO"},
                       f"Successfully exported mesh with {len(tmm_data.vertices)} vertices")
            logger.info("TMM export completed successfully")
            return {"FINISHED"}

        except Exception as e:
            wm.progress_end()
            logger.error(f"TMM export failed: {e}")
            self.report({"ERROR"}, f"Export failed: {e!s}")
            return {"CANCELLED"}


class BatchExportOperator(bpy.types.Operator):
    """Export multiple objects at once"""
    bl_idname = "aomr.batch_export"
    bl_label = "Batch Export"
    bl_description = "Export multiple selected objects"

    @handle_errors
    def execute(self, context):
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({"ERROR"}, "Please select objects to export")
            return {"CANCELLED"}

        exported_count = 0
        errors = []

        # Progress reporting
        wm = context.window_manager
        wm.progress_begin(0, len(selected_objects))

        try:
            for i, obj in enumerate(selected_objects):
                wm.progress_update(i)

                try:
                    if obj.type == "ARMATURE":
                        # Export TMA
                        output_path = f"{obj.name}.tma"
                        TMAManager.create_from_blender_armature(
                            armature_object=obj,
                            output_path=output_path
                        )
                        exported_count += 1
                        logger.info(f"Exported armature: {obj.name}")

                    elif obj.type == "MESH":
                        # Export TMM
                        output_path = f"{obj.name}.tmm"
                        TMMManager.create_from_blender_mesh(
                            mesh_object=obj,
                            output_path=output_path
                        )
                        exported_count += 1
                        logger.info(f"Exported mesh: {obj.name}")

                except Exception as e:
                    errors.append(f"{obj.name}: {e}")
                    logger.error(f"Failed to export {obj.name}: {e}")

            wm.progress_end()

            if errors:
                error_msg = "\n".join(errors[:3])  # Show first 3 errors
                if len(errors) > 3:
                    error_msg += f"\n... and {len(errors) - 3} more errors"
                self.report({"WARNING"}, f"Exported {exported_count} objects. Errors:\n{error_msg}")
            else:
                self.report({"INFO"}, f"Successfully exported {exported_count} objects")

            return {"FINISHED"}

        except Exception as e:
            wm.progress_end()
            logger.error(f"Batch export failed: {e}")
            self.report({"ERROR"}, f"Batch export failed: {e}")
            return {"CANCELLED"}


# Menu classes
class AOMR_MT_import(bpy.types.Menu):
    bl_idname = "AOMR_MT_import"
    bl_label = "Age of Mythology Retold"

    def draw(self, context):
        layout = self.layout
        layout.operator(ImportTMAOperator.bl_idname, text="TMA Animation (.tma)")
        layout.operator(ImportTMMOperator.bl_idname, text="TMM Mesh (.tmm)")


class AOMR_MT_export(bpy.types.Menu):
    bl_idname = "AOMR_MT_export"
    bl_label = "Age of Mythology Retold"

    def draw(self, context):
        layout = self.layout
        layout.operator(ExportTMAOperator.bl_idname, text="TMA Animation (.tma)")
        layout.operator(ExportTMMOperator.bl_idname, text="TMM Mesh (.tmm)")
        layout.separator()
        layout.operator(BatchExportOperator.bl_idname, text="Batch Export")


# Panel for addon settings
class AOMR_PT_main_panel(bpy.types.Panel):
    bl_label = "Age of Mythology Retold Tools"
    bl_idname = "AOMR_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AOMR"

    def draw(self, context):
        layout = self.layout

        # Import section
        box = layout.box()
        box.label(text="Import")
        row = box.row()
        row.operator(ImportTMAOperator.bl_idname, text="Import TMA")
        row.operator(ImportTMMOperator.bl_idname, text="Import TMM")

        # Export section
        box = layout.box()
        box.label(text="Export")
        row = box.row()
        row.operator(ExportTMAOperator.bl_idname, text="Export TMA")
        row.operator(ExportTMMOperator.bl_idname, text="Export TMM")

        # Batch operations
        box = layout.box()
        box.label(text="Batch Operations")
        box.operator(BatchExportOperator.bl_idname, text="Batch Export Selected")

        # Info section
        box = layout.box()
        box.label(text="Info")
        box.label(text="Select an armature to export animation")
        box.label(text="Select a mesh to export model")
        box.label(text="Select multiple objects for batch export")


# Registration
classes = [
    AOMRAddonPreferences,
    ImportTMAOperator,
    ExportTMAOperator,
    ImportTMMOperator,
    ExportTMMOperator,
    BatchExportOperator,
    AOMR_MT_import,
    AOMR_MT_export,
    AOMR_PT_main_panel,
]


def menu_func_import(self, context):
    self.layout.menu(AOMR_MT_import.bl_idname)


def menu_func_export(self, context):
    self.layout.menu(AOMR_MT_export.bl_idname)


def register():
    """Register the addon."""
    logger.info("Registering AOMR addon")

    for cls in classes:
        bpy.utils.register_class(cls)

    # Add to menus
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    logger.info("AOMR addon registered successfully")


def unregister():
    """Unregister the addon."""
    logger.info("Unregistering AOMR addon")

    # Remove from menus
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("AOMR addon unregistered successfully")


if __name__ == "__main__":
    register()
