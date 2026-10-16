"""Draw the application icon (assets/app.ico). Run once; the .ico is committed."""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size // 5
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(31, 58, 95, 255))
    # three rising bars + trend line: "finance training"
    w = size // 7
    base = int(size * 0.80)
    for i, h in enumerate((0.25, 0.40, 0.58)):
        x = int(size * 0.20) + i * int(w * 1.55)
        d.rectangle([x, base - int(size * h), x + w, base], fill=(57, 135, 229, 255))
    d.line([(int(size * 0.18), int(size * 0.50)), (int(size * 0.45), int(size * 0.36)),
            (int(size * 0.82), int(size * 0.16))], fill=(63, 191, 127, 255), width=max(2, size // 18))
    return img


if __name__ == "__main__":
    out = ROOT / "assets" / "app.ico"
    draw(256).save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    draw(256).save(ROOT / "assets" / "app.png")
    print(out)
