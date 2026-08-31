# pillow-minecraft-map

A plugin for [Pillow (PIL)](https://pillow.readthedocs.io) that enables loading, viewing, saving, and manipulation of Minecraft `.dat` map item files. 

<img width="400" alt="hopper map in minecraft" src="https://github.com/user-attachments/assets/e67ba40d-1baf-49b5-b6ff-2bda11a77362" />

## Features

- Open Minecraft maps using standard Pillow syntax (`Image.open("map_0.dat")`).
- Exposes location details (`xCenter`, `zCenter`, `scale`) to Pillow's `.info` attribute.

## Important Note on Compatibility

> **Only Minecraft Java Edition map files are supported at this time.** 
> Minecraft Bedrock Edition utilizes a different map info format.

## Installation

Install the package via pip:

```bash
pip install pillow-minecraft-map
```

## Usage

Import the module to register the `.dat` plugin handlers into Pillow's image loader database.

### Reading Map Images

```python
from PIL import Image
import pillow_minecraft_map  # Activates the extension

# Open the map file
with Image.open("tests/data/map_130.dat") as img:
    # Convert from 8-bit color-indexed format ("P") to True Color ("RGB")
    rgb_img = img.convert("RGB")
    
    # Open inside your system's default image viewer
    rgb_img.show()
    
    # Export it to a standard format
    rgb_img.save("minecraft_map_render.png")
```

### Accessing Map Metadata (`info`)

The plugin maps in-game positioning values into the image's `.info` dictionary:

```python
from PIL import Image
import pillow_minecraft_map

with Image.open("tests/data/map_130.dat") as img:
    x = img.info.get("x_center")
    z = img.info.get("z_center")
    scale_factor = img.info.get("scale")
    version = img.info.get("data_version")
    
    # Calculate real-world block coverage
    block_width = 128 * (2 ** scale_factor)
    
    print(f"Minecraft DataVersion: {version}")
    print(f"Center Coordinates: X={x}, Z={z}")
    print(f"Scale: 1:{2**scale_factor} ({block_width}x{block_width} blocks total)")
```

### Saving map files

```python
from PIL import Image
import pillow_minecraft_map

with Image.open("hopper.jpg") as img:
    img.save("map_0.dat", format="MINECRAFT_MAP", version="26.2")
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
