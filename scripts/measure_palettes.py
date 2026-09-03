from glob import glob
import re
from PIL import Image

base_comments = [
    "# Air / Transparent  ID 0->3", 
    "# Grass  ID 4->7", 
    "# Sand  ID 8->11", 
    "# Cloth / White Wool  ID 12->15", 
    "# TNT / Fire / Lava  ID 16->19", 
    "# Ice  ID 20->23", 
    "# Iron / Metal  ID 24->27", 
    "# Foliage / Plant  ID 28->31", 
    "# Snow  ID 32->35", 
    "# Clay  ID 36->39",
    "# Dirt  ID 40->43", 
    "# Stone  ID 44->47", 
    "# Water  ID 48->51", 
    "# Wood  ID 52->55", 
    "# Quartz  ID 56->59", 
    "# Orange Wool  ID 60->63", 
    "# Magenta Wool  ID 64->67", 
    "# Light Blue Wool  ID 68->71", 
    "# Yellow Wool  ID 72->75", 
    "# Lime Wool  ID 76->79", 
    "# Pink Wool  ID 80->83", 
    "# Gray Wool  ID 84->87", 
    "# Light Gray Wool  ID 88->91", 
    "# Cyan Wool  ID 92->95", 
    "# Purple Wool  ID 96->99", 
    "# Blue Wool  ID 100->103", 
    "# Brown Wool  ID 104->107", 
    "# Green Wool  ID 108->111", 
    "# Red Wool  ID 112->115", 
    "# Black Wool  ID 116->119", 
    "# Gold  ID 120->123", 
    "# Diamond  ID 124->127", 
    "# Lapis  ID 128->131", 
    "# Emerald  ID 132->135", 
    "# Podzol  ID 136->139", 
    "# Netherrack  ID 140->143", 
    "# White Terracotta  ID 144->147", 
    "# Orange Terracotta  ID 148->151", 
    "# Magenta Terracotta  ID 152->155", 
    "# Light Blue Terracotta  ID 156->159", 
    "# Yellow Terracotta  ID 160->163", 
    "# Lime Terracotta  ID 164->167", 
    "# Pink Terracotta  ID 168->171", 
    "# Gray Terracotta  ID 172->175", 
    "# Light Gray Terracotta  ID 176->179", 
    "# Cyan Terracotta  ID 180->183", 
    "# Purple Terracotta  ID 184->187", 
    "# Blue Terracotta  ID 188->191", 
    "# Brown Terracotta  ID 192->195", 
    "# Green Terracotta  ID 196->199", 
    "# Red Terracotta  ID 200->203", 
    "# Black Terracotta  ID 204->207", 
    "# Crimson Nylium  ID 208->211", 
    "# Crimson Stem  ID 212->215", 
    "# Crimson Hyphae  ID 216->219", 
    "# Warped Nylium  ID 220->223", 
    "# Warped Stem  ID 224->227", 
    "# Warped Hyphae  ID 228->231", 
    "# Warped Wart Block  ID 232->235", 
    "# Deepslate  ID 236->239", 
    "# Raw Iron  ID 240->243", 
    "# Glow Lichen  ID 244->247", 
]


def split_version(v):
    # Separate leading letters from numbers
    m = re.match(r'([A-Za-z]*)(.*)', v)
    prefix, rest = m.groups()
    if prefix == "":
        prefix = "ZZZ"  # "beta" before <nothing>
    # Extract numeric components
    nums = [int(x) for x in re.findall(r'\d+', rest)]
    return (prefix, nums)


def sort_versions(versions):
    return sorted(versions, key=split_version)


version_paths = {}
for image_path in glob("../tests/images/*.*/*.png"):
    version = re.split(r"[\\/]", image_path)[-2]
    image = Image.open(image_path)
    if image.size != (1920, 1080):
        continue
    version_paths[version] = image_path

versions = sorted(version_paths.keys(), key=split_version)


for version in versions:
    assert isinstance(version, str)
    image_path = version_paths[version]
    image = Image.open(image_path)
    v = version.replace(".", "_").upper()
    print(f"JE_{v}_PALLETTE = [")
    stride = 50.875  # pixels per palette block
    for row in range(16):
        y = int(89.5 + (0.5 + row) * stride)
        for col in range(16):
            if col % 4 == 0:
                print("   ", end="")  # indent
            x = int(552.5 + (0.5 + col) * stride)
            r, g, b = image.getpixel((x, y))[0:3]
            hex_str = f"0x{r:02X}{g:02X}{b:02X}"
            print(f"{hex_str}, ", end="")
            if col % 4 == 3:
                ix = 4 * row + col//4
                if ix >= len(base_comments):
                    ix = 0  # Air for other entries
                print(f"  {base_comments[ix]}")  # One quartet per line
    print("]")
    print("")
