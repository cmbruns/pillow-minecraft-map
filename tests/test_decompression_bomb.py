import gzip
import io


def make_gzip_bomb():
    # 10 MB of zeros compressed extremely well
    data = b"\x00" * 10_000_000
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(data)
    return buf.getvalue()


def test_detects_decompression_bomb():
    bomb = make_gzip_bomb()
    stream = gzip.GzipFile(fileobj=io.BytesIO(bomb), mode="rb")

    MAX = 1_000_000  # 1 MB safety limit
    total = 0

    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX:
                raise ValueError("Decompression bomb detected")
    except ValueError:
        return  # success

    assert False, "Bomb was not detected"
