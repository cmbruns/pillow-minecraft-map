import gzip
from PIL import Image, ImageFile, ImagePalette

# --- HISTORICAL MAP PALETTES ---
MINECRAFT_1_7_MAP_PALETTE = [
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (89, 125, 39), (109, 153, 48), (127, 178, 56), (67, 94, 29),
    (174, 164, 115), (213, 201, 140), (247, 233, 163), (130, 123, 86),
    (140, 140, 140), (171, 171, 171), (199, 199, 199), (105, 105, 105),
    (180, 0, 0), (220, 0, 0), (255, 0, 0), (135, 0, 0),
    (112, 112, 180), (138, 138, 220), (160, 160, 255), (84, 84, 135),
    (117, 117, 117), (144, 144, 144), (167, 167, 167), (88, 88, 88),
    (0, 87, 0), (0, 106, 0), (0, 124, 0), (0, 65, 0),
    (180, 180, 180), (220, 220, 220), (255, 255, 255), (135, 135, 135),
    (115, 118, 129), (141, 145, 158), (164, 168, 184), (86, 88, 97),
    (106, 76, 54), (130, 94, 66), (151, 109, 77), (79, 57, 40),
    (79, 79, 79), (96, 96, 96), (112, 112, 112), (59, 59, 59),
    (45, 45, 180), (55, 55, 220), (64, 64, 255), (33, 33, 135),
    (100, 84, 50), (123, 102, 62), (143, 119, 72), (75, 63, 38)
]

MINECRAFT_1_8_MAP_PALETTE = MINECRAFT_1_7_MAP_PALETTE + [
    (180, 177, 172), (220, 217, 211), (255, 252, 245), (135, 133, 129),
    (152, 89, 36), (186, 109, 44), (216, 127, 51), (114, 67, 27),
    (125, 53, 152), (153, 65, 186), (178, 76, 216), (94, 40, 114),
    (72, 108, 152), (88, 132, 186), (102, 153, 216), (54, 81, 114),
    (161, 161, 36), (197, 197, 44), (229, 229, 51), (121, 121, 27),
    (89, 144, 17), (109, 176, 21), (127, 204, 25), (67, 108, 13),
    (170, 89, 116), (208, 109, 142), (242, 127, 165), (128, 67, 87),
    (53, 53, 53), (65, 65, 65), (76, 76, 76), (40, 40, 40),
    (108, 108, 108), (132, 132, 132), (153, 153, 153), (81, 81, 81),
    (53, 89, 108), (65, 109, 132), (76, 127, 153), (40, 67, 81),
    (89, 44, 125), (109, 54, 153), (127, 63, 178), (67, 33, 94),
    (36, 53, 125), (44, 65, 153), (51, 76, 178), (27, 40, 94),
    (72, 53, 36), (88, 65, 44), (102, 76, 51), (54, 40, 27),
    (72, 89, 36), (88, 109, 44), (102, 127, 51), (54, 67, 27),
    (108, 36, 36), (132, 44, 44), (153, 51, 51), (81, 27, 27),
    (17, 17, 17), (21, 21, 21), (25, 25, 25), (13, 13, 13),
    (176, 168, 54), (215, 205, 66), (250, 238, 77), (132, 126, 40),
    (64, 154, 150), (79, 189, 183), (92, 219, 213), (48, 116, 112),
    (52, 90, 180), (63, 110, 220), (74, 128, 255), (39, 67, 135),
    (0, 153, 40), (0, 187, 50), (0, 217, 58), (0, 114, 30),
    (91, 60, 34), (111, 74, 42), (129, 86, 49), (68, 45, 25),
    (79, 1, 0), (96, 1, 0), (112, 2, 0), (59, 1, 0)
]

MINECRAFT_1_12_MAP_PALETTE = MINECRAFT_1_8_MAP_PALETTE + [
    (147, 124, 113), (180, 152, 138), (209, 177, 161), (110, 93, 85),
    (112, 57, 25), (137, 70, 31), (159, 82, 36), (84, 43, 19),
    (105, 61, 76), (128, 75, 93), (149, 87, 108), (78, 46, 57),
    (79, 76, 97), (96, 93, 119), (112, 108, 138), (59, 57, 73),
    (131, 93, 25), (160, 114, 31), (186, 133, 36), (98, 70, 19),
    (72, 82, 37), (88, 100, 45), (103, 117, 53), (54, 61, 28),
    (112, 54, 55), (138, 66, 67), (160, 77, 78), (84, 40, 41),
    (40, 28, 24), (49, 35, 30), (57, 41, 35), (30, 21, 18),
    (95, 75, 69), (116, 92, 84), (135, 107, 98), (71, 56, 51),
    (61, 64, 64), (75, 79, 79), (87, 92, 92), (46, 48, 48),
    (86, 51, 62), (105, 62, 75), (122, 73, 88), (64, 38, 46),
    (53, 43, 64), (65, 53, 79), (76, 62, 92), (40, 32, 48),
    (53, 35, 24), (65, 43, 30), (76, 50, 35), (40, 26, 18),
    (53, 57, 29), (65, 70, 36), (76, 82, 42), (40, 43, 22),
    (100, 42, 32), (122, 51, 39), (142, 60, 46), (75, 31, 24),
    (26, 15, 11), (31, 18, 13), (37, 22, 16), (19, 11, 8)
]

