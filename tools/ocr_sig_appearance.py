# -*- coding: utf-8 -*-
r"""Uso:  python tools/ocr_sig_appearance.py RUTA_AL_PDF_O_CARPETA"""
import sys, os, json, io
from typing import List, Dict, Any
import fitz
from PIL import Image
import pytesseract

def collect_pdfs(src: str) -> List[str]:
    if os.path.isfile(src) and src.lower().endswith(".pdf"):
        return [src]
    files = []
    for r,_,fns in os.walk(src):
        for fn in fns:
            if fn.lower().endswith(".pdf"):
                files.append(os.path.join(r, fn))
    return sorted(files)

def ocr_pil(img: Image.Image) -> str:
    try:
        return pytesseract.image_to_string(img, lang="spa+eng") or ""
    except Exception as e:
        return f"[OCR_ERROR] {e.__class__.__name__}: {e}"

def is_signature_widget(w) -> bool:
    try:
        if hasattr(fitz, "PDF_WIDGET_TYPE_SIGNATURE"):
            return getattr(w, "field_type", None) == fitz.PDF_WIDGET_TYPE_SIGNATURE
    except Exception:
        pass
    name = (getattr(w, "field_name", "") or "").lower()
    return ("sign" in name) or ("firma" in name) or ("signature" in name) or ("sig" in name)

def process_file(pdf_path: str) -> Dict[str, Any]:
    out = {"file": pdf_path, "appearances": []}
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        out["appearances"].append({"page": None, "field_name": None, "error": f"{e.__class__.__name__}: {e}"})
        return out

    for pno in range(len(doc)):
        page = doc[pno]
        widgets = []
        try:
            widgets = page.widgets() or []
        except Exception:
            annot = page.first_annot
            while annot:
                try:
                    if getattr(annot, "type", (None,""))[1].lower() == "widget":
                        widgets.append(annot)
                except Exception:
                    pass
                annot = getattr(annot, "next", None)

        for w in widgets:
            try:
                if not is_signature_widget(w): continue
                rect = getattr(w, "rect", None)
                if rect is None: continue
                pix = page.get_pixmap(clip=rect, dpi=300)
                pil = Image.open(io.BytesIO(pix.tobytes("png")))
                text = ocr_pil(pil).strip()
                out["appearances"].append({
                    "page": pno + 1,
                    "field_name": getattr(w, "field_name", None),
                    "rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "ocr_text": text
                })
            except Exception as e:
                out["appearances"].append({
                    "page": pno + 1,
                    "field_name": getattr(w, "field_name", None),
                    "error": f"{e.__class__.__name__}: {e}"
                })
    return out

def main():
    if len(sys.argv) < 2:
        print("[]"); return
    src = sys.argv[1]
    files = collect_pdfs(src)
    results = [process_file(p) for p in files]
    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
