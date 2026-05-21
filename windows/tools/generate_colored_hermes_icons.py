"""
Bouwt windows/hermes_logo.ico en gekleurde varianten uit assets/Hermes_logo.png.

- Start-app icoon (hermes_logo.ico): **originele kleuren**, één **256×256**-laag in de ICO (compatibel
  met Windows-snelkoppelingen; ICO-resource = **32bpp DIB + alpha** met volledige **AND-monomaan**
  (Pillow laat die weg → Shell toont soms een zwart vlak; we vullen die bytes na ``save`` aan).
  ``IconLocation`` = ``pad.ico,0``.
- Backup / restore / update: zelfde beeld, **felle kleur** via HSV (hue naar doelkleur).
- Standaard: **cirkelmasker** — alles buiten de ingeschreven cirkel is transparant (geen vierkante hoeken
  in taakbalk/desktop). Overslaan: ``--full-square``.
- **Bijna-zwart** binnen het canvas wordt zacht transparant gemaakt (typisch “logo op zwart vlak”),
  daarna wordt het zichtbare embleem **opgeschaald** naar ~``CONTENT_FILL`` van het vierkant (nu
  taakbalk-pariteit met veel vastgezette apps). Overslaan: ``--no-black-key``.
- Bij een PNG-bron (niet ``--full-square``): dezelfde pipeline wordt teruggeschreven naar die PNG
  (meestal ``assets/Hermes_logo.png``), zodat het bronbestand gelijk loopt met de iconen (max.
  ``WRITE_PIPELINE_MAX_SIDE`` px in de pipeline voor snelheid).

**Nog een donker vlak na opnieuw vastpinnen?** Meestal **Windows-icooncache** of een oude pin —
probeer pin verwijderen, opnieuw ``windows\\*naar taakbalk slepen*.lnk``, of opnieuw aanmelden.
Blijft het beeld zelf donker rond het embleem, tune dan ``LUM_KEY_LO`` / ``LUM_KEY_HI`` en de
drempels in ``_finalize_transparency_for_windows_ico`` (geen ICO-formaat nodig).

Vereiste: pip install pillow

Gebruik:
  python windows/tools/generate_colored_hermes_icons.py

Optioneel: expliciet PNG-pad
  python windows/tools/generate_colored_hermes_icons.py --png ..\\assets\\Hermes_logo.png

Vierkant canvas (geen cirkel; bron-PNG wordt niet met masker overschreven):
  python windows/tools/generate_colored_hermes_icons.py --full-square

Geen luminantie-key (logo met opzet veel zwart):
  python windows/tools/generate_colored_hermes_icons.py --no-black-key
"""
from __future__ import annotations

import argparse
import colorsys
import io
import shutil
import struct
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    print("Installeer Pillow: pip install pillow", file=sys.stderr)
    raise SystemExit(1) from e

# Felle doelkleuren (RGB) → hue voor HSV-recolor
VARIANTS: dict[str, tuple[int, int, int]] = {
    "hermes_logo_backup.ico": (255, 32, 140),
    "hermes_logo_restore.ico": (0, 210, 255),
    "hermes_logo_update.ico": (255, 160, 0),
    # Wit Hermes-monogram (update + setup-snelkoppelingen); zelfde pipeline als gekleurde varianten.
    "hermes_taskbar_white.ico": (248, 248, 252),
}

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
# Bron: max zijde na vierkant croppen (kleiner = sneller; 512 is scherp genoeg voor 256-ico)
MASTER_MAX_SIDE = 512
# PNG-rewrite: te grote vierkanten eerst verkleinen (key/expand is O(pixels))
WRITE_PIPELINE_MAX_SIDE = 1536
# Luminantie-key: donkerder vlak rond goud → transparant; smallere LUM_KEY_LO / hogere LUM_KEY_HI = agressiever.
LUM_KEY_LO = 6.0
LUM_KEY_HI = 74.0
# Na key: embleem vult max. dit deel van het canvas (taakbalk ≈ andere vastgezette apps).
CONTENT_FILL = 0.99
# Voor bbox/opschalen: alleen pixels met alpha > drempel = “inhoud”; hoger = strakkere bbox = groter opgezoomd.
BBOX_ALPHA_FLOOR = 62


