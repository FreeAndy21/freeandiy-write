#!/usr/bin/env python3
# Modified-by: FreeANDIY (Free Andy Agency), 2026. Adapted from upstream PhotoCraft's
# packaging/macos/dmg/generate.py (MIT OR Apache-2.0, the PhotoCraft authors): the TIFF, alias and
# .DS_Store code is upstream's; the artwork is drawn here from the FreeANDIY brand instead of an SVG.
"""Write the macOS DMG window background and layout for this repository's FreeANDIY app.

    .venv/bin/pip install -r freeandiy/tools/requirements.txt
    .venv/bin/python -I freeandiy/tools/make_dmg.py

Outputs freeandiy/assets/dmg/{background.tiff, dmg-layout.DS_Store}; the rebrand copies them to
packaging/macos/dmg/. Both are reproducible: no local paths, user or disk names, dates or UUIDs.
"""

import datetime
import os
import sys
import tomllib
from pathlib import Path

from ds_store import DSStore
from mac_alias import Alias, TargetInfo, VolumeInfo
from PIL import Image, ImageCms, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_icons  # noqa: E402  (angel masks, colours)

ROOT = Path(__file__).resolve().parents[1]  # freeandiy/
OUT = ROOT / "assets" / "dmg"
CFG = tomllib.loads((ROOT / "branding.toml").read_text())
CFG.update(tomllib.loads((ROOT / "app.toml").read_text()))
APP = CFG["apps"][CFG["app"]]

# Keep in sync with packaging/macos/package.sh (volume name = the app name).
VOLUME = APP["name"]
WIDTH, HEIGHT = 660, 400  # window content, pt; the background's 1x size
TITLE_BAR = 32
ICON_SIZE = 128
PALETTE = 16  # colours in background.tiff
ICONS = {f"{APP['name']}.app": (326, 205), "Applications": (574, 205)}
FIXED_DATE = datetime.datetime(2026, 10, 8, tzinfo=datetime.timezone.utc)
PANEL = 232  # width of the coloured panel on the left


def draw(app, colors, scale):
    """The background at `scale`: paper, the app-colour panel with the angel, title, arrow."""
    s = scale
    W, H = WIDTH * s, HEIGHT * s
    paper, black = make_icons.rgba(colors["paper"]), make_icons.rgba(colors["black"])
    img = Image.new("RGBA", (W, H), paper)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, PANEL * s, H], fill=make_icons.rgba(app["color"]))
    size = 330 * s
    ink, body = make_icons.angel_masks(size, 9)
    panel = Image.new("RGBA", (PANEL * s, H), (0, 0, 0, 0))
    panel.paste(Image.new("RGBA", (size, size), paper), (-25 * s, 60 * s), body)
    panel.paste(Image.new("RGBA", (size, size), black), (-25 * s, 60 * s), ink)
    img.alpha_composite(panel)
    d.line([PANEL * s, 0, PANEL * s, H], fill=black, width=max(1, round(1.2 * s)))
    mono = lambda px, w="SemiBold": make_icons.font(px * s, w)
    d.text((267 * s, 46 * s), app["name"], font=mono(26), fill=black)
    d.line([267 * s, 88 * s, 624 * s, 88 * s], fill=black, width=s)
    d.line([267 * s, 335 * s, 624 * s, 335 * s], fill=black, width=s)
    d.text((267 * s, 348 * s), "Drag the app to Applications to install it.", font=mono(12, "Regular"), fill=black)
    # Arrow between the two icon boxes (they stay clear: 10 pt around each 128 pt box).
    y = 205 * s
    d.line([410 * s, y, 478 * s, y], fill=black, width=3 * s)
    d.polygon([(478 * s, y - 9 * s), (494 * s, y), (478 * s, y + 9 * s)], fill=black)
    return img.convert("RGB")


