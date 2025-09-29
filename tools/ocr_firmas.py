from __future__ import annotations
import sys, os, json, time
import fitz  # PyMuPDF
from PIL import Image
import numpy as np

def guess_tesseract_cmd():
    try:
        import json as _json
        p = os.path.join("config", "config.json")
        if os.path.exists(p):
            cfg = _json.load(open(p, "r", encoding="utf-8"))
            tcmd = ((cfg.get("tesseract") or {}).get("cmd") or "").strip()
            return tcmd or None
    except Exception:
        pass
    return None

def ocr_image(img):
    # 1) pytesseract
    try:
        import pytesseract
        tcmd = guess_tesseract_cmd()
        if tcmd:
            pytesseract.pytesseract.tesseract_cmd = tcmd
        return pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:
        pass
    # 2) easyocr (fallback)
    try:
        import easyocr
        reader = easyocr.Reader(["es","en"], gpu=False, verbose=False)
        arr = np.array(img.convert("RGB"))
        lines = reader.readtext(arr, detail=False, paragraph=True)
        return "\n".join(lines)
    except Exception as e:
        return f"[OCR error] {e}"

def extract_sig_rects(doc):
    rects = []
    for pno in range(len(doc)):
        page = doc[pno]
        # Widgets (preferido)
        try:
            widgets = page.widgets()
        except Exception:
            widgets = None
        if widgets:
            for w in widgets:
                ftype = str(getattr(w, "field_type", "")).lower()
                if "sig" in ftype:
                    rects.append((pno, fitz.Rect(w.rect)))
        # Annotations (fallback)
        try:
            for annot in page.annots() or []:
                try:
                    if str(getattr(annot, "type", ("",""))[1]).lower() == "widget":
                        ftype = str(getattr(annot, "field_type", "")).lower()
                        if "sig" in ftype:
                            rects.append((pno, fitz.Rect(annot.rect)))
                except Exception:
                    continue
        except Exception:
            pass
    return rects

def process_file(path, outdir):
    out = []
    with fitz.open(path) as doc:
        sig_rects = extract_sig_rects(doc)
        for idx, (pno, rect) in enumerate(sig_rects, 1):
            page = doc[pno]
            clip = fitz.Rect(rect).inflate(10)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            txt = ocr_image(img)
            base = os.path.splitext(os.path.basename(path))[0]
            name = f"{base}_p{pno+1}_sig{idx}.txt"
            with open(os.path.join(outdir, name), "w", encoding="utf-8") as f:
                f.write(txt)
            out.append({"page": pno+1, "rect": [clip.x0, clip.y0, clip.x1, clip.y1], "text_preview": txt[:200]})
    return out

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.ocr_firmas <archivo.pdf | carpeta>")
        sys.exit(1)
    target = sys.argv[1]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    outdir = os.path.join("_sig_ocr", stamp)
    os.makedirs(outdir, exist_ok=True)
    files = []
    if os.path.isdir(target):
        for r, _, fns in os.walk(target):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    files.append(os.path.join(r, fn))
    else:
        files = [target]
    results = []
    for p in files:
        try:
            items = process_file(p, outdir)
            results.append({"file": p, "found_boxes": len(items), "boxes": items})
        except Exception as e:
            results.append({"file": p, "error": str(e)})
    summary = os.path.join(outdir, "summary.json")
    with open(summary, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps({"outdir": outdir, "files": len(files)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
