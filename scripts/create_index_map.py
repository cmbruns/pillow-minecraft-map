import gzip

# Load a real Minecraft map info data into memory
template_file_name = r"C:\Users\cmbruns\AppData\Roaming\.minecraft\saves\Creative1_16_2\data\map_0.dat"
with gzip.open(template_file_name, mode="rb") as gz:
    bytes_blob = bytearray(gz.read())
p_col = bytes_blob.index(b'colors') + len(b'colors') + 4
s_col = int.from_bytes(bytes_blob[p_col - 4: p_col], byteorder="big")
assert 128 * 128 == s_col
palette_bytes = bytes_blob[p_col:p_col + s_col]
assert 128 * 128 == len(palette_bytes)

# Create a synthetic index map with 16x16 8x8 squares of the same palette value
index_bytes = b''
pv = 0
max_pv = 236
for stripe in range(16):  # 16 128x8 stripes of 16 colors
    row = b''
    for block in range(16):  # 16 colors in a scan line with 8 pixels each
        row += bytes([pv]) * 8  # 8 pixels of one color
        pv += 1  # march to the next palette color index
        if pv >= max_pv:
            break
    row += b'\0' * (128 - len(row))
    assert 128 == len(row)
    index_bytes += row * 8  # duplicate the scan line 8 times to form the stripe
    if pv >= max_pv:
        break  # Just one stripe for testing
# assert pv == 256  # All possible palette values are accounted for
index_bytes += b'\0' * (128*128 - len(index_bytes))  # pad with zeros if partial  index
assert 128*128 == len(index_bytes)

# Copy the synthetic index map data into the template map
lb = len(bytes_blob)
bytes_blob[p_col: p_col + s_col] = index_bytes
assert len(bytes_blob) == lb

# Replace xCenter with a large value so the map is not "right here"
p_xc = bytes_blob.index(b'xCenter') + len(b'xCenter')
x_center = int.from_bytes(bytes_blob[p_xc: p_xc + 4], byteorder="big")
print("Old xCenter:", x_center)
new_x_center = -5000  # or any large int
bytes_blob[p_xc:p_xc + 4] = new_x_center.to_bytes(4, byteorder="big", signed=True)

# Write out 6000.dat next to the input file
output_file_name = template_file_name
with gzip.open(output_file_name, mode="wb") as gz:
    gz.write(bytes_blob)

print("Wrote", output_file_name)
