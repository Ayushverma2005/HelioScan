from io import BytesIO
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image


# Maximum dimension of the browser preview.
# The original TIFF is NOT resized or modified.
MAX_PREVIEW_SIZE = 2048


def create_naip_preview(tiff_path: str | Path) -> BytesIO:
    """
    Convert a NAIP GeoTIFF into an RGB/RGBA PNG suitable for browser display.

    NAIP imagery may contain 4 bands:
        1 = Red
        2 = Green
        3 = Blue
        4 = Near Infrared

    Only RGB bands are used for the browser preview.

    The original GeoTIFF remains completely untouched.

    Preview processing:
        1. Read RGB bands.
        2. Read the raster validity mask.
        3. Apply robust percentile normalization.
        4. Remove obvious empty/invalid pixels.
        5. Convert to RGBA.
        6. Downsample large previews.
        7. Return PNG bytes.
    """

    tiff_path = Path(tiff_path)

    if not tiff_path.exists():
        raise FileNotFoundError(
            f"NAIP TIFF not found: {tiff_path}"
        )

    if not tiff_path.is_file():
        raise FileNotFoundError(
            f"NAIP TIFF path is not a file: {tiff_path}"
        )

    with rasterio.open(tiff_path) as src:

        if src.count < 3:
            raise ValueError(
                f"NAIP image must contain at least 3 bands; "
                f"found {src.count}"
            )

        # Read RGB bands.
        #
        # Shape:
        #   (3, height, width)
        rgb = src.read([1, 2, 3])

        # Rasterio's combined dataset validity mask.
        #
        # 255 = valid
        #   0 = invalid / nodata
        mask = src.dataset_mask()

    # ---------------------------------------------------------
    # Convert from:
    #
    #   (bands, height, width)
    #
    # to:
    #
    #   (height, width, bands)
    # ---------------------------------------------------------

    rgb = np.transpose(rgb, (1, 2, 0))

    # Work with floating point values during normalization.
    rgb_float = rgb.astype(np.float32)

    # ---------------------------------------------------------
    # Build validity mask
    # ---------------------------------------------------------

    valid_mask = mask > 0

    # Some imagery exports can contain completely empty pixels
    # that are not properly represented by the dataset mask.
    #
    # Treat pixels where all RGB channels are zero as invalid.
    empty_pixels = np.all(rgb_float <= 0, axis=2)

    valid_mask &= ~empty_pixels

    if not np.any(valid_mask):
        raise ValueError(
            "NAIP preview contains no valid RGB pixels."
        )

    # ---------------------------------------------------------
    # Robust contrast normalization
    # ---------------------------------------------------------
    #
    # Instead of simply clipping values to 0-255, calculate
    # useful lower/upper percentiles from valid pixels.
    #
    # This prevents a small number of extreme pixels from
    # making the entire preview appear washed out or dark.
    # ---------------------------------------------------------

    normalized = np.zeros_like(rgb_float, dtype=np.float32)

    for channel in range(3):

        channel_data = rgb_float[:, :, channel]

        valid_values = channel_data[valid_mask]

        # Robust bounds.
        low = float(np.percentile(valid_values, 2))
        high = float(np.percentile(valid_values, 98))

        # Avoid division by zero for completely flat channels.
        if high <= low:
            normalized[:, :, channel] = np.clip(
                channel_data,
                0,
                255,
            )
            continue

        normalized[:, :, channel] = (
            (channel_data - low)
            / (high - low)
            * 255.0
        )

    # Convert to uint8 RGB.
    rgb_uint8 = np.clip(
        normalized,
        0,
        255,
    ).astype(np.uint8)

    # ---------------------------------------------------------
    # Create RGBA
    # ---------------------------------------------------------

    rgba = np.dstack(
        (
            rgb_uint8,
            np.where(
                valid_mask,
                255,
                0,
            ).astype(np.uint8),
        )
    )

    image = Image.fromarray(
        rgba,
        mode="RGBA",
    )

    # ---------------------------------------------------------
    # Downsample large previews
    # ---------------------------------------------------------
    #
    # This affects ONLY the browser PNG.
    #
    # The original GeoTIFF remains full resolution on disk.
    # ---------------------------------------------------------

    width, height = image.size

    if max(width, height) > MAX_PREVIEW_SIZE:

        scale = MAX_PREVIEW_SIZE / max(width, height)

        new_width = max(
            1,
            round(width * scale),
        )

        new_height = max(
            1,
            round(height * scale),
        )

        image = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS,
        )

    # ---------------------------------------------------------
    # Encode PNG
    # ---------------------------------------------------------

    output = BytesIO()

    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output