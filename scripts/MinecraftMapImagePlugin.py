import gzip

from PIL import Image, ImageFile, ImagePalette


class MinecraftMapImageFile(ImageFile.ImageFile):
    format = "MINECRAFT_MAP"
    format_description = "Minecraft Map Item Format (.dat)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pixels = None
        self.file_bytes = b''

    @staticmethod
    def accept(prefix: bytes) -> bool:
        """
        Quickly checks the first 4-16 bytes of a file to see
        if it matches this plugin's format.
        """
        # Match only the standard GZIP magic numbers
        return len(prefix) >= 3 and prefix[:3] == b"\x1f\x8b\x08"

    # Avoid dependency on nbt. Our needs are simple here
    def get_byte_array(self, tag: str) -> bytes:
        """Fetch an NBT byte array by tag name"""
        pos = self.file_bytes.index(tag.encode())
        pos += len(tag.encode())
        size = int.from_bytes(self.file_bytes[pos:pos + 4], "big")
        pos += 4
        result: bytes = self.file_bytes[pos:pos+size]
        return result

    def get_int(self, tag: str) -> int:
        """Fetch an NBT integer value by tag name"""
        pos = self.file_bytes.index(tag.encode())
        pos += len(tag.encode())
        result = int.from_bytes(self.file_bytes[pos:pos + 4], "big", signed=True)
        return result

    def load(self):
        """Override load to push the bytes straight to the internal C core."""
        if self._pixels is not None:
            self.load_prepare()
            self.frombytes(self._pixels, "raw", ("P", 0, 1))
            if self.palette:
                raw_mode, data_bytes = self.palette.getdata()
                self.im.putpalette("RGB", raw_mode, data_bytes)
            self._pixels = None
        return super().load()

    def _open(self) -> None:
        """
        Reads the file header, sets metadata, and loads the small pixel array.
        """
        # 1. Rewind the stream and open it as a GZIP stream
        self.fp.seek(0)
        with gzip.open(self.fp, mode="rb") as gz:
            self.file_bytes = gz.read()
        self._pixels = self.get_byte_array("colors")
        assert 128 * 128 == len(self._pixels)
        self._size = 128, 128
        self._mode = "P"
        # Palette
        data_version = self.get_int("DataVersion")
        # TODO - other version palettes
        assert data_version == 2975  # Minecraft Java Edition 1.18.2
        palette = MINECRAFT_1_18_MAP_PALETTE
        # Flatten the list of RGB tuples into a 1D sequence of integers
        flat_palette = [color for rgb in palette for color in rgb]
        # Pad out to exactly 768 entries (256 colors * 3 channels) using zeros
        pil_palette = flat_palette + [0] * (768 - len(flat_palette))
        assert len(pil_palette) == 768
        self.palette = ImagePalette.ImagePalette(mode="RGB", palette=pil_palette)
        self.fp = None


Image.register_extensions(
    MinecraftMapImageFile.format,
    extensions=[".dat"],
)

Image.register_open(
    MinecraftMapImageFile.format,
    MinecraftMapImageFile,
    MinecraftMapImageFile.accept,
)

# Minecraft Java 1.18.2 (DataVersion 2975) complete Map Palette
# Contains 244 RGB triples organized sequentially (4 shaded variants per base ID)
# Order per ID: [Darkest (0), Darker (1), Normal (2), Brighter (3)]

