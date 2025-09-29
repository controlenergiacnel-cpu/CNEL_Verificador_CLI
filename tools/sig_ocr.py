# tools/sig_ocr.py
from __future__ import annotations
import sys, os, json, tempfile
import fitz  # PyMuPDF

def _load_cfg():
    try:
        with open(os.path.join("config", "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _make_reader(langs):
    # Preferimos EasyOCR si está instalado; si no, caemos a Tesseract (opcional)
    try:
        import easyocr
        return ("easyocr", easyocr.Reader(langs, gpu=False))
    except Exception:
        try:
            import pytesseract
            from PIL import Image
            return ("tesseract", (pytesseract, Image))
        except Exception:
            return (None, None)

def _ocr_image_bytes(engine, obj, png_bytes, lang):
    if engine == "easyocr":
        reader = obj
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name
        try:
            lines = reader.readtext(tmp_path, detail=0, paragraph=True)
            return "\n".join(lines).strip()
        finally:
            try: os.unlink(tmp_path)
            except: pass
    elif engine == "tesseract":
        pytesseract, Image = obj
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name
        try:
            im = Image.open(tmp_path)
            return pytesseract.image_to_string(im, lang=lang).strip()
        finally:
            try: os.unlink(tmp_path)
            except: pass
    else:
        return ""

def _iter_signature_widgets(page):
    # Devuelve (widget, rect, name) para firmas
    out = []
    # PyMuPDF nuevo: page.widgets; fallback via anotaciones si hiciera falta
    try:
        widgets = page.widgets or []
        for w in widgets:
            ft = getattr(w, "field_type", None)
            fts = getattr(w, "field_type_string", "") or ""
            if ft == fitz.PDF_WIDGET_TYPE_SIGNATURE or "signature" in fts.lower():
                out.append((w, w.rect, getattr(w, "field_name", None)))
    except Exception:
        pass
    # Fallback mínimo usando anotaciones tipo 'Widget'
    try:
        a = page.first_annot
        while a:
            try:
                if a.type[0] == fitz.PDF_ANNOT_WIDGET:
                    # No siempre podemos distinguir FT/Sig aquí, así que lo omitimos para no falsear
                    pass
            except Exception:
                pass
            a = a.next
    except Exception:
        pass
    return out

def ocr_signatures(pdf_path: str, dpi=300, margin=2):
    cfg = _load_cfg()
    langs = (cfg.get("ocr") or {}).get("langs") or ["es", "en"]
    lang_str = "+".join(langs)
    engine, obj = _make_reader(langs)
    results = {"file": pdf_path, "engine": engine or "none", "signatures": []}

    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, 1):
            for w, rect, fname in _iter_signature_widgets(page):
                r = fitz.Rect(rect)
                r = fitz.Rect(r.x0 - margin, r.y0 - margin, r.x1 + margin, r.y1 + margin)
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat, clip=r, alpha=False)
                png = pix.tobytes("png")
                txt = _ocr_image_bytes(engine, obj, png, lang_str)
                results["signatures"].append({
                    "page": pno,
                    "field_name": fname,
                    "rect": [r.x0, r.y0, r.x1, r.y1],
                    "dpi": dpi,
                    "text": txt,
                    "text_len": len(txt)
                })
    return results

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.sig_ocr <archivo.pdf|carpeta>")
        raise SystemExit(1)

    target = sys.argv[1]
    files = []
    if os.path.isdir(target):
        for r, d, fns in os.walk(target):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    files.append(os.path.join(r, fn))
    else:
        files = [target]

    all_out = []
    for f in files:
        try:
            all_out.append(ocr_signatures(f))
        except Exception as e:
            all_out.append({"file": f, "error": str(e)})

    print(json.dumps(all_out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
