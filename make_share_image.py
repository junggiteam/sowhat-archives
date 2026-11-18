"""Render the site's original typographic share card. Run locally with Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = Path('C:/Windows/Fonts')


def main():
    canvas = Image.new('RGB',(1200,630),'#fffefb')
    draw = ImageDraw.Draw(canvas)
    def text(x,y,value,size,color='#202021',bold=False):
        font = ImageFont.truetype(str(FONT/('malgunbd.ttf' if bold else 'malgun.ttf')),size)
        draw.text((x,y),value,font=font,fill=color,stroke_width=0)
    draw.rectangle((0,0,1200,11),fill='#d12f30')
    text(72,58,'SO WHAT?',76,'#d12f30',True)
    text(78,169,'THE LETTER ARCHIVE',19,'#858576',True)
    text(70,213,'쏘왓레터 모아보기',76,bold=True)
    text(78,331,'경제 · 기업 · M&A · 기업승계 · 세무',29,'#66665d')
    draw.line((78,416,1122,416),fill='#deded5',width=2)
    text(78,452,'지난 뉴스레터를 대표이미지와 제목으로 만나보세요.',26,'#66665d')
    text(78,550,'중기이코노미 × BEST EXIT',21,'#747468',True)
    text(775,548,'sowhat.bestexit.co.kr',23,'#d12f30',True)
    target = ROOT/'assets/sowhat-share.png'
    target.parent.mkdir(exist_ok=True)
    canvas.save(target,optimize=True)


if __name__ == '__main__':
    main()
