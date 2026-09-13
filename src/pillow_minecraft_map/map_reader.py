"""
Incremental Map Loader to maybe avoid decompression bombs
"""

import enum
import logging
import struct
from typing import BinaryIO, Iterator

import zlib
from PIL import UnidentifiedImageError

logger = logging.getLogger("PIL.MinecraftMapPlugin")


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


PayloadType = int | float | str | bytearray | list | dict


class MapReader:
    def __init__(
            self,
            compressed_stream: BinaryIO,
            max_length: int = 1024 * 1024,  # Data size limit
            max_depth: int = 30,  # Data tree recursion depth limit
    ) -> None:
        self.compressed_stream: BinaryIO = compressed_stream
        self.max_length: int = max_length
        self.max_depth: int = max_depth
        # 16 + MAX_WBITS tells zlib to expect a gzip wrapper
        self.inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
        self.decompressed: bytearray = bytearray(b'')
        self.cursor: int = 0
        self.map_data = dict()
        try:
            self.read_root_tag()
        except zlib.error as exc:
            raise UnidentifiedImageError from exc
        self.read_top_tags()
        if "colors" not in self.map_data:
            raise UnidentifiedImageError("'colors' Minecraft map NBT tag not found")

    def inflate_to_byte(self, pos: int) -> None:
        """Continue decompressing to the nth byte of the decompressed stream"""
        while len(self.decompressed) < pos:
            chunk = self.compressed_stream.read(1024)
            if not chunk:
                raise ValueError("Unexpected end of file")
            self.decompressed += self.inflater.decompress(chunk, max_length=self.max_length)
            if len(self.decompressed) > self.max_length:
                raise ValueError(f"Decompression bomb detected: Exceeded maximum allowed size {self.max_length}")

    def read_root_tag(self) -> None:
        """Begin reading a freshly opened map file"""
        # Root tag - must be a container with name ""
        tag_type: NBTTagType = NBTTagType(self.read_u8())
        if tag_type != NBTTagType.Compound:
            raise UnidentifiedImageError  # Not a Minecraft map
        tag_name: str = self.read_string()
        if tag_name != "":
            raise UnidentifiedImageError  # Not a Minecraft map

    def read_top_tags(self) -> None:
        """Read the NBT tags directly under the root"""
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
                self.read_data_container(depth=1)
            else:
                raise UnidentifiedImageError

    def read_compound(self, depth) -> dict:
        out = {}
        for tag_type, name, payload in self.iter_compound(depth):
            out[name] = payload
        return out

    def read_data_container(self, depth: int) -> None:
        # Most map tags are in the "data" section
        for tag_type, tag_name, payload in self.iter_compound(depth):
            if tag_name not in [
                "banners",
                "colors",
                "dimension",
                "frames",
                "height",
                "locked",
                "scale",
                "trackingPosition",
                "unlimitedTracking",
                "UUIDLeast",
                "UUIDMost",
                "width",
                "xCenter",
                "zCenter",
            ]:
                # Not an error. "Be liberal with your inputs (and conservative with your outputs)"
                logger.warning(f"Unrecognized Minecraft map NBT tag 'data.{tag_name}'")
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

    def read_fixed_list(self, elem_type: NBTTagType, length: int, depth: int) -> list[PayloadType]:
        if length < 0:
            raise ValueError("Negative NBT list length")
        if length > 1_000_000:
            raise ValueError("NBT list too large")
        if depth > self.max_depth:
            raise ValueError(f"NBT nesting depth too deep ({depth})")
        out = []
        for _ in range(length):
            out.append(self.read_payload(elem_type, depth))
        return out

    def read_string(self) -> str:
        length = self.read_u16()
        if length > 1024:  # sanity limit
            raise ValueError("NBT string too long")
        return self.read_exact(length).decode("utf-8", "replace")

    def iter_compound(self, depth: int) -> Iterator[tuple[NBTTagType, str, PayloadType]]:
        if depth > self.max_depth:
            raise ValueError(f"NBT nesting depth too deep ({depth})")
        while True:
            tag_type: NBTTagType = NBTTagType(self.read_u8())
            if tag_type == NBTTagType.End:
                return
            name = self.read_string()
            yield tag_type, name, self.read_payload(tag_type, depth)

    def read_payload(
            self,
            tag_type: NBTTagType,
            depth: int,
    ) -> PayloadType:
        if tag_type == NBTTagType.End:
            raise ValueError("Unexpected NBT end tag")
        elif tag_type == NBTTagType.Byte:
            return self.read_exact(1)[0]
        elif tag_type == NBTTagType.Short:
            return struct.unpack(">h", self.read_exact(2))[0]
        elif tag_type == NBTTagType.Int:
            return self.read_i32()
        elif tag_type == NBTTagType.Long:
            return struct.unpack(">q", self.read_exact(8))[0]
        elif tag_type == NBTTagType.Float:
            return struct.unpack(">f", self.read_exact(4))[0]
        elif tag_type == NBTTagType.Double:
            return struct.unpack(">d", self.read_exact(8))[0]
        elif tag_type == NBTTagType.Byte_Array:
            length = self.read_i32()
            if length < 0 or length > 1_000_000:
                raise ValueError("Byte array length suspicious")
            return self.read_exact(length)
        elif tag_type == NBTTagType.String:
            return self.read_string()
        elif tag_type == NBTTagType.List:
            elem_type = NBTTagType(self.read_u8())
            length = self.read_i32()
            return self.read_fixed_list(elem_type, length, depth + 1)
        elif tag_type == NBTTagType.Compound:
            return self.read_compound(depth + 1)
        elif tag_type == NBTTagType.Int_Array:
            length = self.read_i32()
            return self.read_fixed_list(NBTTagType.Int, length, depth + 1)
        elif tag_type == NBTTagType.Long_Array:
            length = self.read_i32()
            return self.read_fixed_list(NBTTagType.Long, length, depth + 1)
        else:
            raise ValueError(f"Unknown NBT tag type: '{tag_type.name}'")
