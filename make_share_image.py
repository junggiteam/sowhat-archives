"""Render the link-preview (Open Graph) card: assets/sowhat-og-v4.png, 1200x630.

Photo background (assets/src/og-photo.webp) lightly darkened, centred three-line
copy with a soft shadow. Run locally with Pillow; uses the Noto Sans KR variable
font that ships with Windows 11. Scheduled builds do not need this.
When the design changes, bump the file name (and build_site.py) so KakaoTalk
and other messengers fetch the new image instead of a cached one.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
NOTO = 'C:/Windows/Fonts/NotoSansKR-VF.ttf'
W, H, S = 1200, 630, 2
BRIGHT_RED = (255, 92, 92)
L1, L2A, L2B = '결론이 있는 뉴스레터', '중기이코노미 ', '쏘왓레터'
SUB = '복잡한 정보는 덜어내고, 방향성 있는 결론만'


def font(size, weight):
    f = ImageFont.truetype(NOTO, size * S)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def photo(size):
    im = Image.open(ROOT / 'assets/src/og-photo.webp').convert('RGB')
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left, top = (im.width - tw) // 2, (im.height - th) // 2
    return im.crop((left, top, left + tw, top + th))


def radial(size, inner_alpha, outer_alpha):
    """Darker behind the text in the centre, lighter towards the edges."""
    small = Image.new('L', (120, 63))
    px = small.load()
    for y in range(63):
        for x in range(120):
            dx, dy = (x - 59.5) / 60, (y - 31) / 34
            t = min(1, (dx * dx + dy * dy) ** 0.5)
            px[x, y] = round(inner_alpha + (outer_alpha - inner_alpha) * t)
    layer = Image.new('RGBA', size, (10, 14, 22, 0))
    layer.putalpha(small.resize(size, Image.BICUBIC))
    return layer


def main(head_size=96, sub_size=42, sub_color=(248, 249, 251), sub_gap_px=38, target=None):
    base = photo((W * S, H * S)).convert('RGBA')
    base.alpha_composite(Image.new('RGBA', base.size, (10, 14, 22, 70)))
    base.alpha_composite(radial(base.size, 120, 20))

    head, sub = font(head_size, 800), font(sub_size, 500)
    d = ImageDraw.Draw(base)
    hb = d.textbbox((0, 0), L1, font=head)
    sb = d.textbbox((0, 0), SUB, font=sub)
    hh, sh = hb[3] - hb[1], sb[3] - sb[1]
    gap, sub_gap = 18 * S, sub_gap_px * S
    top = (H * S - (hh * 2 + gap + sub_gap + sh)) // 2
    cx = W * S // 2
    y2 = top + hh + gap
    y3 = y2 + hh + sub_gap
    lines = [(L1, head, top - hb[1]), (L2A + L2B, head, y2 - hb[1]), (SUB, sub, y3 - sb[1])]

    # Soft shadow so the text stays crisp over the bright newspapers.
    shadow = Image.new('RGBA', base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for text, f, y in lines:
        sd.text((cx - sd.textlength(text, font=f) / 2, y + 3 * S), text, font=f, fill=(0, 0, 0, 170))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7 * S)))

    d = ImageDraw.Draw(base)
    d.text((cx - d.textlength(L1, font=head) / 2, top - hb[1]), L1, font=head, fill=(255, 255, 255))
    w2 = d.textlength(L2A + L2B, font=head)
    d.text((cx - w2 / 2, y2 - hb[1]), L2A, font=head, fill=(255, 255, 255))
    d.text((cx - w2 / 2 + d.textlength(L2A, font=head), y2 - hb[1]), L2B, font=head, fill=BRIGHT_RED)
    d.text((cx - d.textlength(SUB, font=sub) / 2, y3 - sb[1]), SUB, font=sub, fill=sub_color)

    out = base.convert('RGB').resize((W, H), Image.LANCZOS)
    target = target or ROOT / 'assets/sowhat-og-v4.png'
    out.save(target, optimize=True)
    print(target, out.size)


if __name__ == '__main__':
    main()
