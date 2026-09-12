"""
Incremental Map Loader to maybe avoid decompression bombs
"""

import enum
import glob
import os
import struct
from typing import BinaryIO

import zlib
from PIL import UnidentifiedImageError


class NBTTagType(enum.IntEnum):
    End = 0x0
    Byte = 0x1
    Short = 0x2
    Int = 0x3
    Long = 0x4
    Float = 0x5
    Double = 0x6
    Byte_Array = 0x7
    String = 0x8
    List = 0x9
    Compound = 0xA
    Int_Array = 0xB
    Long_Array = 0xC


class MapReader:
    def __init__(self, compressed_stream: BinaryIO, max_length=1024 * 1024) -> None:
        self.compressed_stream: BinaryIO = compressed_stream
        self.max_length: int = max_length
        # 16 + MAX_WBITS tells zlib to expect a gzip wrapper
        self.inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.decompressed: bytearray = bytearray(b'')
        self.cursor: int = 0
        self.map_data = dict()
        self.read_root_tag()
        self.read_top_tags()
        if "colors" not in self.map_data:
            raise UnidentifiedImageError("'colors' tag not found")

    def inflate_to_byte(self, pos: int) -> None:
        while len(self.decompressed) < pos:
            chunk = fp.read(1024)
            if not chunk:
                raise ValueError("Unexpected end of file")
            self.decompressed += self.inflater.decompress(chunk, max_length=self.max_length)
            if len(self.decompressed) > self.max_length:
                raise ValueError(f"Decompression bomb detected: Exceeded maximum allowed size {self.max_length}")

    def read_root_tag(self):
        # Root tag - must be a container with name ""
        tag_type: NBTTagType = NBTTagType(self.read_u8())
        if tag_type != NBTTagType.Compound:
            raise UnidentifiedImageError  # Not a Minecraft map
        tag_name: str = self.read_string()
        if tag_name != "":
            raise UnidentifiedImageError  # Not a Minecraft map

    def read_top_tags(self):
        # There are only two top level tags found in Minecraft maps:
        # "data" and "DataVersion"
        while True:
            tag_type = NBTTagType(self.read_u8())
            if tag_type == NBTTagType.End:
                return
            tag_name: str = self.read_string()
            if (tag_type, tag_name) == (NBTTagType.Int, "DataVersion"):
                self.map_data[tag_name] = self.read_i32()
            elif (tag_type, tag_name) == (NBTTagType.Compound, "data"):
                self.read_data_container()
            else:
                raise UnidentifiedImageError

    def read_data_container(self):
        # Most map tags are in the "data" section
        for tag_type, tag_name, payload in self.iter_compound():
            # TODO: is this too conservative?
            # we want to be liberal in our inputs, but quickly reject other
            # non-map NBT files like level.dat
            if tag_name not in [
                "banners",
                "colors",
                "dimension",
                "frames",
                "height",
                "scale",
                "trackingPosition",
                "unlimitedTracking",
                "width",
                "xCenter",
                "zCenter",
            ]:
                raise UnidentifiedImageError(f"Unrecognized NBT tag {tag_name}")
            self.map_data[tag_name] = payload

    def read_exact(self, n: int = 1) -> bytearray:
        """Read the next n bytes from the inflated stream"""
        self.inflate_to_byte(self.cursor + n)
        c0 = self.cursor
        self.cursor += n
        return self.decompressed[c0: self.cursor]

    def read_u8(self) -> int:
        return struct.unpack(">B", self.read_exact(1))[0]

    def read_u16(self) -> int:
        return struct.unpack(">H", self.read_exact(2))[0]

    def read_i32(self) -> int:
        return struct.unpack(">i", self.read_exact(4))[0]

    def read_string(self) -> str:
        length = self.read_u16()
        if length > 1024:  # sanity limit
            raise ValueError("NBT string too long")
        return self.read_exact(length).decode("utf-8", "replace")

    def iter_compound(self):
        while True:
            tag_type: NBTTagType = NBTTagType(self.read_u8())
            if tag_type == NBTTagType.End:
                return
            name = self.read_string()
            yield tag_type, name, self.read_payload(tag_type)

    def read_payload(self, tag_type: NBTTagType) -> int | str | bytearray:
        if tag_type == NBTTagType.Byte:
            return self.read_exact(1)[0]
        elif tag_type == NBTTagType.Short:
            return struct.unpack(">h", self.read_exact(2))[0]
        elif tag_type == NBTTagType.Int:
            return self.read_i32()
        elif tag_type == NBTTagType.String:
            return self.read_string()
        elif tag_type == NBTTagType.Byte_Array:
            length = self.read_i32()
            if length < 0 or length > 1_000_000:
                raise ValueError("Byte array length suspicious")
            return self.read_exact(length)
        # For now, skip complex types:
        elif tag_type in (
                NBTTagType.List,
                NBTTagType.Compound,
                NBTTagType.Int_Array,
                NBTTagType.Long_Array
        ):
            # Implement minimal skipping logic or bail
            raise ValueError(f"Unsupported NBT tag type in map {tag_type.name}")
        else:
            raise ValueError(f"Unknown NBT tag type: {tag_type.name}")


folder = os.path.abspath(os.path.dirname(__file__)) + "/images"
for file_name in glob.glob(os.path.join(folder, "*/*.dat")):
    print(file_name)
    with open(file_name, "rb") as fp:
        mr = MapReader(fp)
        print(mr.map_data)
