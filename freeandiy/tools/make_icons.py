#!/usr/bin/env python3
# Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
"""Generate the FreeANDIY app icon set (variant C: the angel Andy on the app colour).

    python3 -m venv .venv && .venv/bin/pip install -r freeandiy/tools/requirements.txt
    cargo install vtracer                                          # SVG traces
    .venv/bin/python -I freeandiy/tools/make_icons.py [app ...|all]   # default: this repo's app

Reads freeandiy/branding.toml and writes freeandiy/assets/icons/<app>/:
  master-1024.png      full-bleed square (Windows, Linux, web)
  macos-1024.png       the same on Apple's 824/1024 grid with rounded corners
  mark-128.png         the monogram for the in-app title bar mark
  <app>.icns           macOS bundle icon (needs iconutil, macOS only)
  <app>.ico            Windows icon, 16-256 px
  hicolor/<s>.png      16-512 px; 32 px and below use the lowercase monogram, the angel
                       is unreadable that small
  <app>.svg            vector trace of the master (vtracer)
  favicon.svg          vector trace of the 32 px monogram
The outputs are committed; packaging never runs this script.
"""
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]  # freeandiy/
ASSETS = ROOT / "assets"
S = 1024
HICOLOR = (16, 24, 32, 48, 64, 128, 256, 512)
ICO = (16, 24, 32, 48, 64, 128, 256)
SMALL = 32  # at or below: monogram


def rgba(hex_):
    h = hex_.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4)) + (255,)


def font(px, weight="Bold"):
    return ImageFont.truetype(str(ASSETS / "fonts" / f"IBMPlexMono-{weight}.ttf"), px)


def angel_masks(size, thicken):
    """(ink, body) masks of the angel scaled to `size`: strokes thickened, body = enclosed area."""
    src = Image.open(ASSETS / "brand" / "fa-angel-left.png").convert("RGBA")
    dark = src.convert("L").point(lambda v: 255 if v < 128 else 0)
    ink = ImageChops.multiply(src.getchannel("A"), dark).filter(ImageFilter.MaxFilter(thicken))
    ink = ink.resize((size, size), Image.LANCZOS).point(lambda v: 255 if v > 100 else 0)
    closed = ink.filter(ImageFilter.MaxFilter(7))  # close small gaps before the flood fill
    canvas = Image.new("L", (size + 2, size + 2), 0)
    canvas.paste(closed, (1, 1))
    ImageDraw.floodfill(canvas, (0, 0), 128)
    outside = canvas.crop((1, 1, size + 1, size + 1)).point(lambda v: 255 if v == 128 else 0)
    return ink, ImageChops.invert(outside)


def master(app, colors):
    """1024 px full-bleed tile: angel bleeding off the right/bottom edge, monogram bottom left."""
    field, black, paper = rgba(app["color"]), rgba(colors["black"]), rgba(colors["paper"])
    label = paper if app["label"] == "paper" else black
    dark_field = app["color"].upper() == colors["black"].upper()
    img = Image.new("RGBA", (S, S), field)
    size, (ox, oy) = 1080, (250, 30)
    ink, body = angel_masks(size, 13)
    # On the black launcher tile the angel is drawn in paper line work instead.
    img.paste(Image.new("RGBA", (size, size), black if dark_field else paper), (ox, oy), body)
    img.paste(Image.new("RGBA", (size, size), paper if dark_field else black), (ox, oy), ink)
    d = ImageDraw.Draw(img)
    f = font(250)
    bb = d.textbbox((0, 0), app["monogram"], font=f)
    d.text((60 - bb[0], S - 60 - bb[3]), app["monogram"], font=f, fill=label)
    return img