def _normalize_ico_bytes(raw: bytes) -> bytes:
    if len(raw) >= 2 and raw[:2] == b"\xff\xfe":
        raw = raw[2:]
    for i in range(0, min(128, len(raw) - 6)):
        if raw[i : i + 4] != b"\x00\x00\x01\x00":
            continue
        count = int.from_bytes(raw[i + 4 : i + 6], "little")
        if 1 <= count <= 32:
            return raw[i:]
    return raw


def _try_load_rgba_from_ico_bytes(data: bytes) -> Image.Image | None:
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return im.convert("RGBA")
    except OSError:
        return None


def _synthetic_base_rgba(size: int = 256) -> Image.Image:
    """Alleen als er geen PNG en geen geldige ICO is."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    m = max(4, int(size * 0.06))
    r = int(size * 0.2)
    draw.rounded_rectangle(
        [m, m, size - m, size - m],
        radius=r,
        fill=(22, 27, 34, 255),
        outline=(232, 184, 109, 255),
        width=max(2, size // 64),
    )
    ch = "H"
    font_size = int(size * 0.46)
    font: ImageFont.ImageFont | None = None
    for fp in (
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ):
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), ch, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), ch, font=font, fill=(245, 220, 175, 255))
    return im


def _find_source_png(repo_root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    assets = repo_root / "assets"
    for name in ("Hermes_logo.png", "hermes_logo.png"):
        p = assets / name
        if p.is_file():
            return p
    return None


def _load_master_from_png(png_path: Path, *, apply_black_key: bool = True) -> Image.Image:
    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    im = im.crop((left, top, left + side, top + side))
    if apply_black_key:
        im = _suppress_near_black_alpha(im, LUM_KEY_LO, LUM_KEY_HI)
    im = _expand_content_to_square_canvas(im, CONTENT_FILL)
    side2 = im.width
    if side2 > MASTER_MAX_SIDE:
        im = im.resize((MASTER_MAX_SIDE, MASTER_MAX_SIDE), Image.Resampling.LANCZOS)
    elif side2 < 256:
        im = im.resize((256, 256), Image.Resampling.LANCZOS)
    return im


def _apply_circular_mask_rgba(im: Image.Image) -> Image.Image:
    """Maakt alles buiten de ingeschreven cirkel transparant (vierkant canvas, zelfde afmeting)."""
    im = im.convert("RGBA")
    w, h = im.size
    if w < 1 or h < 1:
        return im
    side = min(w, h)
    if (w, h) != (side, side):
        left = (w - side) // 2
        top = (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
        w = h = side
    transparent = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, w - 1, h - 1), fill=255)
    return Image.composite(im, transparent, mask)


def _suppress_near_black_alpha(
    im: Image.Image, lum_lo: float = LUM_KEY_LO, lum_hi: float = LUM_KEY_HI
) -> Image.Image:
    """Maakt (bijna)zwarte pixels transparant met zachte rand — typisch vlak achter een gouden embleem."""
    im = im.convert("RGBA")
    w, h = im.size
    buf = im.tobytes()
    out = bytearray(len(buf))
    span = max(lum_hi - lum_lo, 1e-6)
    for i in range(0, len(buf), 4):
        r, g, b, a = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
        if a == 0:
            continue
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        t = (lum - lum_lo) / span
        if t <= 0.0:
            pass  # volledig transparant
        elif t >= 1.0:
            out[i : i + 4] = buf[i : i + 4]
        else:
            na = int(a * t + 0.5)
            if na <= 0:
                pass
            else:
                out[i] = r
                out[i + 1] = g
                out[i + 2] = b
                out[i + 3] = na
    return Image.frombytes("RGBA", (w, h), bytes(out))


def _finalize_transparency_for_windows_ico(im: Image.Image) -> Image.Image:
    """
    Verwijdert donkere halftransparante randen en resterend kernzwart dat op de taakbalk als
    een zwart vierkant leest (cmd/WScript.Shell + sommige shell-blends). Zet echte lege pixels op #00000000.
    """
    im = im.convert("RGBA")
    w, h = im.size
    buf = bytearray(im.tobytes())
    for i in range(0, len(buf), 4):
        r, g, b, a = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
        if a == 0:
            continue
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        mx = max(r, g, b)
        if a < 28:
            buf[i : i + 4] = b"\0\0\0\0"
            continue
        if a < 252 and lum < 40 and mx < 58:
            buf[i : i + 4] = b"\0\0\0\0"
            continue
        if a > 90 and mx < 26 and lum < 30:
            buf[i : i + 4] = b"\0\0\0\0"
            continue
        if a > 50 and mx < 18 and lum < 22:
            buf[i : i + 4] = b"\0\0\0\0"
            continue
    return Image.frombytes("RGBA", (w, h), bytes(buf))


def _kill_desaturated_dark_rgba(im: Image.Image) -> Image.Image:
    """
    Verwijdert donker, bijna-grijs vlak binnen het medaillon (zeer lage kleurverzadiging) —
    typisch restanten van een zwarte achtergrond binnen de cirkel (het masker knipt alleen hoeken weg).
    """
    im = im.convert("RGBA")
    w, h = im.size
    buf = bytearray(im.tobytes())
    for i in range(0, len(buf), 4):
        r, g, b, a = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
        if a < 18:
            continue
        mx = max(r, g, b)
        mn = min(r, g, b)
        if mx < 1:
            buf[i : i + 4] = b"\0\0\0\0"
            continue
        sat = (mx - mn) / float(mx)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        if sat < 0.17 and lum < 64 and mx < 82:
            buf[i : i + 4] = b"\0\0\0\0"
    return Image.frombytes("RGBA", (w, h), bytes(buf))


def _expand_content_to_square_canvas(
    im: Image.Image, fill_ratio: float = CONTENT_FILL
) -> Image.Image:
    """Centreert het zichtbare beeld (alpha) en schaalt op zodat het ~fill_ratio van de zijde vult."""
    im = im.convert("RGBA")
    w, h = im.size
    if w < 2 or h < 2:
        return im
    side = min(w, h)
    if (w, h) != (side, side):
        left = (w - side) // 2
        top = (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
        w = h = side
    alpha = im.split()[3]
    # Alleen pixels met voldoende alpha meetellen: voorkomt dat een zwakke/halo-rand de bbox opblaast
    # en het embleem visueel klein houdt.
    bbox = alpha.point(lambda p: 255 if p > BBOX_ALPHA_FLOOR else 0).getbbox()
    if bbox is None:
        bbox = alpha.getbbox()
    if bbox is None:
        return im
    bx0, by0, bx1, by1 = bbox
    bw, bh = bx1 - bx0, by1 - by0
    if bw < 2 or bh < 2:
        return im
    if bw >= fill_ratio * side and bh >= fill_ratio * side:
        return im
    pad = max(2, int(max(bw, bh) * 0.035))
    x0 = max(0, bx0 - pad)
    y0 = max(0, by0 - pad)
    x1 = min(side, bx1 + pad)
    y1 = min(side, by1 + pad)
    crop = im.crop((x0, y0, x1, y1))
    cw, ch = crop.size
    scale = (fill_ratio * side) / max(cw, ch, 1)
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    resized = crop.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox = (side - nw) // 2
    oy = (side - nh) // 2
    canvas.paste(resized, (ox, oy), resized)
    return canvas


def _write_circular_masked_source_png(png_path: Path, *, apply_black_key: bool = True) -> None:
    """Centraal vierkant, optioneel luminantie-key + upschaal embleem, cirkelmasker; atomisch naar png_path."""
    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    square = im.crop((left, top, left + side, top + side))
    if square.width > WRITE_PIPELINE_MAX_SIDE:
        square = square.resize(
            (WRITE_PIPELINE_MAX_SIDE, WRITE_PIPELINE_MAX_SIDE),
            Image.Resampling.LANCZOS,
        )
    if apply_black_key:
        square = _suppress_near_black_alpha(square, LUM_KEY_LO, LUM_KEY_HI)
    square = _expand_content_to_square_canvas(square, CONTENT_FILL)
    masked = _apply_circular_mask_rgba(square)
    masked = _kill_desaturated_dark_rgba(masked)
    masked = _finalize_transparency_for_windows_ico(masked)
    tmp = png_path.with_name(png_path.stem + ".tmp.png")
    masked.save(tmp, format="PNG", compress_level=6)
    tmp.replace(png_path)


def _recolor_hue_rgba(im: Image.Image, tr: int, tg: int, tb: int) -> Image.Image:
    """Zelfde luminantie-structuur: hue naar doelkleur, saturatie/helderheid licht opgevoerd."""
    out = im.copy()
    trn, tgn, tbn = tr / 255.0, tg / 255.0, tb / 255.0
    target_h, _, _ = colorsys.rgb_to_hsv(trn, tgn, tbn)
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
            _h, s, v = colorsys.rgb_to_hsv(rn, gn, bn)
            s2 = min(1.0, s * 1.08 + 0.1)
            v2 = min(1.0, v * 1.04 + 0.03)
            r2, g2, b2 = colorsys.hsv_to_rgb(target_h, s2, v2)
            px[x, y] = (
                min(255, int(r2 * 255)),
                min(255, int(g2 * 255)),
                min(255, int(b2 * 255)),
                a,
            )
    return out


def _pyramid_from_master(master: Image.Image) -> list[Image.Image]:
    master = master.convert("RGBA")
    side = min(master.size)
    if master.size != (side, side):
        left = (master.width - side) // 2
        top = (master.height - side) // 2
        master = master.crop((left, top, left + side, top + side))
    return [master.resize((sz, sz), Image.Resampling.LANCZOS) for sz in ICO_SIZES]


def _patch_ico_bmp_append_and_mask(ico_path: Path) -> None:
    """
    Pillow schrijft 32bpp DIB-in-ICO met ``biHeight`` = 2×nominaal maar **zonder** AND-monomaan.
    Vul ontbrekende AND-bytes (nullen) en corrigeer ``biSizeImage`` / ``dwBytesInRes``.
    """
    data = bytearray(ico_path.read_bytes())
    if len(data) < 22 or data[:4] != b"\x00\x00\x01\x00":
        return
    n = struct.unpack_from("<H", data, 4)[0]
    cursor = 6
    modified = False
    for _ in range(n):
        if cursor + 16 > len(data):
            return
        _w0, _h0, _cc, _res, _planes, bpp, blk_sz, blk_off = struct.unpack_from("<BBBBHHII", data, cursor)
        if bpp != 32 or blk_off + blk_sz > len(data):
            cursor += 16
            continue
        blob_bytes = bytes(data[blk_off : blk_off + blk_sz])
        if len(blob_bytes) < 44 or blob_bytes[:4] == b"\x89PNG":
            cursor += 16
            continue
        hs = int.from_bytes(blob_bytes[0:4], "little")
        if hs < 40:
            cursor += 16
            continue
        biw = int.from_bytes(blob_bytes[4:8], "little")
        bih = int.from_bytes(blob_bytes[8:12], "little")
        if bih < biw * 2:
            cursor += 16
            continue
        nominal = bih // 2
        stride = ((biw * 32 + 31) // 32) * 4
        xor_bytes = stride * nominal
        and_row = ((biw + 31) // 32) * 4
        and_bytes = and_row * nominal
        need = 40 + xor_bytes + and_bytes
        if len(blob_bytes) >= need:
            cursor += 16
            continue
        new_blob = bytearray(blob_bytes[: 40 + xor_bytes]) + bytes(and_bytes)
        struct.pack_into("<I", new_blob, 20, xor_bytes + and_bytes)
        new_blk_sz = len(new_blob)
        tail = bytes(data[blk_off + blk_sz :])
        data[:] = data[:blk_off] + bytes(new_blob) + tail
        struct.pack_into("<I", data, cursor + 8, new_blk_sz)
        modified = True
        cursor += 16
    if modified:
        ico_path.write_bytes(data)


def _save_ico(pyramid_smallest_first: list[Image.Image], path: Path) -> None:
    """
    Alleen 256×256: ``bitmap_format='bmp'`` + ``_patch_ico_bmp_append_and_mask`` — volledige
    Windows-DIB in ICO (anders zwart vlak in Shell); ``IconLocation`` blijft ``,0``.
    """
    largest = _finalize_transparency_for_windows_ico(pyramid_smallest_first[-1])
    largest.save(
        path,
        format="ICO",
        sizes=[(256, 256)],
        bitmap_format="bmp",
    )
    _patch_ico_bmp_append_and_mask(path)


def _load_master_from_windows_ico(windows_dir: Path) -> Image.Image | None:
    src = windows_dir / "hermes_logo.ico"
    if not src.is_file():
        return None
    raw_original = src.read_bytes()
    normalized = _normalize_ico_bytes(raw_original)
    if normalized != raw_original:
        src.write_bytes(normalized)
        print(f"[OK] ICO-header genormaliseerd: {src.name}")
    for candidate in (normalized, raw_original):
        im = _try_load_rgba_from_ico_bytes(candidate)
        if im is not None:
            return im
    bak = windows_dir / "hermes_logo.ico.corrupt.bak"
    shutil.copyfile(src, bak)
    print(
        f"[WARN] hermes_logo.ico onleesbaar — backup {bak.name}; zoek PNG in assets/.",
        file=sys.stderr,
    )
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Hermes .ico uit PNG + kleurvarianten.")
    ap.add_argument(
        "--png",
        type=Path,
        default=None,
        help="Pad naar bron-PNG (default: assets/Hermes_logo.png)",
    )
    ap.add_argument(
        "--full-square",
        action="store_true",
        help="Geen cirkelmasker: volledig vierkant behouden (standaard is buiten de cirkel transparant).",
    )
    ap.add_argument(
        "--no-black-key",
        action="store_true",
        help="Geen luminantie-key op zwart vlak; embleem wordt nog wel opgeschaald naar de taakbalk-vulling.",
    )
    args = ap.parse_args()

    windows_dir = Path(__file__).resolve().parent.parent
    repo_root = windows_dir.parent

    png_path = _find_source_png(repo_root, args.png)
    master: Image.Image | None = None
    apply_key = not args.no_black_key

    if png_path is not None:
        if not args.full_square:
            _write_circular_masked_source_png(png_path, apply_black_key=apply_key)
            print(
                f"[OK] Bron-PNG bijgewerkt (cirkel + opschaal embleem"
                f"{'' if apply_key else ' (zonder luminantie-key)'}; pipeline max {WRITE_PIPELINE_MAX_SIDE}px): "
                f"{png_path.relative_to(repo_root)}"
            )
        master = _load_master_from_png(png_path, apply_black_key=apply_key)
        print(f"[OK] Bron: {png_path.relative_to(repo_root)} ({master.width}x{master.height})")
    else:
        master = _load_master_from_windows_ico(windows_dir)
        if master is None:
            master = _synthetic_base_rgba(256)
            print("[WARN] Geen PNG in assets/ — synthetisch basisbeeld.", file=sys.stderr)

    if not args.full_square and png_path is None and master is not None:
        w, h = master.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        master = master.crop((left, top, left + side, top + side))
        if apply_key:
            master = _suppress_near_black_alpha(master, LUM_KEY_LO, LUM_KEY_HI)
        master = _expand_content_to_square_canvas(master, CONTENT_FILL)
        master = _apply_circular_mask_rgba(master)
        master = _kill_desaturated_dark_rgba(master)
        print("[OK] Icoon-PNG: key/opschaal + cirkelmasker (bron was geen assets-PNG).")

    master = _finalize_transparency_for_windows_ico(master.convert("RGBA"))
    base_pyramid = _pyramid_from_master(master)
    out_main = windows_dir / "hermes_logo.ico"
    _save_ico(base_pyramid, out_main)
    print(f"[OK] {out_main.name} — originele kleuren (256×256 ICO)")

    for filename, tint in VARIANTS.items():
        tr, tg, tb = tint
        layers: list[Image.Image] = []
        for layer in base_pyramid:
            layers.append(_recolor_hue_rgba(layer.copy(), tr, tg, tb))
        out_path = windows_dir / filename
        _save_ico(layers, out_path)
        print(f"[OK] {out_path.name} (256×256 ICO)")


if __name__ == "__main__":
    main()
