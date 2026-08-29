from PIL import Image
import pillow_minecraft_map  # "unused" import loads the plugin as a side effect

with Image.open("../tests/data/hopper.jpg") as img:
    img.save("map_666.dat", format="MINECRAFT_MAP", version="1.10")