MINECRAFT_1_16_MAP_PALETTE = MINECRAFT_1_12_MAP_PALETTE + [
    (133, 33, 34), (163, 41, 42), (189, 48, 49), (100, 25, 25),
    (104, 44, 68), (127, 54, 83), (148, 63, 97), (78, 33, 51),
    (64, 17, 20), (79, 21, 25), (92, 25, 29), (48, 13, 15),
    (15, 88, 94), (18, 108, 115), (22, 126, 134), (11, 66, 71),
    (40, 100, 98), (50, 122, 120), (58, 142, 140), (30, 75, 74),
    (60, 31, 43), (74, 37, 53), (86, 44, 62), (45, 23, 32),
    (14, 127, 93), (17, 155, 114), (20, 180, 133), (10, 95, 70)
]

MINECRAFT_1_18_MAP_PALETTE = MINECRAFT_1_16_MAP_PALETTE + [
    (70, 70, 70), (86, 86, 86), (100, 100, 100), (52, 52, 52),
    (152, 123, 103), (186, 150, 126), (216, 175, 147), (114, 92, 77),
    (89, 117, 105), (109, 144, 129), (127, 167, 150), (67, 88, 79)
]

MINECRAFT_1_20_MAP_PALETTE = MINECRAFT_1_18_MAP_PALETTE + [
    (104, 154, 133), (127, 189, 163), (148, 219, 189), (78, 116, 100),
    (79, 60, 52), (96, 74, 64), (112, 86, 75), (59, 45, 39),
    (149, 102, 116), (182, 124, 142), (211, 144, 165), (111, 76, 87),
    (58, 48, 31), (71, 59, 38), (83, 69, 45), (43, 36, 23)
]


class MinecraftMapImageFile(ImageFile.ImageFile):
    format = "MINECRAFT_MAP"
    format_description = "Minecraft Map Item Format (.dat)"

    @staticmethod
    def accept(prefix: bytes) -> bool:
        return len(prefix) >= 3 and prefix[:3] == b"\x1f\x8b\x08"

    def _find_tag_payload(self, tag: str) -> int:
        tag_bytes = tag.encode()
        nbt_string_prefix = len(tag_bytes).to_bytes(2, "big") + tag_bytes
        return self.file_bytes.index(nbt_string_prefix) + len(nbt_string_prefix)

    def get_byte_array(self, tag: str) -> bytes:
        pos = self._find_tag_payload(tag)
        size = int.from_bytes(self.file_bytes[pos : pos + 4], "big")
        return self.file_bytes[pos + 4 : pos + 4 + size]

    def get_int(self, tag: str) -> int:
        pos = self._find_tag_payload(tag)
        return int.from_bytes(self.file_bytes[pos : pos + 4], "big", signed=True)

    def load(self):
        if hasattr(self, "_pixels") and self._pixels is not None:
            self.load_prepare()
            self.frombytes(self._pixels, "raw", ("P", 0, 1))
            if self.palette:
                raw_mode, data_bytes = self.palette.getdata()
                self.im.putpalette("RGB", raw_mode, data_bytes)
            self._pixels = None
        return super().load()

    def _open(self) -> None:
        self.fp.seek(0)
        with gzip.open(self.fp, mode="rb") as gz:
            self.file_bytes = gz.read()

        self._pixels = self.get_byte_array("colors")
        assert 16384 == len(self._pixels)
        self._size = (128, 128)
        self._mode = "P"

        try:
            data_version = self.get_int("DataVersion")
        except ValueError:
            data_version = 0

        if data_version >= 3463:
            raw_palette = MINECRAFT_1_20_MAP_PALETTE
        elif data_version >= 2975:
            raw_palette = MINECRAFT_1_18_MAP_PALETTE
        elif data_version >= 2566:
            raw_palette = MINECRAFT_1_16_MAP_PALETTE
        elif data_version >= 1139:
            raw_palette = MINECRAFT_1_12_MAP_PALETTE
        elif data_version >= 99:
            raw_palette = MINECRAFT_1_8_MAP_PALETTE
        else:
            raw_palette = MINECRAFT_1_7_MAP_PALETTE

        flat_palette = [color for rgb in raw_palette for color in rgb]
        pil_palette = flat_palette + [0] * (768 - len(flat_palette))
        self.palette = ImagePalette.ImagePalette(mode="RGB", palette=pil_palette)

        self.fp = None


def register_plugin():
    """Safely hooks the Minecraft decoder module into Pillow's driver registry."""
    if MinecraftMapImageFile.format not in Image.ID:
        Image.register_extensions(
            MinecraftMapImageFile.format,
            extensions=[".dat"],
        )
        Image.register_open(
            MinecraftMapImageFile.format,
            MinecraftMapImageFile,
            MinecraftMapImageFile.accept,
        )
