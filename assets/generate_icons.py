#!/usr/bin/env python3
"""
Generate platform icon files for YouTube Downloader.

The shared icon matches the approved visual direction used on Android:
a soft white rounded tile, a glossy red play panel, and a white download
arrow/tray. The artwork stays comfortably inside common platform icon masks.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "generated"


def rounded_mask(box: tuple[int, int, int, int], radius: int) -> Image.Image:
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(box, radius=radius, fill=255)
    return mask


def render_icon() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Soft outer shadow for the white app tile.
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((80, 92, 944, 956), radius=205, fill=(0, 0, 0, 105))
    shadow = shadow.filter(ImageFilter.GaussianBlur(38))
    canvas = Image.alpha_composite(canvas, shadow)

    # White/very-light-grey rounded tile.
    tile = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle((72, 68, 952, 948), radius=205, fill=(247, 248, 250, 255))
    td.rounded_rectangle((92, 86, 932, 926), radius=185, outline=(255, 255, 255, 255), width=12)
    canvas = Image.alpha_composite(canvas, tile)

    # Slight cool-grey depth near the bottom of the tile.
    depth = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(depth)
    dd.rounded_rectangle((100, 735, 924, 918), radius=150, fill=(198, 204, 212, 58))
    depth = depth.filter(ImageFilter.GaussianBlur(24))
    tile_mask = rounded_mask((72, 68, 952, 948), 205)
    clipped_depth = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    clipped_depth.paste(depth, (0, 0), tile_mask)
    canvas = Image.alpha_composite(canvas, clipped_depth)

    # Shadow under the red play panel.
    red_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rsd = ImageDraw.Draw(red_shadow)
    rsd.rounded_rectangle((176, 254, 846, 706), radius=118, fill=(0, 0, 0, 105))
    red_shadow = red_shadow.filter(ImageFilter.GaussianBlur(22))
    canvas = Image.alpha_composite(canvas, red_shadow)

    # Red play panel.
    red = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(red)
    rd.rounded_rectangle((164, 236, 834, 686), radius=118, fill=(244, 18, 31, 255))
    rd.rounded_rectangle((182, 252, 816, 360), radius=88, fill=(255, 255, 255, 35))
    rd.rounded_rectangle((164, 236, 834, 686), radius=118, outline=(211, 8, 19, 255), width=9)
    canvas = Image.alpha_composite(canvas, red)

    # Play symbol.
    fg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg)
    play = [(340, 356), (340, 590), (545, 473)]
    fd.polygon(play, fill=(255, 255, 255, 255))

    # Download arrow, kept mostly inside the red panel.
    arrow = [
        (625, 365),
        (704, 365),
        (704, 490),
        (768, 490),
        (665, 602),
        (562, 490),
        (625, 490),
    ]
    fd.polygon(arrow, fill=(255, 255, 255, 255))

    # Download tray. This sits inside the red panel to remain legible even at
    # small launcher sizes and under platform masks.
    fd.line(
        [(570, 618), (570, 638), (596, 664), (734, 664), (760, 638), (760, 618)],
        fill=(255, 255, 255, 255),
        width=34,
        joint="curve",
    )

    # Tiny soft shadow behind the white symbols for definition.
    symbol_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ssd = ImageDraw.Draw(symbol_shadow)
    ssd.polygon([(x + 7, y + 9) for x, y in play], fill=(0, 0, 0, 65))
    ssd.polygon([(x + 7, y + 9) for x, y in arrow], fill=(0, 0, 0, 65))
    symbol_shadow = symbol_shadow.filter(ImageFilter.GaussianBlur(11))
    canvas = Image.alpha_composite(canvas, symbol_shadow)
    canvas = Image.alpha_composite(canvas, fg)

    return canvas


def save_png(image: Image.Image) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "youtube_downloader.png"
    image.save(path, format="PNG", optimize=True)
    return path


def save_windows(image: Image.Image) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "youtube_downloader.ico"
    image.save(
        path,
        format="ICO",
        sizes=[
            (16, 16),
            (24, 24),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256),
        ],
    )
    return path


def save_macos(image: Image.Image) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "youtube_downloader.icns"
    image.save(path, format="ICNS")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--platform",
        choices=("windows", "macos", "all"),
        default="all",
    )
    args = parser.parse_args()

    image = render_icon()
    outputs = [save_png(image)]

    if args.platform in ("windows", "all"):
        outputs.append(save_windows(image))
    if args.platform in ("macos", "all"):
        outputs.append(save_macos(image))

    for path in outputs:
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
