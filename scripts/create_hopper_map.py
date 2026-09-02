from PIL import Image
import pillow_minecraft_map  # "unused" import loads the plugin as a side effect

version = "1.15"
with Image.open("../tests/data/hopper.jpg") as img:
    img.save(
        # fp=f"../tests/images/{version}/hopper.dat",
        fp=r"C:\Users\cmbruns\AppData\Roaming\.minecraft\saves\1_12_2\data\map_0.dat",
        format="MINECRAFT_MAP",
        version=version,
    )
