import io
import os
import sys

from PIL import Image
import pillow_minecraft_map  # "unused" import loads the plugin as a side effect
import pytest


def create_mock_map(scale_value=3):
    """Generates a minimal valid Gzipped byte stream mimicking a map.dat file."""
    img = Image.new(mode="RGBA", size=(128, 128), color=(0, 0, 0, 0))
    stream = io.BytesIO()
    img.save(stream, format="MINECRAFT_MAP", version="26.2", scale=scale_value)
    stream.seek(0)
    return stream


def test_load_valid_minecraft_map():
    """Test that a valid map file opens with correct dimensions and metadata."""
    mock_file = create_mock_map(scale_value=2)
    folder = os.path.dirname(__file__)
    with Image.open(mock_file) as img:
        assert img.size == (128, 128)
        assert img.info.get("scale") == 2


if __name__ == "__main__":
    # Passing __file__ instructs pytest to specifically run this file.
    # sys.exit ensures the script exits with the correct status code for CI/CD pipelines.
    current_file = os.path.abspath(__file__)
    sys.exit(pytest.main([current_file]))
