import PIL
from PIL import Image
import pillow_minecraft_map  # "unused" import loads the plugin as a side effect

with Image.open("../tests/data/map_111.dat") as img:
    print(PIL.__version__)
    assert img.mode == "P"
    for tag in ["x_center", "z_center", "scale", "data_version"]:
        val = img.info.get(tag)
        print(f"{tag} = {val}")
    img.show()
