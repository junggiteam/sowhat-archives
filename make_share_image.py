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

    # Red accent bar along the top edge.
    draw.rectangle((0, 0, W * s, 14 * s), fill=RED)

    # Decorative question mark on the right, kept fully inside the frame
    # (messengers crop previews slightly at the top and bottom).
    qfont = font(470 * s, 900)
    box = draw.textbbox((0, 0), '?', font=qfont)
    qh = box[3] - box[1]
    qx = (W - 70) * s - (box[2] - box[0]) - box[0]
    qy = (H * s - qh) // 2 - box[1] - 42 * s
    draw.text((qx, qy), '?', font=qfont, fill='#eff1f4')

    # Three lines, vertically centred as one block.
    x = 92
    head = font(104 * s, 800)
    sub = font(40 * s, 500)
    line_gap, sub_gap = 18, 44
    hb = draw.textbbox((0, 0), '결론이 있는 뉴스레터', font=head)
    sb = draw.textbbox((0, 0), '복잡한 정보는 덜어내고', font=sub)
    head_h, sub_h = hb[3] - hb[1], sb[3] - sb[1]
    block = head_h * 2 + line_gap * s + sub_gap * s + sub_h
    top = (H * s - block) // 2 + 6 * s
    draw.text((x * s, top - hb[1]), '결론이 있는 뉴스레터', font=head, fill=INK)
    y2 = top + head_h + line_gap * s
    first = '중기이코노미 '
    draw.text((x * s, y2 - hb[1]), first, font=head, fill=INK)
    draw.text((x * s + draw.textlength(first, font=head), y2 - hb[1]), '쏘왓레터', font=head, fill=RED)
    y3 = y2 + head_h + sub_gap * s
    draw.text((x * s, y3 - sb[1]), '복잡한 정보는 덜어내고, 방향성 있는 결론만', font=sub, fill=GREY)

    out = canvas.resize((W, H), Image.LANCZOS)
    target = ROOT / 'assets/sowhat-og.png'
    out.save(target, optimize=True)
    print(target, out.size)


if __name__ == '__main__':
    main()
