#!/usr/bin/env python3
"""
Generate platform icon files for YouTube Downloader.

The icon deliberately keeps the play/download mark well inside the safe area
used by Android launchers and desktop icon masks. This avoids the clipped,
oversized look that can happen on Samsung and other adaptive-icon launchers.
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


def vertical_gradient(
    size: int,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
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
    # Premium dark tile. The outer corners stay transparent so each platform
    # can apply its native mask cleanly.
    base = vertical_gradient(SIZE, (28, 32, 40), (8, 10, 14))

    mask = Image.new("L", base.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((42, 42, 982, 982), radius=205, fill=255)

    canvas = Image.new("RGBA", base.size, (0, 0, 0, 0))
    canvas.paste(base, (0, 0), mask)

    # Subtle glow stays contained behind the red play surface.
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((260, 300, 790, 790), fill=(225, 25, 38, 55))
    glow = glow.filter(ImageFilter.GaussianBlur(85))
    canvas = Image.alpha_composite(canvas, glow)

    # Smaller, centred play surface with generous margin around the mark.
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (205, 300, 815, 715),
        radius=108,
        fill=(0, 0, 0, 135),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    canvas = Image.alpha_composite(canvas, shadow)

    red = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(red)
    rd.rounded_rectangle(
        (195, 280, 805, 695),
        radius=108,
        fill=(245, 29, 42, 255),
    )

    # Very restrained highlight so it remains crisp at small launcher sizes.
    rd.rounded_rectangle(
        (215, 298, 785, 405),
        radius=82,
        fill=(255, 78, 86, 48),
    )
    canvas = Image.alpha_composite(canvas, red)

    fg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg)

    # Play mark.
    fd.polygon(
        [(335, 385), (335, 590), (515, 487)],
        fill=(255, 255, 255, 255),
    )

    # Download arrow, entirely contained within the red panel.
    fd.polygon(
        [
            (615, 385),
            (690, 385),
            (690, 500),
            (750, 500),
            (652, 600),
            (554, 500),
            (615, 500),
        ],
        fill=(255, 255, 255, 255),
    )

    # Download tray, also kept within the panel so no platform mask clips it.
    fd.line(
        [
            (565, 625),
            (565, 645),
            (590, 670),
            (715, 670),
            (740, 645),
            (740, 625),
        ],
        fill=(255, 255, 255, 255),
        width=34,
        joint="curve",
    )

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
