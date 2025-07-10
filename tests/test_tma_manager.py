"""
Tests for TMA Manager.

This module contains unit tests for the TMA file manager functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import struct
from pathlib import Path

# Import the modules to test
from ..tma_manager import (
    TMAManager, TMAFile, TMAHeader, TMABone, TMAAnimationData
)
from ..config import AOMRConfig


class TestTMAHeader(unittest.TestCase):
    """Test TMA header functionality."""
    
    def test_tma_header_creation(self):
        """Test creating a TMA header."""
        header = TMAHeader(
            magic=AOMRConfig.TMA_MAGIC,
            version=AOMRConfig.TMA_VERSION,
            dp=20548
        )
        
        self.assertEqual(header.magic, AOMRConfig.TMA_MAGIC)
        self.assertEqual(header.version, AOMRConfig.TMA_VERSION)
        self.assertEqual(header.dp, 20548)


class TestTMABone(unittest.TestCase):
    """Test TMA bone functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_matrix = Mock()
        self.bone = TMABone(
            name="TestBone",
            parent_index=0,
            parent_space_matrix=self.mock_matrix,
            world_space_matrix=self.mock_matrix,
            inverse_bind_matrix=self.mock_matrix
        )
    
    def test_tma_bone_creation(self):
        """Test creating a TMA bone."""
        self.assertEqual(self.bone.name, "TestBone")
        self.assertEqual(self.bone.parent_index, 0)
        self.assertEqual(self.bone.parent_space_matrix, self.mock_matrix)
        self.assertEqual(self.bone.world_space_matrix, self.mock_matrix)
        self.assertEqual(self.bone.inverse_bind_matrix, self.mock_matrix)


class TestTMAAnimationData(unittest.TestCase):
    """Test TMA animation data functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.animation = TMAAnimationData(
            bone_name="TestBone",
            position_mode=1,
            rotation_mode=3,
            translations=[(0.0, 0.0, 0.0)],
            rotations=[Mock()]  # Mock quaternion
        )
    
    def test_tma_animation_data_creation(self):
        """Test creating TMA animation data."""
        self.assertEqual(self.animation.bone_name, "TestBone")
        self.assertEqual(self.animation.position_mode, 1)
        self.assertEqual(self.animation.rotation_mode, 3)
        self.assertEqual(len(self.animation.translations), 1)
        self.assertEqual(len(self.animation.rotations), 1)


class TestTMAFile(unittest.TestCase):
    """Test TMA file functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.header = TMAHeader(
            magic=AOMRConfig.TMA_MAGIC,
            version=AOMRConfig.TMA_VERSION,
            dp=20548
        )
        
        self.tma_file = TMAFile(
            header=self.header,
            active_bone_count=1,
            frame_count=60,
            animation_duration=2.0,
            root_position=(0.0, 0.0, 0.0),
            bones=[],
            animations=[],
            attachments=[]
        )
    
    def test_tma_file_creation(self):
        """Test creating a TMA file."""
        self.assertEqual(self.tma_file.header, self.header)
        self.assertEqual(self.tma_file.active_bone_count, 1)
        self.assertEqual(self.tma_file.frame_count, 60)
        self.assertEqual(self.tma_file.animation_duration, 2.0)
        self.assertEqual(self.tma_file.root_position, (0.0, 0.0, 0.0))


