"""
Configuration for Age of Mythology Retold Modding Tools.

This module contains all configuration constants and settings used throughout the addon.
"""

from pathlib import Path


class AOMRConfig:
    """Configuration class for AOMR addon."""

    # File format magic numbers
    TMA_MAGIC = 1095586882  # BTMA
    TMM_MAGIC = 1296913474  # BTMM

    # File format versions
    TMA_VERSION = 12
    TMM_VERSION = 35

    # Default settings
    DEFAULT_FRAME_RANGE = (1, 60)
    DEFAULT_COLLECTION_PREFIX = "AOMR_"
    DEFAULT_EXPORT_PATH = str(Path.home() / "Documents" / "AOMR_Exports")

    # Export options
    COMPRESSION_ENABLED = True
    OPTIMIZE_STATIC_BONES = True
    AUTO_CREATE_COLLECTIONS = True
    PRESERVE_ORIGINAL_NAMES = True

    # Import options
    CREATE_MATERIALS = True
    CREATE_ARMATURE_MODIFIER = True

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = "aomr_addon.log"

    # UI settings
    PANEL_CATEGORY = "AOMR"
    PANEL_LABEL = "Age of Mythology Retold Tools"

    # File extensions
    TMA_EXTENSION = ".tma"
    TMM_EXTENSION = ".tmm"

    # Batch export settings
    BATCH_EXPORT_MAX_OBJECTS = 100
    BATCH_EXPORT_TIMEOUT = 300  # seconds

    # Progress reporting
    PROGRESS_UPDATE_INTERVAL = 0.1  # seconds

    # Error handling
    MAX_ERROR_MESSAGES = 3
    ERROR_MESSAGE_LENGTH = 100

    @classmethod
    def get_export_path(cls, user_preferences=None):
        """Get the export path from user preferences or default."""
        if user_preferences and user_preferences.default_export_path:
            return user_preferences.default_export_path
        return cls.DEFAULT_EXPORT_PATH

    @classmethod
    def ensure_export_path(cls, user_preferences=None):
        """Ensure the export path exists."""
        export_path = cls.get_export_path(user_preferences)
        Path(export_path).mkdir(parents=True, exist_ok=True)
        return export_path

    @classmethod
    def get_log_level(cls, user_preferences=None):
        """Get log level from user preferences or default."""
        if user_preferences and user_preferences.enable_debug_logging:
            return "DEBUG"
        return cls.LOG_LEVEL

    @classmethod
    def get_log_file_path(cls):
        """Get the log file path."""
        log_dir = Path.home() / ".aomr_addon" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir / cls.LOG_FILE)


# File format constants
TMA_FORMAT = {
    "magic": AOMRConfig.TMA_MAGIC,
    "version": AOMRConfig.TMA_VERSION,
    "dp": 20548,
    "extension": AOMRConfig.TMA_EXTENSION,
    "description": "Age of Mythology Retold Animation File"
}

TMM_FORMAT = {
    "magic": AOMRConfig.TMM_MAGIC,
    "version": AOMRConfig.TMM_VERSION,
    "dp": 20548,
    "extension": AOMRConfig.TMM_EXTENSION,
    "description": "Age of Mythology Retold Mesh File"
}

# Supported file formats
SUPPORTED_FORMATS = {
    "tma": TMA_FORMAT,
    "tmm": TMM_FORMAT
}

# UI text constants
UI_TEXTS = {
    "addon_name": "Age of Mythology Retold Modding Tools",
    "panel_title": "AOMR Tools",
    "import_section": "Import",
    "export_section": "Export",
    "batch_section": "Batch Operations",
    "info_section": "Info",
    "select_armature": "Select an armature to export animation",
    "select_mesh": "Select a mesh to export model",
    "select_multiple": "Select multiple objects for batch export",
    "success": "Success",
    "error": "Error",
    "warning": "Warning",
    "info": "Information"
}

# Error messages
ERROR_MESSAGES = {
    "no_armature_selected": "Please select an armature object",
    "no_mesh_selected": "Please select a mesh object",
    "no_objects_selected": "Please select objects to export",
    "invalid_tma_format": "Invalid TMA file format",
    "invalid_tmm_format": "Invalid TMM file format",
    "unsupported_version": "Unsupported file version: {}",
    "file_validation_failed": "File validation failed: {}",
    "import_failed": "Import failed: {}",
    "export_failed": "Export failed: {}",
    "batch_export_failed": "Batch export failed: {}"
}

# Success messages
SUCCESS_MESSAGES = {
    "tma_imported": "Successfully imported animation from {}",
    "tmm_imported": "Successfully imported mesh from {}",
    "tma_exported": "Successfully exported animation with {} frames",
    "tmm_exported": "Successfully exported mesh with {} vertices",
    "batch_exported": "Successfully exported {} objects",
    "addon_registered": "AOMR addon registered successfully",
    "addon_unregistered": "AOMR addon unregistered successfully"
}