def monogram(app, colors, px):
    """Small-size icon: the lowercase monogram on the app colour (lowercase keeps it clear of
    the two-letter capital tiles other vendors use)."""
    field = rgba(app["color"])
    label = rgba(colors["paper"]) if app["label"] == "paper" else rgba(colors["black"])
    big = 256  # draw large, then downsample for clean anti-aliasing
    img = Image.new("RGBA", (big, big), field)
    d = ImageDraw.Draw(img)
    text = app["monogram"].lower()
    f = font(150)
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((big - (bb[2] - bb[0])) / 2 - bb[0], (big - (bb[3] - bb[1])) / 2 - bb[1] - 6), text, font=f, fill=label)
    return img.resize((px, px), Image.LANCZOS)


def at(app, colors, m, px):
    return monogram(app, colors, px) if px <= SMALL else m.resize((px, px), Image.LANCZOS)


def macos(tile):
    """Apple's icon grid: an 824 px body centred on 1024, corner radius ~22.4% of the body."""
    body, r = 824, 185
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (body * 4, body * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body * 4 - 1, body * 4 - 1], radius=r * 4, fill=255)
    mask = mask.resize((body, body), Image.LANCZOS)
    out.paste(tile.resize((body, body), Image.LANCZOS), ((S - body) // 2, (S - body) // 2), mask)
    return out


def icns(app, colors, m, dest):
    if not shutil.which("iconutil"):
        print("  iconutil not found (macOS only): skipping .icns")
        return
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()
        for base in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                px = base * scale
                img = macos(m).resize((px, px), Image.LANCZOS) if px > SMALL else macos(monogram(app, colors, 256)).resize((px, px), Image.LANCZOS)
                name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
                img.save(iconset / name)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(dest)], check=True)


def trace(png, svg):
    """Vectorise with the vtracer CLI (`cargo install vtracer`, MIT; its Python wheel crashes on 3.14)."""
    exe = shutil.which("vtracer")
    if not exe:
        print("  vtracer not found (cargo install vtracer): skipping", svg.name)
        return
    subprocess.run([exe, "--input", str(png), "--output", str(svg), "--colormode", "color", "--hierarchical", "stacked",
                    "--mode", "spline", "--filter_speckle", "4", "--color_precision", "6", "--gradient_step", "16",
                    "--corner_threshold", "60", "--segment_length", "4", "--splice_threshold", "45",
                    "--path_precision", "2"], check=True, stdout=subprocess.DEVNULL)


def build(key, app, colors):
    out = ASSETS / "icons" / key
    if out.exists():
        shutil.rmtree(out)
    (out / "hicolor").mkdir(parents=True)
    m = master(app, colors)
    m.save(out / "master-1024.png", optimize=True)
    macos(m).save(out / "macos-1024.png", optimize=True)
    # In-app mark (title bar, ~20 pt): the monogram, at 128 px for HiDPI.
    monogram(app, colors, 128).save(out / "mark-128.png", optimize=True)
    for px in HICOLOR:
        at(app, colors, m, px).save(out / "hicolor" / f"{px}.png", optimize=True)
    imgs = [at(app, colors, m, px) for px in ICO]
    imgs[-1].save(out / f"{key}.ico", sizes=[(p, p) for p in ICO], append_images=imgs[:-1])
    icns(app, colors, m, out / f"{key}.icns")
    trace(out / "master-1024.png", out / f"{key}.svg")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "fav.png"
        monogram(app, colors, 256).save(p)
        trace(p, out / "favicon.svg")
    print(f"  {key}: {out.relative_to(ROOT.parent)}")


def main():
    cfg = tomllib.loads((ROOT / "branding.toml").read_text())
    app_toml = ROOT / "app.toml"  # absent in the meta repository: name the app(s) or `all`
    if app_toml.exists():
        cfg.update(tomllib.loads(app_toml.read_text()))
    if not sys.argv[1:] and "app" not in cfg:
        sys.exit("usage: make_icons.py <app>... | all")
    keys = sys.argv[1:] or [cfg["app"]]
    if keys == ["all"]:
        keys = list(cfg["apps"])
    for k in keys:
        if k not in cfg["apps"]:
            sys.exit(f"unknown app {k!r}; known: {', '.join(cfg['apps'])}")
        build(k, cfg["apps"][k], cfg["colors"])


if __name__ == "__main__":
    main()