class TestTMAReader(unittest.TestCase):
    """Test TMA reader functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.tma")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)
    
    def create_test_tma_file(self):
        """Create a minimal test TMA file."""
        with open(self.test_file, 'wb') as f:
            # Header
            f.write(struct.pack("<L", AOMRConfig.TMA_MAGIC))  # Magic
            f.write(struct.pack("<L", AOMRConfig.TMA_VERSION))  # Version
            f.write(struct.pack("<H", 20548))  # DP
            
            # Import block
            f.write(struct.pack("<L", 4))  # Length
            f.write(struct.pack("<L", 0))  # No imports
            
            # Animation info
            f.write(struct.pack("<L", 1))  # Active bone count
            f.write(struct.pack("<L", 60))  # Frame count
            f.write(struct.pack("<f", 2.0))  # Duration
            
            # Root position (twice)
            for _ in range(2):
                f.write(struct.pack("<fff", 0.0, 0.0, 0.0))
            
            # Bone count and attachment count
            f.write(struct.pack("<L", 1))  # Bone count
            f.write(struct.pack("<L", 0))  # Attachment count
            
            # Bone data
            bone_name = "TestBone"
            name_bytes = bone_name.encode("UTF-16-LE")
            f.write(struct.pack("<L", len(bone_name)))
            f.write(name_bytes)
            f.write(struct.pack("<l", -1))  # Parent index
            
            # Matrices (3 x 4x4)
            for _ in range(3):
                for _ in range(16):
                    f.write(struct.pack("<f", 0.0))
            
            # Animation data
            f.write(struct.pack("<L", len(bone_name)))
            f.write(name_bytes)
            f.write(struct.pack("<BBBB", 1, 1, 3, 0))  # Modes
            f.write(struct.pack("<L", 60))  # Frame count
            
            # Position data
            f.write(struct.pack("<L", 60 * 12))  # Byte length
            for _ in range(60):
                f.write(struct.pack("<fff", 0.0, 0.0, 0.0))
            
            # Rotation data
            f.write(struct.pack("<L", 60 * 8))  # Byte length
            for _ in range(60):
                f.write(struct.pack("<Q", 0))  # Compressed quaternion
            
            # Scale data
            f.write(struct.pack("<ffff", 1.0, 1.0, 1.0, 1.0))
    
    def test_read_valid_tma_file(self):
        """Test reading a valid TMA file."""
        self.create_test_tma_file()
        
        from ..tma_manager import TMAReader
        reader = TMAReader(self.test_file)
        tma_data = reader.read()
        
        self.assertIsInstance(tma_data, TMAFile)
        self.assertEqual(tma_data.frame_count, 60)
        self.assertEqual(tma_data.animation_duration, 2.0)
        self.assertEqual(len(tma_data.bones), 1)
        self.assertEqual(len(tma_data.animations), 1)
    
    def test_read_invalid_magic(self):
        """Test reading file with invalid magic number."""
        with open(self.test_file, 'wb') as f:
            f.write(struct.pack("<L", 0x12345678))  # Invalid magic
        
        from ..tma_manager import TMAReader
        reader = TMAReader(self.test_file)
        
        with self.assertRaises(AssertionError):
            reader.read()
    
    def test_read_nonexistent_file(self):
        """Test reading a nonexistent file."""
        from ..tma_manager import TMAReader
        reader = TMAReader("nonexistent.tma")
        
        with self.assertRaises(FileNotFoundError):
            reader.read()


class TestTMAWriter(unittest.TestCase):
    """Test TMA writer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.tma")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.temp_dir)
    
    def test_write_tma_file(self):
        """Test writing a TMA file."""
        # Create test data
        header = TMAHeader(
            magic=AOMRConfig.TMA_MAGIC,
            version=AOMRConfig.TMA_VERSION,
            dp=20548
        )
        
        tma_data = TMAFile(
            header=header,
            active_bone_count=1,
            frame_count=60,
            animation_duration=2.0,
            root_position=(0.0, 0.0, 0.0),
            bones=[],
            animations=[],
            attachments=[]
        )
        
        # Write file
        from ..tma_manager import TMAWriter
        writer = TMAWriter(self.test_file)
        writer.write(tma_data)
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.test_file))
        
        # Verify file size is reasonable
        file_size = os.path.getsize(self.test_file)
        self.assertGreater(file_size, 100)  # Should be at least 100 bytes


class TestTMAManager(unittest.TestCase):
    """Test TMA manager functionality."""
    
    @patch('bpy.context')
    @patch('bpy.data')
    def test_create_from_blender_armature_mock(self, mock_bpy_data, mock_context):
        """Test creating TMA from Blender armature (mocked)."""
        # Mock Blender objects
        mock_armature = Mock()
        mock_armature.type = "ARMATURE"
        mock_armature.data.bones = []
        
        mock_scene = Mock()
        mock_scene.frame_start = 1
        mock_scene.frame_end = 60
        mock_scene.render.fps = 30
        mock_scene.render.fps_base = 1
        
        mock_context.scene = mock_scene
        mock_context.active_object = mock_armature
        
        # Mock depsgraph
        mock_depsgraph = Mock()
        mock_context.evaluated_depsgraph_get.return_value = mock_depsgraph
        
        mock_arm_obj_eval = Mock()
        mock_armature.evaluated_get.return_value = mock_arm_obj_eval
        mock_arm_obj_eval.pose.bones = []
        
        # Test the function
        with patch('builtins.open', create=True):
            result = TMAManager.create_from_blender_armature(
                armature_object=mock_armature,
                output_path="test.tma"
            )
        
        self.assertIsInstance(result, TMAFile)
        self.assertEqual(result.frame_count, 60)
    
    def test_read_tma_file(self):
        """Test reading TMA file."""
        # Create a test file
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test.tma")
        
        try:
            # Create minimal test file
            with open(test_file, 'wb') as f:
                f.write(struct.pack("<L", AOMRConfig.TMA_MAGIC))
                f.write(struct.pack("<L", AOMRConfig.TMA_VERSION))
                f.write(struct.pack("<H", 20548))
                f.write(struct.pack("<L", 4))
                f.write(struct.pack("<L", 0))
                f.write(struct.pack("<L", 0))  # Active bones
                f.write(struct.pack("<L", 0))  # Frame count
                f.write(struct.pack("<f", 0.0))  # Duration
                f.write(struct.pack("<fff", 0.0, 0.0, 0.0))  # Root pos
                f.write(struct.pack("<fff", 0.0, 0.0, 0.0))  # Root pos
                f.write(struct.pack("<L", 0))  # Bone count
                f.write(struct.pack("<L", 0))  # Attachment count
            
            # Test reading
            result = TMAManager.read_tma(test_file)
            self.assertIsInstance(result, TMAFile)
            
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            os.rmdir(temp_dir)
    
    def test_write_tma_file(self):
        """Test writing TMA file."""
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test.tma")
        
        try:
            # Create test data
            header = TMAHeader(
                magic=AOMRConfig.TMA_MAGIC,
                version=AOMRConfig.TMA_VERSION,
                dp=20548
            )
            
            tma_data = TMAFile(
                header=header,
                active_bone_count=0,
                frame_count=0,
                animation_duration=0.0,
                root_position=(0.0, 0.0, 0.0),
                bones=[],
                animations=[],
                attachments=[]
            )
            
            # Test writing
            TMAManager.write_tma(test_file, tma_data)
            
            # Verify file exists
            self.assertTrue(os.path.exists(test_file))
            
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            os.rmdir(temp_dir)


if __name__ == '__main__':
    unittest.main() 