def quantize(im):
    # No dithering: dither noise compresses badly and the artwork has flat fills.
    return im.quantize(PALETTE, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


def srgb_profile():
    # LittleCMS's built-in sRGB ("No copyright, use freely"), with its creation date fixed.
    icc = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    d = FIXED_DATE
    icc[24:36] = b"".join(v.to_bytes(2, "big") for v in (d.year, d.month, d.day, 0, 0, 0))
    if icc[84:100] != bytes(16):
        sys.exit("error: the sRGB profile has an ID; recompute it after fixing the date")
    return bytes(icc)


def write_tiff(app, colors, out):
    """1x (72 dpi) and 2x (144 dpi) in one TIFF, as `tiffutil -cathidpicheck` writes them."""
    one, two = (quantize(draw(app, colors, s)) for s in (1, 2))
    two.encoderinfo = {"dpi": (144, 144)}  # the rest as the first page
    # Opaque 16-colour palette, Deflate: the artwork is three inks plus antialiasing, and a palette
    # keeps the file under ~90 KB (RGB was ~200 KB; repository assets must stay small).
    one.save(
        out,
        "TIFF",
        save_all=True,
        append_images=[two],
        compression="tiff_adobe_deflate",  # brand-ok: Pillow's name for TIFF compression 8 (Deflate)
        dpi=(72, 72),
        icc_profile=srgb_profile(),
    )
    with Image.open(out) as im:
        im.seek(1)
        if im.info.get("dpi") != (144, 144):
            sys.exit("error: the 2x page isn't 144 dpi (needs Pillow 12 or later)")
        strips = []
        for page in (0, 1):
            im.seek(page)
            strips += zip(im.tag_v2[273], im.tag_v2[279])  # StripOffsets, StripByteCounts
    # TIFF keeps directories and tag data on even offsets. When a strip ends on an odd one, libtiff
    # leaves the padding byte after it uninitialised, so the file changed from run to run with
    # identical pixels. Zero it: nothing refers to that byte.
    starts = {o for o, _ in strips}
    with open(out, "r+b") as f:
        for o, n in strips:
            if (o + n) % 2 and o + n not in starts:
                f.seek(o + n)
                f.write(bytes(1))


def background_alias():
    # What Finder stores for /.background/background.tiff on the volume, minus anything about the
    # machine (dmgbuild writes the same kind of alias from a mounted image). Disk type 5 (ejectable),
    # the volume flags and the folder/file ids (25, 26) are what Finder wrote on a test image; the ids
    # are only hints, as the volume's creation date.
    volume = VolumeInfo(VOLUME, FIXED_DATE, b"H+", 5, 0x0D02, b"\0\0")
    volume.posix_path = f"/Volumes/{VOLUME}"
    target = TargetInfo(0, "background.tiff", 25, 26, FIXED_DATE, b"\0\0\0\0", b"\0\0\0\0")
    target.folder_name = ".background"
    target.cnid_path = [25]
    target.carbon_path = f"{VOLUME}:.background:\0background.tiff"
    target.posix_path = "/.background/background.tiff"
    return Alias(volume=volume, target=target).to_bytes()


def write_ds_store(out):
    if os.path.exists(out):
        os.remove(out)
    with DSStore.open(out, "w+") as d:
        d["."]["bwsp"] = {
            "ShowStatusBar": False,
            "ShowToolbar": False,
            "ShowTabView": False,
            "ContainerShowSidebar": False,
            "ShowSidebar": False,
            "WindowBounds": f"{{{{200, 528}}, {{{WIDTH}, {HEIGHT + TITLE_BAR}}}}}",
        }
        d["."]["icvp"] = {
            "viewOptionsVersion": 1,
            "backgroundType": 2,
            "backgroundImageAlias": background_alias(),
            "backgroundColorRed": 1.0,
            "backgroundColorGreen": 1.0,
            "backgroundColorBlue": 1.0,
            "gridOffsetX": 0.0,
            "gridOffsetY": 0.0,
            "gridSpacing": 100.0,
            "arrangeBy": "none",
            "showIconPreview": True,
            "showItemInfo": False,
            "labelOnBottom": True,
            "textSize": 16.0,
            "iconSize": float(ICON_SIZE),
        }
        d["."]["vSrn"] = ("long", 1)
        for name, pos in ICONS.items():
            d[name]["Iloc"] = pos


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    write_tiff(APP, CFG["colors"], str(OUT / "background.tiff"))
    write_ds_store(str(OUT / "dmg-layout.DS_Store"))
    print(f"wrote {OUT.relative_to(ROOT.parent)}/background.tiff, dmg-layout.DS_Store")


if __name__ == "__main__":
    main()
