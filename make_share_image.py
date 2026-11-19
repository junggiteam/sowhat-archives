"""Render the link-preview (Open Graph) card: assets/sowhat-og.png, 1200x630.

Run locally with Pillow. Uses the Noto Sans KR variable font that ships with
Windows 11 and the wordmark logos in assets/. Scheduled builds do not need this.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
NOTO = Path('C:/Windows/Fonts/NotoSansKR-VF.ttf')
RED = '#d12f30'
INK = '#15171b'
GREY = '#6b707a'
W, H = 1200, 630


def font(size, weight):
    f = ImageFont.truetype(str(NOTO), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def main():
    # Draw at 2x and downsample for smooth edges.
    s = 2
    canvas = Image.new('RGB', (W * s, H * s), '#ffffff')
    draw = ImageDraw.Draw(canvas)

    # Soft decorative question mark on the right.
    draw.text((865 * s, 20 * s), '?', font=font(560 * s, 900), fill='#f5f6f8')
    # Red accent bar on the left edge.
    draw.rectangle((0, 0, 14 * s, H * s), fill=RED)

    x = 96
    eyebrow = font(22 * s, 600)
    cx = x * s
    for ch in 'SOWHAT LETTER':
        draw.text((cx, 92 * s), ch, font=eyebrow, fill='#8a9099')
        cx += draw.textlength(ch, font=eyebrow) + 7 * s

    head = font(86 * s, 800)
    draw.text((x * s, 140 * s), '결론이 있는 뉴스레터', font=head, fill=INK)
    first = '중기이코노미 '
    draw.text((x * s, 252 * s), first, font=head, fill=INK)
    draw.text((x * s + draw.textlength(first, font=head), 252 * s), '쏘왓레터', font=head, fill=RED)

    sub = font(30 * s, 500)
    draw.text((x * s, 392 * s), '복잡한 정보는 덜어내고, 방향성 있는 결론만', font=sub, fill=GREY)

    draw.line((x * s, 486 * s, (W - x) * s, 486 * s), fill='#e5e7eb', width=2 * s)

    # Publisher wordmarks, matched by width like the site footer.
    lx = x * s
    for name, height in (('junggi-wordmark.png', 30), ('bestexit-wordmark.png', 24.5)):
        logo = Image.open(ROOT / 'assets' / name).convert('RGBA')
        h = int(height * s)
        w = int(logo.width * h / logo.height)
        logo = logo.resize((w, h), Image.LANCZOS)
        canvas.paste(logo, (lx, int((540 - height / 2) * s)), logo)
        lx += w + 34 * s

    url = font(26 * s, 700)
    text = 'sowhat.bestexit.co.kr'
    draw.text(((W - x) * s - draw.textlength(text, font=url), 522 * s), text, font=url, fill=RED)

    out = canvas.resize((W, H), Image.LANCZOS)
    target = ROOT / 'assets/sowhat-og.png'
    out.save(target, optimize=True)
    print(target, out.size)


if __name__ == '__main__':
    main()
