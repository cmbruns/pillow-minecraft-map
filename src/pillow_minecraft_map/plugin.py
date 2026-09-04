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

# We use the first stone color (79,79,79) for all the invalid
# palette IDs so the PIL ditherer will give the best possible result.
# This is the lowest ID for a uniform gray that is shared among all
# historical palettes.
# At save time, we will readjust the palette entries.
OPAQUE_FILLER_COLOR = (79, 79, 79)
OPAQUE_FILLER_ID = 44

# Version 1.17 is valid from Minecraft version 1.17 onward at least to 26.2
# and is a superset of palettes going back to version 1.7.
# Transparent entries are replaced with stone color 0x4F4F4F as part
# of a trick for handling both dithering and transparency.
JE_1_17_PALETTE = [
    # dark    normal    bright    darkest/unused
    # ------  --------  --------  --------
    0x4F4F4F, 0x4F4F4F, 0x4F4F4F, 0x4F4F4F,  # Air / Transparent  ID 0->3
    0x597D27, 0x6D9930, 0x7FB238, 0x435E1D,  # Grass  ID 4->7
    0xAEA473, 0xD5C98C, 0xF7E9A3, 0x827B56,  # Sand  ID 8->11
    0x8C8C8C, 0xABABAB, 0xC7C7C7, 0x696969,  # Cloth / White Wool  ID 12->15
    0xB40000, 0xDC0000, 0xFF0000, 0x870000,  # TNT / Fire / Lava  ID 16->19
    0x7070B4, 0x8A8ADC, 0xA0A0FF, 0x545487,  # Ice  ID 20->23
    0x757575, 0x909090, 0xA7A7A7, 0x585858,  # Iron / Metal  ID 24->27
    0x005700, 0x006A00, 0x007C00, 0x004100,  # Foliage / Plant  ID 28->31
    0xB4B4B4, 0xDCDCDC, 0xFFFFFF, 0x878787,  # Snow  ID 32->35
    0x737681, 0x8D909E, 0xA4A8B8, 0x565861,  # Clay  ID 36->39
    0x6A4C36, 0x825E42, 0x976D4D, 0x4F3928,  # Dirt  ID 40->43
    0x4F4F4F, 0x606060, 0x707070, 0x3B3B3B,  # Stone  ID 44->47
    0x2D2DB4, 0x3737DC, 0x4040FF, 0x212187,  # Water  ID 48->51
    0x645432, 0x7B663E, 0x8F7748, 0x4B3F26,  # Wood  ID 52->55
    0xB4B1AC, 0xDCD9D3, 0xFFFCF5, 0x878581,  # Quartz  ID 56->59
    0x985924, 0xBA6D2C, 0xD87F33, 0x72431B,  # Orange Wool  ID 60->63
    0x7D3598, 0x9941BA, 0xB24CD8, 0x5E2872,  # Magenta Wool  ID 64->67
    0x486C98, 0x5884BA, 0x6699D8, 0x365172,  # Light Blue Wool  ID 68->71
    0xA1A124, 0xC5C52C, 0xE5E533, 0x79791B,  # Yellow Wool  ID 72->75
    0x599011, 0x6DB015, 0x7FCC19, 0x436C0D,  # Lime Wool  ID 76->79
    0xAA5974, 0xD06D8E, 0xF27FA5, 0x804357,  # Pink Wool  ID 80->83
    0x353535, 0x414141, 0x4C4C4C, 0x282828,  # Gray Wool  ID 84->87
    0x6C6C6C, 0x848484, 0x999999, 0x515151,  # Light Gray Wool  ID 88->91
    0x35596C, 0x416D84, 0x4C7F99, 0x284351,  # Cyan Wool  ID 92->95
    0x592C7D, 0x6D3699, 0x7F3FB2, 0x43215E,  # Purple Wool  ID 96->99
    0x24357D, 0x2C4199, 0x334CB2, 0x1B285E,  # Blue Wool  ID 100->103
    0x483524, 0x58412C, 0x664C33, 0x36281B,  # Brown Wool  ID 104->107
    0x485924, 0x586D2C, 0x667F33, 0x36431B,  # Green Wool  ID 108->111
    0x6C2424, 0x842C2C, 0x993333, 0x511B1B,  # Red Wool  ID 112->115
    0x111111, 0x151515, 0x191919, 0x0D0D0D,  # Black Wool  ID 116->119
    0xB0A836, 0xD7CD42, 0xFAEE4D, 0x847E28,  # Gold  ID 120->123
    0x409A96, 0x4FBCB7, 0x5CDBD5, 0x307370,  # Diamond  ID 124->127
    0x345AB4, 0x3F6EDC, 0x4A80FF, 0x274387,  # Lapis  ID 128->131
    0x009928, 0x00BB32, 0x00D93A, 0x00721E,  # Emerald  ID 132->135
    0x5B3C22, 0x6F4A2A, 0x815631, 0x442D19,  # Podzol  ID 136->139
    0x4F0100, 0x600100, 0x700200, 0x3B0100,  # Netherrack  ID 140->143
    0x937C71, 0xB4988A, 0xD1B1A1, 0x6E5D55,  # White Terracotta  ID 144->147
    0x703919, 0x89461F, 0x9F5224, 0x542B13,  # Orange Terracotta  ID 148->151
    0x693D4C, 0x804B5D, 0x95576C, 0x4E2E39,  # Magenta Terracotta  ID 152->155
    0x4F4C61, 0x605D77, 0x706C8A, 0x3B3949,  # Light Blue Terracotta  ID 156->159
    0x835D19, 0xA0721F, 0xBA8524, 0x624613,  # Yellow Terracotta  ID 160->163
    0x485225, 0x58642D, 0x677535, 0x363D1C,  # Lime Terracotta  ID 164->167
    0x703637, 0x8A4243, 0xA04D4E, 0x542829,  # Pink Terracotta  ID 168->171
    0x281C18, 0x31231E, 0x392923, 0x1E1512,  # Gray Terracotta  ID 172->175
    0x5F4B45, 0x745C54, 0x876B62, 0x473833,  # Light Gray Terracotta  ID 176->179
    0x3D4040, 0x4B4F4F, 0x575C5C, 0x2E3030,  # Cyan Terracotta  ID 180->183
    0x56333E, 0x693E4B, 0x7A4958, 0x40262E,  # Purple Terracotta  ID 184->187
    0x352B40, 0x41354F, 0x4C3E5C, 0x282030,  # Blue Terracotta  ID 188->191
    0x352318, 0x412B1E, 0x4C3223, 0x281A12,  # Brown Terracotta  ID 192->195
    0x35391D, 0x414624, 0x4C522A, 0x282B16,  # Green Terracotta  ID 196->199
    0x642A20, 0x7A3327, 0x8E3C2E, 0x4B1F18,  # Red Terracotta  ID 200->203
    0x1A0F0B, 0x1F120D, 0x251610, 0x130B08,  # Black Terracotta  ID 204->207
    0x852122, 0xA3292A, 0xBD3031, 0x641919,  # Crimson Nylium  ID 208->211
    0x682C44, 0x7F3653, 0x943F61, 0x4E2133,  # Crimson Stem  ID 212->215
    0x401114, 0x4F1519, 0x5C191D, 0x300D0F,  # Crimson Hyphae  ID 216->219
    0x0F585E, 0x126C73, 0x167E86, 0x0B4246,  # Warped Nylium  ID 220->223
    0x286462, 0x327A78, 0x3A8E8C, 0x1E4B4A,  # Warped Stem  ID 224->227
    0x3C1F2B, 0x4A2535, 0x562C3E, 0x2D1720,  # Warped Hyphae  ID 228->231
    0x0E7F5D, 0x119B72, 0x14B485, 0x0A5F46,  # Warped Wart Block  ID 232->235
    0x464646, 0x565656, 0x646464, 0x343434,  # Deepslate  ID 236->239
    0x987B67, 0xBA967E, 0xD8AF93, 0x725C4D,  # Raw Iron  ID 240->243
    0x597569, 0x6D9081, 0x7FA796, 0x43584F,  # Glow Lichen  ID 244->247
]

