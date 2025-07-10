# Age of Mythology Retold Modding Tools

A Blender addon for importing and exporting TMA (animation) and TMM (mesh) files used in Age of Mythology Retold modding.

## Features

### Animation Support (TMA Files)
- **Import animations** from TMA files into Blender armatures
- **Export animations** from Blender armatures to TMA files
- **Frame range control** for export
- **Static bone optimization** to reduce file size
- **Progress reporting** for long operations

### Mesh Support (TMM Files)
- **Import meshes** from TMM files into Blender
- **Export meshes** from Blender to TMM files
- **Material support** with automatic creation
- **Armature integration** for skeletal meshes
- **Attachment point handling**

### Advanced Features
- **Batch export** multiple objects at once
- **File validation** before import
- **Undo/Redo support** for all operations
- **Progress bars** for long operations
- **Comprehensive logging** for debugging
- **User preferences** panel
- **Error handling** with user-friendly messages

## Installation

### Prerequisites

The addon requires **numpy** to be installed in Blender's Python environment.

**To install numpy in Blender:**

1. **Find Blender's Python executable:**
   - **Windows:** Usually in `C:\Program Files\Blender Foundation\Blender [version]\[version]\python\bin\python.exe`
   - **macOS:** Usually in `/Applications/Blender.app/Contents/Resources/[version]/python/bin/python3`
   - **Linux:** Usually in `/usr/share/blender/[version]/python/bin/python3`

2. **Install numpy:**
   ```bash
   # Windows (run as Administrator)
   "C:\Program Files\Blender Foundation\Blender 4.0\4.0\python\bin\python.exe" -m pip install numpy

   # macOS/Linux
   /Applications/Blender.app/Contents/Resources/4.0/python/bin/python3 -m pip install numpy
   ```