MINECRAFT_1_18_MAP_PALETTE = [
    # ID 0: Air / Transparent
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    # ID 1: Grass
    (89, 125, 39), (109, 153, 48), (127, 178, 56), (67, 94, 29),
    # ID 2: Sand
    (174, 164, 115), (213, 201, 140), (247, 233, 163), (130, 123, 86),
    # ID 3: Cloth / White Wool
    (140, 140, 140), (171, 171, 171), (199, 199, 199), (105, 105, 105),
    # ID 4: TNT / Fire / Lava
    (180, 0, 0), (220, 0, 0), (255, 0, 0), (135, 0, 0),
    # ID 5: Ice
    (112, 112, 180), (138, 138, 220), (160, 160, 255), (84, 84, 135),
    # ID 6: Iron / Metal
    (117, 117, 117), (144, 144, 144), (167, 167, 167), (88, 88, 88),
    # ID 7: Foliage / Plant
    (0, 87, 0), (0, 106, 0), (0, 124, 0), (0, 65, 0),
    # ID 8: Snow
    (180, 180, 180), (220, 220, 220), (255, 255, 255), (135, 135, 135),
    # ID 9: Clay
    (115, 118, 129), (141, 145, 158), (164, 168, 184), (86, 88, 97),
    # ID 10: Dirt
    (106, 76, 54), (130, 94, 66), (151, 109, 77), (79, 57, 40),
    # ID 11: Stone
    (79, 79, 79), (96, 96, 96), (112, 112, 112), (59, 59, 59),
    # ID 12: Water
    (45, 45, 180), (55, 55, 220), (64, 64, 255), (33, 33, 135),
    # ID 13: Wood
    (100, 84, 50), (123, 102, 62), (143, 119, 72), (75, 63, 38),
    # ID 14: Quartz
    (180, 177, 172), (220, 217, 211), (255, 252, 245), (135, 133, 129),
    # ID 15: Orange Wool
    (152, 89, 36), (186, 109, 44), (216, 127, 51), (114, 67, 27),
    # ID 16: Magenta Wool
    (125, 53, 152), (153, 65, 186), (178, 76, 216), (94, 40, 114),
    # ID 17: Light Blue Wool
    (72, 108, 152), (88, 132, 186), (102, 153, 216), (54, 81, 114),
    # ID 18: Yellow Wool
    (161, 161, 36), (197, 197, 44), (229, 229, 51), (121, 121, 27),
    # ID 19: Lime Wool
    (89, 144, 17), (109, 176, 21), (127, 204, 25), (67, 108, 13),
    # ID 20: Pink Wool
    (170, 89, 116), (208, 109, 142), (242, 127, 165), (128, 67, 87),
    # ID 21: Gray Wool
    (53, 53, 53), (65, 65, 65), (76, 76, 76), (40, 40, 40),
    # ID 22: Light Gray Wool
    (108, 108, 108), (132, 132, 132), (153, 153, 153), (81, 81, 81),
    # ID 23: Cyan Wool
    (53, 89, 108), (65, 109, 132), (76, 127, 153), (40, 67, 81),
    # ID 24: Purple Wool
    (89, 44, 125), (109, 54, 153), (127, 63, 178), (67, 33, 94),
    # ID 25: Blue Wool
    (36, 53, 125), (44, 65, 153), (51, 76, 178), (27, 40, 94),
    # ID 26: Brown Wool
    (72, 53, 36), (88, 65, 44), (102, 76, 51), (54, 40, 27),
    # ID 27: Green Wool
    (72, 89, 36), (88, 109, 44), (102, 127, 51), (54, 67, 27),
    # ID 28: Red Wool
    (108, 36, 36), (132, 44, 44), (153, 51, 51), (81, 27, 27),
    # ID 29: Black Wool
    (17, 17, 17), (21, 21, 21), (25, 25, 25), (13, 13, 13),
    # ID 30: Gold
    (176, 168, 54), (215, 205, 66), (250, 238, 77), (132, 126, 40),
    # ID 31: Diamond
    (64, 154, 150), (79, 189, 183), (92, 219, 213), (48, 116, 112),
    # ID 32: Lapis
    (52, 90, 180), (63, 110, 220), (74, 128, 255), (39, 67, 135),
    # ID 33: Emerald
    (0, 153, 40), (0, 187, 50), (0, 217, 58), (0, 114, 30),
    # ID 34: Podzol
    (91, 60, 34), (111, 74, 42), (129, 86, 49), (68, 45, 25),
    # ID 35: Netherrack
    (79, 1, 0), (96, 1, 0), (112, 2, 0), (59, 1, 0),
    # ID 36: White Terracotta
    (147, 124, 113), (180, 152, 138), (209, 177, 161), (110, 93, 85),
    # ID 37: Orange Terracotta
    (112, 57, 25), (137, 70, 31), (159, 82, 36), (84, 43, 19),
    # ID 38: Magenta Terracotta
    (105, 61, 76), (128, 75, 93), (149, 87, 108), (78, 46, 57),
    # ID 39: Light Blue Terracotta
    (79, 76, 97), (96, 93, 119), (112, 108, 138), (59, 57, 73),
    # ID 40: Yellow Terracotta
    (131, 93, 25), (160, 114, 31), (186, 133, 36), (98, 70, 19),
    # ID 41: Lime Terracotta
    (72, 82, 37), (88, 100, 45), (103, 117, 53), (54, 61, 28),
    # ID 42: Pink Terracotta
    (112, 54, 55), (138, 66, 67), (160, 77, 78), (84, 40, 41),
    # ID 43: Gray Terracotta
    (40, 28, 24), (49, 35, 30), (57, 41, 35), (30, 21, 18),
    # ID 44: Light Gray Terracotta
    (95, 75, 69), (116, 92, 84), (135, 107, 98), (71, 56, 51),
    # ID 45: Cyan Terracotta
    (61, 64, 64), (75, 79, 79), (87, 92, 92), (46, 48, 48),
    # ID 46: Purple Terracotta
    (86, 51, 62), (105, 62, 75), (122, 73, 88), (64, 38, 46),
    # ID 47: Blue Terracotta
    (53, 43, 64), (65, 53, 79), (76, 62, 92), (40, 32, 48),
    # ID 48: Brown Terracotta
    (53, 35, 24), (65, 43, 30), (76, 50, 35), (40, 26, 18),
    # ID 49: Green Terracotta
    (53, 57, 29), (65, 70, 36), (76, 82, 42), (40, 43, 22),
    # ID 50: Red Terracotta
    (100, 42, 32), (122, 51, 39), (142, 60, 46), (75, 31, 24),
    # ID 51: Black Terracotta
    (26, 15, 11), (31, 18, 13), (37, 22, 16), (19, 11, 8),
    # ID 52: Crimson Nylium
    (133, 33, 34), (163, 41, 42), (189, 48, 49), (100, 25, 25),
    # ID 53: Crimson Stem
    (104, 44, 68), (127, 54, 83), (148, 63, 97), (78, 33, 51),
    # ID 54: Crimson Hyphae
    (64, 17, 20), (79, 21, 25), (92, 25, 29), (48, 13, 15),
    # ID 55: Warped Nylium
    (15, 88, 94), (18, 108, 115), (22, 126, 134), (11, 66, 71),
    # ID 56: Warped Stem
    (40, 100, 98), (50, 122, 120), (58, 142, 140), (30, 75, 74),
    # ID 57: Warped Hyphae
    (60, 31, 43), (74, 37, 53), (86, 44, 62), (45, 23, 32),
    # ID 58: Warped Wart Block
    (15, 88, 94), (18, 108, 115), (22, 126, 134), (11, 66, 71),
    # ID 59: Deepslate
    (70, 70, 70), (86, 86, 86), (100, 100, 100), (52, 52, 52),
    # ID 60: Raw Iron
    (152, 123, 103), (186, 150, 126), (216, 175, 147), (114, 92, 77),
    # ID 61: Glow Lichen
    (89, 117, 105), (109, 144, 129), (127, 167, 150), (67, 88, 79)
]


def main():
    with Image.open("../test/map_111.dat") as img:
        assert img.mode == "P"
        img.show()


if __name__ == "__main__":
    main()
