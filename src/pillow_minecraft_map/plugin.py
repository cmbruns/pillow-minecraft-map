"""
Module pillow_minecraft_map

PIL plugin for loading a Minecraft map info file as an Image.
These files are usually stored in server files like "world/data/map_<id>.dat"
Minecraft Java Edition map info files are gzipped NBT files.

Limitations:
  * Support for Minecraft Jave Edition map info files only. Bedrock Edition maps
  are not currently supported.
"""


import gzip
import logging
import re
from typing import cast, BinaryIO
from PIL import Image, ImageFile, ImagePalette

logger = logging.getLogger("PIL.MinecraftMapPlugin")

# Version 1.17 is valid from version 1.17 onward at least to 26.2
# and is a superset of palettes going back to 1.8.3 or earlier
JE_1_17_PALETTE = [
    # ID 0->3: Air / Transparent
    (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    # ID 4->7: Grass
    (89, 125, 39), (109, 153, 48), (127, 178, 56), (67, 94, 29),
    # ID 8->11: Sand
    (174, 164, 115), (213, 201, 140), (247, 233, 163), (130, 123, 86),
    # ID 12->15: Cloth / White Wool
    (140, 140, 140), (171, 171, 171), (199, 199, 199), (105, 105, 105),

    # ID 16->19: TNT / Fire / Lava
    (180, 0, 0), (220, 0, 0), (255, 0, 0), (135, 0, 0),
    # ID 20->23: Ice
    (112, 112, 180), (138, 138, 220), (160, 160, 255), (84, 84, 135),
    # ID 24->27: Iron / Metal
    (117, 117, 117), (144, 144, 144), (167, 167, 167), (88, 88, 88),
    # ID 28->31: Foliage / Plant
    (0, 87, 0), (0, 106, 0), (0, 124, 0), (0, 65, 0),

    # ID 32->35: Snow
    (180, 180, 180), (220, 220, 220), (255, 255, 255), (135, 135, 135),
    # ID 36->39:  Clay
    (115, 118, 129), (141, 144, 158), (164, 168, 184), (86, 88, 97),
    # ID 40->43: Dirt
    (106, 76, 54), (130, 94, 66), (151, 109, 77), (79, 57, 40),
    # ID 44->47: Stone
    (79, 79, 79), (96, 96, 96), (112, 112, 112), (59, 59, 59),

    # ID 48->51: Water
    (45, 45, 180), (55, 55, 220), (64, 64, 255), (33, 33, 135),
    # ID 52->55: Wood
    (100, 84, 50), (123, 102, 62), (143, 119, 72), (75, 63, 38),
    # ID 56->59: Quartz
    (180, 177, 172), (220, 217, 211), (255, 252, 245), (135, 133, 129),
    # ID 60->63: Orange Wool
    (152, 89, 36), (186, 109, 44), (216, 127, 51), (114, 67, 27),

    # ID 64->67: Magenta Wool
    (125, 53, 152), (153, 65, 186), (178, 76, 216), (94, 40, 114),
    # ID 68->71: Light Blue Wool
    (72, 108, 152), (88, 132, 186), (102, 153, 216), (54, 81, 114),
    # ID 72->75: Yellow Wool
    (161, 161, 36), (197, 197, 44), (229, 229, 51), (121, 121, 27),
    # ID 76->79: Lime Wool
    (89, 144, 17), (109, 176, 21), (127, 204, 25), (67, 108, 13),

    # ID 80->83: Pink Wool
    (170, 89, 116), (208, 109, 142), (242, 127, 165), (128, 67, 87),
    # ID 84->87: Gray Wool
    (53, 53, 53), (65, 65, 65), (76, 76, 76), (40, 40, 40),
    # ID 88->91: Light Gray Wool
    (108, 108, 108), (132, 132, 132), (153, 153, 153), (81, 81, 81),
    # ID 92->95: Cyan Wool
    (53, 89, 108), (65, 109, 132), (76, 127, 153), (40, 67, 81),

    # ID 96->99: Purple Wool
    (89, 44, 125), (109, 54, 153), (126, 63, 178), (67, 32, 94),
    # ID 100->103: Blue Wool
    (36, 53, 125), (44, 65, 153), (51, 76, 178), (27, 40, 94),
    # ID 104->107: Brown Wool
    (72, 53, 36), (88, 65, 44), (102, 76, 51), (54, 40, 27),
    # ID 108->111: Green Wool
    (72, 89, 36), (88, 109, 44), (101, 126, 50), (54, 67, 27),

    # ID 112->115: Red Wool
    (108, 36, 36), (132, 44, 44), (153, 51, 51), (81, 27, 27),
    # ID 116->119: Black Wool
    (17, 17, 17), (21, 21, 21), (25, 25, 25), (13, 13, 13),
    # ID 120->123: Gold
    (176, 168, 54), (215, 205, 66), (250, 238, 77), (132, 126, 40),
    # ID 124->127: Diamond
    (64, 154, 150), (79, 188, 183), (92, 219, 213), (48, 115, 112),

    # ID 128->131: Lapis
    (52, 90, 180), (63, 110, 220), (74, 128, 255), (39, 67, 135),
    # ID 132->135: Emerald
    (0, 153, 40), (0, 187, 50), (0, 217, 58), (0, 114, 30),
    # ID 136->139: Podzol
    (91, 60, 34), (111, 74, 42), (129, 86, 49), (68, 45, 25),
    # ID 140->143: Netherrack
    (79, 1, 0), (96, 1, 0), (112, 2, 0), (59, 1, 0),

    # ID 144->147: White Terracotta
    (147, 124, 113), (180, 152, 138), (208, 177, 161), (110, 93, 85),
    # ID 148->151: Orange Terracotta
    (112, 57, 25), (137, 70, 31), (159, 82, 36), (84, 43, 19),
    # ID 152->155: Magenta Terracotta
    (105, 61, 76), (128, 75, 93), (149, 87, 108), (78, 46, 57),
    # ID 156->159: Light Blue Terracotta
    (79, 76, 97), (96, 93, 119), (111, 108, 138), (59, 57, 73),

    # ID 160->163: Yellow Terracotta
    (131, 93, 25), (160, 114, 31), (186, 133, 36), (98, 70, 19),
    # ID 164->167: Lime Terracotta
    (72, 82, 37), (88, 100, 45), (103, 117, 53), (54, 61, 28),
    # ID 168->171: Pink Terracotta
    (112, 54, 55), (138, 66, 67), (160, 77, 78), (84, 40, 41),
    # ID 172->175: Gray Terracotta
    (40, 28, 24), (49, 35, 30), (57, 40, 35), (30, 21, 18),

    # ID 176->179: Light Gray Terracotta
    (95, 75, 69), (116, 92, 84), (135, 107, 98), (71, 56, 51),
    # ID 180->183: Cyan Terracotta
    (61, 64, 64), (75, 79, 79), (87, 92, 92), (46, 48, 48),
    # ID 184->187: Purple Terracotta
    (86, 51, 62), (105, 62, 75), (121, 73, 88), (64, 38, 46),
    # ID 188->191: Blue Terracotta
    (53, 43, 64), (65, 53, 79), (76, 62, 91), (40, 32, 48),

    # ID 192->195: Brown Terracotta
    (53, 35, 24), (65, 43, 30), (75, 50, 35), (40, 26, 18),
    # ID 196->199: Green Terracotta
    (53, 57, 29), (65, 70, 36), (76, 82, 42), (40, 43, 22),
    # ID 200->203: Red Terracotta
    (100, 42, 32), (122, 51, 39), (142, 60, 46), (75, 31, 24),
    # ID 204->207: Black Terracotta
    (26, 15, 11), (31, 18, 13), (37, 22, 16), (19, 11, 8),

    # ID 208->211: Crimson Nylium
    (133, 33, 34), (163, 41, 42), (188, 48, 49), (100, 25, 25),
    # ID 212->215: Crimson Stem
    (104, 44, 68), (127, 54, 83), (148, 63, 97), (78, 33, 51),
    # ID 216->219: Crimson Hyphae
    (64, 17, 20), (79, 21, 25), (92, 25, 29), (48, 13, 15),
    # ID 220->223: Warped Nylium
    (15, 88, 94), (18, 108, 115), (22, 126, 134), (11, 65, 70),

    # ID 224->227: Warped Stem
    (40, 100, 98), (50, 122, 120), (58, 142, 140), (30, 75, 74),
    # ID 228->231: Warped Hyphae
    (60, 31, 43), (74, 37, 53), (86, 44, 62), (45, 23, 32),
    # ID 232->235: Warped Wart Block
    (14, 127, 93), (17, 155, 114), (20, 180, 133), (10, 95, 70),
    # ID 236->239: Deepslate
    (70, 70, 70), (86, 86, 86), (100, 100, 100), (52, 52, 52),

    # ID 240->243: Raw Iron
    (152, 123, 103), (186, 150, 126), (216, 175, 147), (114, 92, 77),
    # ID 244->247: Glow Lichen
    (89, 117, 105), (109, 144, 129), (127, 167, 150), (67, 88, 79),
]


class MinecraftMapImageFile(ImageFile.ImageFile):
    format = "MINECRAFT_MAP"
    format_description = "Minecraft Map Item Format (.dat)"

    @staticmethod
    def accept(prefix: bytes) -> bool:
        """
        Quickly checks the first 4-16 bytes of a file to see
        if it matches this plugin's format.
        """
        # Match only the standard GZIP magic numbers
        return len(prefix) >= 3 and prefix[:3] == b"\x1f\x8b\x08"

    def _find_tag_payload(self, tag: str) -> int:
        tag_bytes = tag.encode()
        nbt_string_prefix = len(tag_bytes).to_bytes(2, "big") + tag_bytes
        return self.file_bytes.index(nbt_string_prefix) + len(nbt_string_prefix)

    def get_byte(self, tag: str) -> int:
        """Fetch an NBT single byte value by tag name."""
        pos = self._find_tag_payload(tag)
        return int.from_bytes(self.file_bytes[pos: pos + 1], "big", signed=True)

    def get_byte_array(self, tag: str) -> bytes:
        """Fetch an NBT byte array by tag name"""
        pos = self._find_tag_payload(tag)
        size = int.from_bytes(self.file_bytes[pos: pos + 4], "big")
        return self.file_bytes[pos + 4: pos + 4 + size]

    def get_int(self, tag: str) -> int:
        """Fetch an NBT integer value by tag name"""
        pos = self._find_tag_payload(tag)
        return int.from_bytes(self.file_bytes[pos: pos + 4], "big", signed=True)

    def load(self):
        """Override load to push the bytes straight to the internal C core."""
        if hasattr(self, "_pixels") and self._pixels is not None:
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
        self._pixels = None
        # 1. Rewind the stream and open it as a GZIP stream
        fp = cast(BinaryIO, self.fp)  # to silence the PyCharm linter
        fp.seek(0)
        with gzip.open(fp, mode="rb") as gz:
            _fb = gz.read()
            self.file_bytes: bytes = _fb
        self._pixels = self.get_byte_array("colors")
        assert isinstance(self._pixels, bytes)
        assert 128*128 == len(self._pixels)
        self._size = 128, 128
        # Handle color palette
        self._mode = "P"
        try:
            data_version = self.get_int("DataVersion")
        except ValueError:
            # Fallback layout if DataVersion string signature is absent in older files
            data_version = 0
        raw_palette = JE_1_17_PALETTE  # Mostly valid back to before 1.8.3
        # TODO: support minor variations, and very old palettes like beta1.6 etc.
        # Flatten the list of RGB tuples into a 1D sequence of integers
        flat_palette = [color for rgb in raw_palette for color in rgb]
        # Pad out to exactly 768 entries (256 colors * 3 channels) using zeros
        pil_palette = flat_palette + [0] * (768 - len(flat_palette))
        self.palette = ImagePalette.ImagePalette(mode="RGB", palette=pil_palette)
        # Parse metadata
        try:
            x_center = self.get_int("xCenter")
            z_center = self.get_int("zCenter")
            scale = self.get_byte("scale")
        except ValueError:
            # Safe fallbacks if parsing legacy/custom map structures
            x_center, z_center, scale = 0, 0, 0
        # Inject into Pillow's metadata API
        self.info["x_center"] = x_center
        self.info["z_center"] = z_center
        self.info["scale"] = scale
        self.info["data_version"] = data_version
        self.info["transparency"] = 0
        # File handle is no longer needed now
        self.fp = None


def _encode_nbt_string(name: str) -> bytes:
    encoded = name.encode("utf-8")
    return len(encoded).to_bytes(2, "big") + encoded


def _save(im: Image.Image, fp, _filename):
    """
    Saves a Pillow image structure back into a standard Minecraft Java .dat map item.
    Automatically handles resizing, alpha transparency layers, and color quantization.
    Supports optional version mapping parameters: im.save(fp, version="1.18")
    """

    # READ OPTIONAL USER PARAMETER (Default to latest safe profile)
    user_version = im.encoderinfo.get("version", "26.2")
    data_version, palette_size = palette_size_for_version(user_version)

    # EVALUATE AND RESAMPLE GEOMETRY BOUNDS
    width, height = im.size
    aspect_ratio = width / height

    if aspect_ratio > 1.8 or aspect_ratio < (1 / 1.8):
        raise ValueError(
            f"Image aspect ratio ({aspect_ratio:.2f}) is outside acceptable limits "
            f"(1.8, 1/1.8). Pre-crop the image to avoid extreme distortion."
        )

    if im.size != (128, 128):
        logger.warning(
            f"Image dimensions {im.size} resized automatically to 128x128 for Minecraft compatibility."
        )
        # Use high-quality Resampling.LANCZOS for downscaling crisp details
        im = im.resize((128, 128), resample=Image.Resampling.LANCZOS)

    # 2. SEPARATE ALPHA TRANSPARENCY MASK FOR MINECRAFT INDEX 0
    alpha_mask = None
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        logger.info("Alpha/Transparency transparency maps detected. Mapping to Map Air Index (0).")
        # Split out alpha channel matrix
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        _, _, _, alpha_channel = im.split()
        # Pixel index is 0 wherever transparency falls below a strict opacity threshold
        alpha_mask = alpha_channel.point(lambda p: 255 if p < 128 else 0)

    # 3. QUANTIZE TRUE COLOR CHANNELS TO MINECRAFT 1.20 PALETTE
    logger.warning(f"Projecting image data down into Minecraft {user_version} color space palette.")

    # Compile a flat 768-integer palette template required by PIL's quantize core
    raw_palette = JE_1_17_PALETTE[: palette_size]
    # Flatten the list of RGB tuples into a 1D sequence of integers
    flat_palette = [color for rgb in raw_palette for color in rgb]
    padded_palette = flat_palette + [0] * (768 - len(flat_palette))

    # Construct an anchor reference image containing our strict 1.20 palette layout
    palette_anchor = Image.new("P", (1, 1))
    palette_anchor.putpalette(padded_palette)

    # Quantize the input image down to the closest matching palette colors using Floyd-Steinberg dithering
    quantized_im = im.convert("RGB").quantize(palette=palette_anchor, dither=Image.Dither.FLOYDSTEINBERG)
    pixel_bytes = bytearray(quantized_im.tobytes())

    # 4. OVERLAY TRANSPARENCY BACK TO INDEX 0 IF APPLICABLE
    if alpha_mask is not None:
        transparent_bytes = alpha_mask.tobytes()
        for idx in range(16384):
            if transparent_bytes[idx] == 255:
                pixel_bytes[idx] = 0  # Reassign value to ID 0 (Air/Transparent)

    # 5. RETRIEVE METADATA VARIANTS OR APPLY IN-GAME DEFAULTS
    x_center = im.info.get("x_center", 0)
    z_center = im.info.get("z_center", 0)
    scale = im.info.get("scale", 0)
    data_version = im.info.get("data_version", data_version)  # Default to standard 1.20+

    # 6. ASSEMBLE RAW BINARY NBT ARCHITECTURE CHUNKS
    nbt_payload = bytearray()

    # Root TAG_Compound
    nbt_payload.append(0x0a)
    nbt_payload.extend(_encode_nbt_string(""))

    # DataVersion Tag (TAG_Int)
    nbt_payload.append(0x03)
    nbt_payload.extend(_encode_nbt_string("DataVersion"))
    nbt_payload.extend(data_version.to_bytes(4, "big", signed=True))

    # data TAG_Compound container entry point
    nbt_payload.append(0x0a)
    nbt_payload.extend(_encode_nbt_string("data"))

    # xCenter
    nbt_payload.append(0x03)
    nbt_payload.extend(_encode_nbt_string("xCenter"))
    nbt_payload.extend(x_center.to_bytes(4, "big", signed=True))

    # zCenter
    nbt_payload.append(0x03)
    nbt_payload.extend(_encode_nbt_string("zCenter"))
    nbt_payload.extend(z_center.to_bytes(4, "big", signed=True))

    # scale
    nbt_payload.append(0x01)
    nbt_payload.extend(_encode_nbt_string("scale"))
    nbt_payload.extend(scale.to_bytes(1, "big", signed=True))

    # Standard boilerplate tracking tags
    for tag_name, val in [("trackingPosition", 0), ("unlimitedTracking", 0), ("locked", 1)]:
        nbt_payload.append(0x01)
        nbt_payload.extend(_encode_nbt_string(tag_name))
        nbt_payload.append(val)

    # colors TAG_Byte_Array payload array injection block
    nbt_payload.append(0x07)
    nbt_payload.extend(_encode_nbt_string("colors"))
    nbt_payload.extend(len(pixel_bytes).to_bytes(4, "big"))
    nbt_payload.extend(pixel_bytes)

    # Close data and root tags safely
    nbt_payload.append(0x00)
    nbt_payload.append(0x00)

    # 7. EXPORT COMPRESSED STREAM TO DISK
    with gzip.open(fp, mode="wb") as gz:
        gz.write(nbt_payload)


def palette_size_for_version(version) -> tuple[int, int]:
    """
    Accepts Minecraft versions or DataVersions in many formats and returns
    the correct palette truncation size (number of palette entries to keep).
    """

    # --- 1. Normalize input to string ---
    v = str(version).strip().lower()

    # --- 2. Handle DataVersion integers ---
    # Pure integer? Treat as DataVersion.
    if v.isdigit():
        dv = int(v)
        if dv < 1139:  # pre 1.12
            return dv, 36*4
        elif dv < 2566:  # pre 1.16
            return dv, 52*4
        else:  # post 1.17
            return dv, 62*4

    # --- 3. Handle beta versions ---
    if v.startswith("beta") or v.startswith("b"):
        return 0, 14*4  # TODO: betas after 1.6 might have more valid entries?

    # --- 4. Extract numeric version components ---
    # Examples: "1.12.2", "1.17", "26.2"
    m = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", v)
    if m:
        major = int(m.group(1))
        minor = int(m.group(2) or 0)
        patch = int(m.group(3) or 0)

        if major < 1 or (major == 1 and minor <= 12):
            return 99, 36*4  # at least back to 1.8.3 anyway
        elif major == 1 and minor <= 16:
            return 1139, 52*4
        elif major == 1 and minor <= 17:
            return 2566, 59*4
        else:  # 1.17 through 26.2 and counting
            return 2724, 62*4
    # --- 5. Fallback: assume modern palette ---
    return 2724, 62*4


def register_minecraft_map():
    """Hooks the Minecraft decoder module into Pillow's driver registry."""
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
        Image.register_save(MinecraftMapImageFile.format, _save,)