3. **Alternative method (if the above doesn't work):**
   - Download the `requirements.txt` file from this repository
   - Run: `[blender-python-path] -m pip install -r requirements.txt`

4. **Using the helper script:**
   - Run: `python install_dependencies.py [blender-python-path]`
   - The script will try to find Blender Python automatically
   - Or run it from Blender's Python console directly

### Method 1: Install as Blender Addon
1. Download the `src/aomr_modding` folder
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **Install** and select the `src/aomr_modding` folder
4. Enable the addon by checking the box next to "Import-Export: Age of Mythology Retold Modding Tools"

### Method 2: Development Installation
```bash
# Clone the repository
git clone <repository-url>
cd Age-Of-Mythology-Retold-Modding-Scripts

# Install dependencies
poetry install

# Run tests
poetry run pytest tests/
```

## Usage

### Basic Import/Export

#### Import Animation (TMA)
1. Go to **File > Import > Age of Mythology Retold > TMA Animation (.tma)**
2. Select your TMA file
3. Choose import options:
   - **Create New Armature**: Create a new armature or use existing
   - **Collection Name**: Name for the imported collection

#### Export Animation (TMA)
1. Select an armature object
2. Go to **File > Export > Age of Mythology Retold > TMA Animation (.tma)**
3. Set export options:
   - **Frame Start/End**: Animation frame range
   - **Optimize Static Bones**: Reduce file size for static bones

#### Import Mesh (TMM)
1. Go to **File > Import > Age of Mythology Retold > TMM Mesh (.tmm)**
2. Select your TMM file
3. Choose import options:
   - **Create New Mesh**: Create a new mesh or use existing
   - **Create Materials**: Automatically create materials
   - **Collection Name**: Name for the imported collection

#### Export Mesh (TMM)
1. Select a mesh object
2. Go to **File > Export > Age of Mythology Retold > TMM Mesh (.tmm)**
3. Set export options:
   - **Include Armature**: Include armature data if present

### Batch Operations

#### Batch Export
1. Select multiple objects (armatures and/or meshes)
2. Go to **File > Export > Age of Mythology Retold > Batch Export**
3. Objects will be exported with their names as filenames

### Using the UI Panel

1. In the 3D Viewport, press **N** to open the sidebar
2. Go to the **AOMR** tab
3. Use the buttons to quickly import/export files

## Configuration

### User Preferences
Go to **Edit > Preferences > Add-ons > Age of Mythology Retold Modding Tools** to configure:

#### Export Settings
- **Default Export Path**: Default directory for exported files
- **Auto-create Collections**: Automatically create collections for imported objects
- **Preserve Original Names**: Keep original file names when importing
- **Compression Enabled**: Enable compression for exported files
- **Optimize Static Bones**: Use static mode for bones that don't move

#### Import Settings
- **Create Materials**: Automatically create materials for imported meshes

#### Debug Settings
- **Enable Debug Logging**: Enable detailed logging for debugging

## API Usage

The addon provides manager classes as the primary API for working with TMA and TMM files. These classes offer a clean, object-oriented interface for all file operations.

### Using the Manager Classes

```python
from aomr_modding.tma_manager import TMAManager
from aomr_modding.tmm_manager import TMMManager

# Export animation
tma_data = TMAManager.create_from_blender_armature(
    armature_object=armature,
    output_path="animation.tma",
    frame_start=1,
    frame_end=60
)

# Import animation
armature = TMAManager.import_to_blender(
    filepath="animation.tma",
    collection_name="imported_animations"
)

# Export mesh
tmm_data = TMMManager.create_from_blender_mesh(
    mesh_object=mesh,
    output_path="model.tmm",
    armature_object=armature
)

# Import mesh
mesh = TMMManager.import_to_blender(
    filepath="model.tmm",
    collection_name="imported_meshes"
)
```

### Reading Files Without Importing

```python
# Read TMA file for analysis
tma_data = TMAManager.read_tma("animation.tma")
print(f"Animation has {tma_data.frame_count} frames")
print(f"Duration: {tma_data.animation_duration} seconds")

# Read TMM file for analysis
tmm_data = TMMManager.read_tmm("model.tmm")
print(f"Mesh has {len(tmm_data.vertices)} vertices")
print(f"Materials: {tmm_data.materials}")
```

## File Format Support

### TMA (Animation) Files
- **Magic**: BTMA (1095586882)
- **Version**: 12
- **Features**:
  - Bone hierarchy
  - Keyframe animation data
  - Position and rotation tracks
  - Static bone optimization
  - Attachment points

### TMM (Mesh) Files
- **Magic**: BTMM (1296913474)
- **Version**: 35
- **Features**:
  - Vertex data with UVs and normals
  - Triangle indices
  - Material assignments
  - Bone weights
  - Bounding boxes
  - Attachment points

## Architecture

The addon follows a clean, modular architecture:

### Core Components
- **Manager Classes**: `TMAManager` and `TMMManager` provide the main API
- **Data Classes**: `TMAFile`, `TMMFile` and related classes represent file data
- **Reader/Writer Classes**: Handle low-level file I/O operations
- **Configuration**: Centralized settings in `AOMRConfig`
- **Utilities**: Helper functions for common tasks

### Design Principles
- **Separation of Concerns**: Each class has a single responsibility
- **Object-Oriented Design**: Clean interfaces with data classes
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Performance**: Optimized operations with progress reporting
- **Testability**: Unit tests for all core functionality

## Development
```
src/aomr_modding/
├── __init__.py              # Main addon registration
├── tma_manager.py           # TMA file management
├── tmm_manager.py           # TMM file management
├── config.py                # Configuration constants
├── utils.py                 # Utility functions
└── example_usage.py         # Usage examples

tests/
├── test_tma_manager.py      # TMA manager tests
└── test_tmm_manager.py      # TMM manager tests
```

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_tma_manager.py

# Run with coverage
poetry run pytest --cov=aomr_modding
```

### Code Quality
```bash
# Run linter
poetry run ruff check .

# Run formatter
poetry run ruff format .

# Fix issues automatically
poetry run ruff check --fix .
```

## Troubleshooting

### Common Issues

#### "No active object selected"
- Make sure you have selected an armature (for TMA export) or mesh (for TMM export)
- The object must be the active object (highlighted in orange)

#### "Invalid file format"
- Ensure you're using the correct file type (.tma for animations, .tmm for meshes)
- Check that the file isn't corrupted

#### Import fails
- Check the console for detailed error messages
- Ensure the file is a valid TMA/TMM file
- Try enabling debug logging in preferences

### Debug Logging
1. Go to **Edit > Preferences > Add-ons**
2. Find "Age of Mythology Retold Modding Tools"
3. Click the arrow to expand
4. Enable "Enable Debug Logging"
5. Check the console for detailed logs

### Getting Help
- Check the console for error messages
- Enable debug logging for detailed information
- Review the file format documentation
- Check that your Blender version is compatible (3.0+)

### Dependency Issues

#### "ModuleNotFoundError: No module named 'numpy'"
This means numpy is not installed in Blender's Python environment.
1. Follow the **Prerequisites** section above to install numpy
2. Restart Blender after installing numpy
3. Try installing the addon again

#### "ImportError: cannot import name 'Matrix' from 'mathutils'"
This is rare but can happen with older Blender versions.
1. Update to Blender 3.0 or later
2. The addon requires Blender 3.0+ for full compatibility

#### Addon doesn't appear in the list
1. Check the Blender console for import errors
2. Make sure you're installing the `aomr_modding` folder (not its parent)
3. Verify that all dependencies are installed
4. Try restarting Blender

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Acknowledgments

- Age of Mythology Retold development team
- Blender Foundation for the excellent addon system
- The modding community for file format research
