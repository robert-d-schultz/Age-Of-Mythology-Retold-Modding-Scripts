"""
Utilities for Age of Mythology Retold Modding Tools.

This module contains utility functions, error handling, and logging setup.
"""

from collections.abc import Callable
import functools
import logging
from pathlib import Path
import time

import bpy

from .config import AOMRConfig


class AOMRError(Exception):
    """Base exception for AOMR addon."""


class TMAFormatError(AOMRError):
    """TMA file format error."""


class TMMFormatError(AOMRError):
    """TMM file format error."""


class ValidationError(AOMRError):
    """File validation error."""


def setup_logging(name: str, user_preferences=None) -> logging.Logger:
    """Set up logging for the addon."""
    logger = logging.getLogger(name)

    # Don't add handlers if they already exist
    if logger.handlers:
        return logger

    # Set log level
    log_level = AOMRConfig.get_log_level(user_preferences)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(AOMRConfig.LOG_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    try:
        log_file_path = AOMRConfig.get_log_file_path()
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")

    return logger


def handle_errors(func: Callable) -> Callable:
    """Decorator for error handling in Blender operators."""
    @functools.wraps(func)
    def wrapper(self, context):
        try:
            return func(self, context)
        except AOMRError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        except Exception as e:
            # Log the full error for debugging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)

            # Show user-friendly message
            self.report({"ERROR"}, f"An unexpected error occurred: {e!s}")
            return {"CANCELLED"}
    return wrapper


def validate_file_path(filepath: str) -> bool:
    """Validate that a file path exists and is accessible."""
    try:
        path = Path(filepath)
        return path.exists() and path.is_file()
    except Exception:
        return False


def ensure_directory(path: str) -> str:
    """Ensure a directory exists, create if necessary."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise AOMRError(f"Could not create directory {path}: {e}")


def get_safe_filename(filename: str) -> str:
    """Convert a filename to a safe version for the filesystem."""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    safe_filename = filename
    for char in unsafe_chars:
        safe_filename = safe_filename.replace(char, "_")

    # Limit length
    if len(safe_filename) > 255:
        name, ext = safe_filename.rsplit(".", 1) if "." in safe_filename else (safe_filename, "")
        safe_filename = name[:255-len(ext)-1] + "." + ext

    return safe_filename


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def get_blender_version() -> tuple:
    """Get Blender version as tuple."""
    return bpy.app.version


def is_blender_version_at_least(major: int, minor: int, patch: int = 0) -> bool:
    """Check if Blender version is at least the specified version."""
    current = get_blender_version()
    required = (major, minor, patch)
    return current >= required


def get_active_object(context) -> bpy.types.Object | None:
    """Get the active object with validation."""
    obj = context.active_object
    if obj is None:
        raise AOMRError("No active object selected")
    return obj


def get_selected_objects(context) -> list:
    """Get selected objects with validation."""
    objects = context.selected_objects
    if not objects:
        raise AOMRError("No objects selected")
    return objects


def create_collection(name: str, parent_collection=None) -> bpy.types.Collection:
    """Create a new collection."""
    try:
        # Check if collection already exists
        existing = bpy.data.collections.get(name)
        if existing:
            return existing

        # Create new collection
        collection = bpy.data.collections.new(name)

        # Link to parent
        if parent_collection:
            parent_collection.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)

        return collection
    except Exception as e:
        raise AOMRError(f"Could not create collection '{name}': {e}")


def get_or_create_material(name: str) -> bpy.types.Material:
    """Get existing material or create new one."""
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    return material


def progress_callback(context, current: int, total: int, message: str = ""):
    """Update progress bar in Blender."""
    wm = context.window_manager
    if hasattr(wm, "progress_update"):
        progress = (current / total) * 100 if total > 0 else 0
        wm.progress_update(progress)

        if message:
            wm.progress_update(progress, message)


def time_operation(func: Callable) -> Callable:
    """Decorator to time operations for performance monitoring."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time

            logger = logging.getLogger(__name__)
            logger.info(f"{func.__name__} completed in {duration:.2f} seconds")

            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            logger = logging.getLogger(__name__)
            logger.error(f"{func.__name__} failed after {duration:.2f} seconds: {e}")
            raise

    return wrapper


def validate_blender_context(context, required_mode: str = None) -> None:
    """Validate Blender context for operations."""
    if required_mode and context.mode != required_mode:
        raise AOMRError(f"Operation requires {required_mode} mode, current mode: {context.mode}")


def backup_blender_state(context) -> dict:
    """Backup current Blender state for undo operations."""
    return {
        "mode": context.mode,
        "active_object": context.active_object,
        "selected_objects": list(context.selected_objects),
        "frame_start": context.scene.frame_start,
        "frame_end": context.scene.frame_end,
    }


def restore_blender_state(context, state: dict) -> None:
    """Restore Blender state from backup."""
    try:
        # Restore frame range
        if "frame_start" in state:
            context.scene.frame_start = state["frame_start"]
        if "frame_end" in state:
            context.scene.frame_end = state["frame_end"]

        # Restore active object
        if state.get("active_object"):
            context.view_layer.objects.active = state["active_object"]

        # Restore mode
        if "mode" in state and context.mode != state["mode"]:
            bpy.ops.object.mode_set(mode=state["mode"])

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not fully restore Blender state: {e}")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    if seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    hours = seconds / 3600
    return f"{hours:.1f} hours"


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def safe_execute_operator(operator_id: str, **kwargs) -> dict:
    """Safely execute a Blender operator."""
    try:
        result = bpy.ops.object.mode_set(mode="OBJECT")
        if result != {"FINISHED"}:
            raise AOMRError(f"Failed to execute operator {operator_id}")
        return result
    except Exception as e:
        raise AOMRError(f"Error executing operator {operator_id}: {e}")


# Performance monitoring
class PerformanceMonitor:
    """Monitor performance of operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type is None:
                self.logger.info(f"{self.operation_name} completed in {duration:.2f} seconds")
            else:
                self.logger.error(f"{self.operation_name} failed after {duration:.2f} seconds: {exc_val}")


# Context manager for progress reporting
class ProgressReporter:
    """Context manager for progress reporting."""

    def __init__(self, context, total: int, message: str = ""):
        self.context = context
        self.total = total
        self.message = message
        self.current = 0

    def __enter__(self):
        wm = self.context.window_manager
        wm.progress_begin(0, self.total)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        wm = self.context.window_manager
        wm.progress_end()

    def update(self, increment: int = 1, message: str = None):
        """Update progress."""
        self.current += increment
        wm = self.context.window_manager
        progress = (self.current / self.total) * 100 if self.total > 0 else 0
        wm.progress_update(progress, message or self.message)
