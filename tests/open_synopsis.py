import os
from PIL import Image
import pillow_minecraft_map  # "unused" import loads the plugin as a side effect

folder = os.path.dirname(__file__)

with Image.open(f"{folder}/data/map_111.dat") as img:
    assert img.mode == "P"
    for tag in ["x_center", "z_center", "scale", "data_version"]:
        val = img.info.get(tag)
        print(f"{tag} = {val}")
    img.show()
