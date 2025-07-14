import os
import shutil
import re
from pathlib import Path
from PIL import Image
import xml.etree.ElementTree as ET
import csv

LOGOS_DIR = "data/logos/"
SVG_OUT   = "data/logos_svg_patch/"
BAD_SVG   = "data/bad_svg/"
BAD_RASTER = "data/bad_raster/"
CSV_LOG   = "svg_patch_report.csv"

DEFAULT_SIZE = 256

# common HTML entities that may break SVG parsing if not replaced
ENTITY_MAP = {
    "&uuml;": "ü",
    "&Uuml;": "Ü",
    "&aacute;": "á",
    "&Aacute;": "Á",
    "&eacute;": "é",
    "&oacute;": "ó",
    "&iacute;": "í",
    "&ntilde;": "ñ",
    "&amp;": "&",
    "&quot;": '"',
    "&lt;": "<",
    "&gt;": ">",
    
}

#read all error files from a previous error report CSV produced by preprocess step
def get_error_files(csv_file):
    error_files = []
    with open(csv_file, encoding="utf8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            error_files.append(row['filename'])
    return error_files

#patch SVGs: fix entities, add width/height if missing, and validate XML syntax
def patch_svg_file(path, out_path):
    try:
        #open SVG as text
        with open(path, encoding="utf8") as f:
            data = f.read()

        for k, v in ENTITY_MAP.items():
            data = data.replace(k, v)

     #ensure <svg> tag has width and height attributes
        if re.search(r"<svg[^>]+>", data, re.IGNORECASE):
            
            m = re.search(r"<svg([^>]*)>", data, re.IGNORECASE)
            if m:
                attrs = m.group(1)
                if "width" not in attrs or "height" not in attrs:
                    
                    attrs_new = attrs
                    if "width" not in attrs:
                        attrs_new += f' width="{DEFAULT_SIZE}"'
                    if "height" not in attrs:
                        attrs_new += f' height="{DEFAULT_SIZE}"'
                    data = data.replace(m.group(0), f"<svg{attrs_new}>")

      
        with open(out_path, "w", encoding="utf8") as f:
            f.write(data)

         # try parsing as XML to ensure it s now valid
        try:
            ET.fromstring(data)
            return "patched", ""
        except ET.ParseError as e:
            # any other failure: copy file to BAD_SVG and log error
            shutil.move(out_path, os.path.join(BAD_SVG, os.path.basename(path)))
            return "xml_error", str(e)

    except Exception as e:
        shutil.copy(path, os.path.join(BAD_SVG, os.path.basename(path)))
        return "fail", str(e)

# for raster images: try opening to verify it's not corrupt
def check_raster_file(path):
    try:
        with Image.open(path) as img:
            img.verify()
        return "ok", ""
    except Exception as e:
        shutil.move(path, os.path.join(BAD_RASTER, os.path.basename(path)))
        return "corrupt", str(e)

def ensure_dirs():
    for d in [SVG_OUT, BAD_SVG, BAD_RASTER]:
        Path(d).mkdir(parents=True, exist_ok=True)

def main():
    ensure_dirs()
    
    error_files = get_error_files("data/preprocess_errors.csv")
    results = []
    for fname in error_files:
        path = os.path.join(LOGOS_DIR, fname)
        if not os.path.exists(path):
            # file missing log as error, continue
            results.append([fname, "not_found", "", "File missing!"])
            continue
        ext = fname.lower().rsplit('.', 1)[-1]
        if ext == "svg":
            # try to patch and fix the SVG, then validate
            out_path = os.path.join(SVG_OUT, fname)
            res, err = patch_svg_file(path, out_path)
            results.append([fname, "svg", res, err])
        elif ext in {"png", "jpg", "jpeg"}:
            res, err = check_raster_file(path)
            results.append([fname, "raster", res, err])

  
    with open(CSV_LOG, "w", encoding="utf8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "type", "result", "error"])
        writer.writerows(results)

    print(f"[OK] Patch/filtrare terminat. Log în {CSV_LOG}")

if __name__ == "__main__":
    main()
