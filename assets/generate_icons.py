#!/usr/bin/env python3
"""
Generate platform icon files for YouTube Downloader.

This renders the approved visual concept used by the project:
dark rounded app tile + red play surface + white play/download symbols.

Outputs are generated during packaging rather than committed as binary build
artifacts, keeping the source repository small and the platform icons consistent.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "generated"


def lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (size, size))
    pixels = image.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        color = (
            lerp(top[0], bottom[0], t),
            lerp(top[1], bottom[1], t),
            lerp(top[2], bottom[2], t),
            255,
        )
        for x in range(size):
            pixels[x, y] = color
    return image


def render_icon() -> Image.Image:
    canvas = vertical_gradient(SIZE, (26, 30, 38), (6, 8, 12))
    canvas = canvas.convert("RGBA")

    # Soft red glow behind the play surface.
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((170, 390, 890, 990), fill=(220, 20, 30, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(95))
    canvas = Image.alpha_composite(canvas, glow)

    # Dark outer rounded tile.
    mask = Image.new("L", canvas.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((28, 28, 996, 996), radius=190, fill=255)
    clipped = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    clipped.paste(canvas, (0, 0), mask)
    canvas = clipped

    # Red play-button shadow.
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((155, 240, 855, 735), radius=125, fill=(0, 0, 0, 165))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    canvas = Image.alpha_composite(canvas, shadow)

    # Main red surface.
    red = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(red)
    rd.rounded_rectangle((145, 215, 850, 710), radius=125, fill=(245, 18, 28, 255))
    rd.rounded_rectangle((165, 230, 830, 365), radius=105, fill=(255, 65, 71, 80))
    canvas = Image.alpha_composite(canvas, red)

    # Play triangle with a subtle shadow.
    triangle = [(380, 345), (380, 590), (595, 468)]
    tri_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    tsd = ImageDraw.Draw(tri_shadow)
    tsd.polygon([(x + 12, y + 16) for x, y in triangle], fill=(0, 0, 0, 115))
    tri_shadow = tri_shadow.filter(ImageFilter.GaussianBlur(18))
    canvas = Image.alpha_composite(canvas, tri_shadow)

    fg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg)
    fd.polygon(triangle, fill=(255, 255, 255, 255))

    # Download arrow.
    arrow = [
        (665, 490),
        (755, 490),
        (755, 590),
        (815, 590),
        (710, 705),
        (605, 590),
        (665, 590),
    ]
    fd.polygon(arrow, fill=(255, 255, 255, 255))

    # Download tray.
    tray_width = 45
    fd.line(
        [(585, 730), (585, 775), (620, 810), (805, 810), (840, 775), (840, 730)],
        fill=(255, 255, 255, 255),
        width=tray_width,
        joint="curve",
    )

    canvas = Image.alpha_composite(canvas, fg)

    # Keep the outer corners transparent so each OS can apply its own mask.
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
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
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
