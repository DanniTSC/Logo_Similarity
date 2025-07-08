import os
from pathlib import Path
from PIL import Image, ImageOps
import cairosvg
import csv


RAW_DIR   = "data/logos/"
OUT_DIR   = "data/logos_preprocessed/"
ERR_CSV   = "data/preprocess_errors.csv"
SIZE      = (128, 128)
BG_COLOR  = (255, 255, 255)  

def ensure_out_dir():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

def rasterize_svg(path):
    from io import BytesIO
    png_bytes = cairosvg.svg2png(url=path)
    return Image.open(BytesIO(png_bytes))

def preprocess_image(in_path, out_path):
    ext = in_path.lower().rsplit(".",1)[-1]
    if ext == "svg":
        img = rasterize_svg(in_path)
    else:
        img = Image.open(in_path)

    
    if img.mode in ("RGBA", "LA") or (img.mode=="P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, BG_COLOR + (255,))
        bg.paste(img, mask=img.split()[3])
        img = bg

    if img.mode != "RGB":
        img = img.convert("RGB")

    img = ImageOps.grayscale(img)
    img = ImageOps.pad(img, SIZE, color=255)
    img.save(out_path, format="PNG", optimize=True)

def main():
    ensure_out_dir()
    errors = []
    for fname in os.listdir(RAW_DIR):
        inp = os.path.join(RAW_DIR, fname)
        name, _ = os.path.splitext(fname)
        out = os.path.join(OUT_DIR, f"{name}.png")
        try:
            preprocess_image(inp, out)
            print(f"[OK] {fname} → {out}")
        except Exception as e:
            print(f"[ERROR] {fname}: {e}")
            errors.append([fname, str(e)])
   
    if errors:
        with open(ERR_CSV, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["filename", "error"])
            writer.writerows(errors)
        print(f"[INFO] {len(errors)} fișiere cu erori. Vezi {ERR_CSV}")

if __name__ == "__main__":
    main()
