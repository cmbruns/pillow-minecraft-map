from PIL import Image
import pillow_minecraft_map  # "unused" import loads the plugin as a side effect

with Image.open("../tests/data/hopper.jpg") as img:
    img.save(
        fp=r"C:\Users\cmbruns\AppData\Roaming\.minecraft\saves\Creative26_2\data\minecraft\maps\3.dat",
        format="MINECRAFT_MAP",
        version=26.2,
    )