# The early 56-entry palettes have some slightly different colors
# in Minecraft versions from Beta1.6 through (release) 1.0 to 1.6.4
# Transparent entries are replaced with stone color 0x4F4F4F as part
# of a trick for handling both dithering and transparency.
JE_BETA1_6_PALETTE = [
    # dark    normal    bright    darkest/unused
    # ------  --------  --------  --------
    0x4F4F4F, 0x4F4F4F, 0x4F4F4F, 0x4F4F4F,   # Air / Transparent  ID 0->3
    0x597D27, 0x6D9930, 0x7FB238, 0x6D9930,   # Grass  ID 4->7
    0xAEA473, 0xD5C98C, 0xF7E9A3, 0xD5C98C,   # Sand  ID 8->11
    0x757575, 0x909090, 0xA7A7A7, 0x909090,   # Cloth / White Wool  ID 12->15
    0xB40000, 0xDC0000, 0xFF0000, 0xDC0000,   # TNT / Fire / Lava  ID 16->19
    0x7070B4, 0x8A8ADC, 0xA0A0FF, 0x8A8ADC,   # Ice  ID 20->23
    0x757575, 0x909090, 0xA7A7A7, 0x909090,   # Iron / Metal  ID 24->27
    0x005700, 0x006A00, 0x007C00, 0x006A00,   # Foliage / Plant  ID 28->31
    0xB4B4B4, 0xDCDCDC, 0xFFFFFF, 0xDCDCDC,   # Snow  ID 32->35
    0x737681, 0x8D909E, 0xA4A8B8, 0x8D909E,   # Clay  ID 36->39
    0x814A21, 0x9D5B28, 0xB76A2F, 0x9D5B28,   # Dirt  ID 40->43
    0x4F4F4F, 0x606060, 0x707070, 0x606060,   # Stone  ID 44->47
    0x2D2DB4, 0x3737DC, 0x4040FF, 0x3737DC,   # Water  ID 48->51
    0x493A23, 0x59472B, 0x685332, 0x59472B,   # Wood  ID 52->55
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
        flat_palette = [color for rgb in raw_palette for color in rgb_from_int(rgb)]
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
    if palette_size == 56:  # Oldest palettes had some slightly different colors
        raw_palette = JE_BETA1_6_PALETTE
    else:
        raw_palette = JE_1_17_PALETTE[: palette_size]
    # Flatten the list of RGB tuples into a 1D sequence of integers
    flat_palette = [color for rgb in raw_palette for color in rgb_from_int(rgb)]
    padded_palette = flat_palette + [OPAQUE_FILLER_COLOR[0]] * (768 - len(flat_palette))

    # Construct an anchor reference image containing our strict 1.20 palette layout
    palette_anchor = Image.new("P", (1, 1))
    palette_anchor.putpalette(padded_palette)

    # Quantize the input image down to the closest matching palette colors using Floyd-Steinberg dithering
    quantized_im = im.convert("RGB").quantize(palette=palette_anchor, dither=Image.Dither.FLOYDSTEINBERG)
    pixel_bytes = bytearray(quantized_im.tobytes())

    # Replace invalid palette values with OPAQUE_FILLER_COLOR
    # BEFORE inserting the truly transparent values
    for idx in range(16384):
        pid = pixel_bytes[idx]
        if pid < 4 or pid >= len(flat_palette):
            # This is the color PIL thought was at this index
            pixel_bytes[idx] = OPAQUE_FILLER_ID

    # 4. OVERLAY TRANSPARENCY BACK TO INDEX 0 IF APPLICABLE
    if alpha_mask is not None:
        transparent_bytes = alpha_mask.tobytes()
        for idx in range(16384):
            if transparent_bytes[idx] == 255:
                pixel_bytes[idx] = 0  # Reassign value to ID 0 (Air/Transparent)

    # 5. RETRIEVE METADATA VARIANTS OR APPLY IN-GAME DEFAULTS
    x_center = im.info.get("x_center", 20000)
    z_center = im.info.get("z_center", 20000)
    data_version = im.info.get("data_version", data_version)  # Default to standard 1.20+

    # 6. ASSEMBLE RAW BINARY NBT ARCHITECTURE CHUNKS
    nbt_payload = bytearray()

    # Root TAG_Compound
    nbt_payload.append(0x0a)
    nbt_payload.extend(_encode_nbt_string(""))

    # DataVersion Tag (TAG_Int)
    # Not required in 26.2
    # Not required in 1.17
    # Not required in 1.15
    # nbt_payload.append(0x03)
    # nbt_payload.extend(_encode_nbt_string("DataVersion"))
    # nbt_payload.extend(data_version.to_bytes(4, "big", signed=True))

    # data TAG_Compound container entry point
    nbt_payload.append(0x0a)
    nbt_payload.extend(_encode_nbt_string("data"))

    # width (TAG_Short = 0x02)
    # required for 1.12
    nbt_payload.append(0x02)
    nbt_payload.extend(_encode_nbt_string("width"))
    nbt_payload.extend((128).to_bytes(2, "big", signed=True))

    # height (TAG_Short = 0x02)
    nbt_payload.append(0x02)
    nbt_payload.extend(_encode_nbt_string("height"))
    nbt_payload.extend((128).to_bytes(2, "big", signed=True))

    # xCenter
    nbt_payload.append(0x03)
    nbt_payload.extend(_encode_nbt_string("xCenter"))
    nbt_payload.extend(x_center.to_bytes(4, "big", signed=True))

    # zCenter
    nbt_payload.append(0x03)
    nbt_payload.extend(_encode_nbt_string("zCenter"))
    nbt_payload.extend(z_center.to_bytes(4, "big", signed=True))

    for tag_name, val in [
        ("trackingPosition", 0),
        ("unlimitedTracking", 0),
        ("locked", 1),
    ]:
        nbt_payload.append(0x01)
        nbt_payload.extend(_encode_nbt_string(tag_name))
        nbt_payload.append(val)

    # dimension
    # Not required in 26.2
    # Required in 1.17
    # Byte not string in 1.15 and earlier
    if data_version > 2500:  # 1.16+, Uses string dimension
        nbt_payload.append(0x08)  # TAG_String
        nbt_payload.extend(_encode_nbt_string("dimension"))
        nbt_payload.extend(_encode_nbt_string("minecraft:overworld"))

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
    # DataVersions did not exist before 1.9
    if v.isdigit():
        dv = int(v)
        if dv < 1:
            return dv, 14*4  # Palette A, err on the side of caution
        elif dv < 1000:  # pre 1.12
            return dv, 36*4  # Palette B
        elif dv < 2500:  # pre 1.16
            return dv, 52*4  # Palette C
        elif dv < 2700:  # pre 1.17
            return dv, 59 * 4  # Palette D
        else:  # post 1.17
            return dv, 62*4  # Palette E

    # --- 3. Handle beta versions ---
    if v.startswith("beta") or v.startswith("b"):
        return 0, 14*4  # Palette A

    # --- 4. Extract numeric version components ---
    # Examples: "1.12.2", "1.17", "26.2"
    m = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", v)
    if m:
        major = int(m.group(1))
        minor = int(m.group(2) or 0)
        _patch = int(m.group(3) or 0)

        if major < 1 or (major == 1 and minor <= 6):
            return 0, 14*4  # Palette A
        elif major == 1 and minor <= 12:
            return 99, 36*4  # Palette B
        elif major == 1 and minor <= 16:
            return 1139, 52*4  # Palette C
        elif major == 1 and minor <= 17:
            return 2566, 59*4  # Palette D
        else:  # 1.17 through 26.2 and counting
            return 2724, 62*4  # Palette E
    # --- 5. Fallback: assume palette E ---
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


def rgb_from_int(val: int = 0xFFFFFF) -> tuple[int, int, int]:
    return (
        (val >> 16) & 0xFF,  # R
        (val >> 8) & 0xFF,  # G
        val & 0xFF  # B
    )