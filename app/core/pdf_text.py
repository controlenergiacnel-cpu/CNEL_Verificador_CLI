from __future__ import annotations
from typing import List, Tuple, Dict, Any
import os, json, tempfile, subprocess
import fitz  # PyMuPDF
import sys

def _load_cfg() -> Dict[str, Any]:
    try:
        with open(os.path.join("config", "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _run_ocrmypdf(src: str, dst: str, cfg: Dict[str, Any]) -> bool:
    ocr = (cfg.get("ocr") or {}).get("ocrmypdf") or {}
    if not ocr.get("enable"):
        return False
    jobs = str(ocr.get("jobs", 2))
    timeout = int(ocr.get("timeout_sec", 240))
    flags = list(ocr.get("flags", []))
    cmd = ["python", "-m", "ocrmypdf", "-j", jobs, *flags, src, dst]
    try:
        subprocess.run(cmd, check=True, timeout=timeout)
        return os.path.exists(dst) and os.path.getsize(dst) > 0
    except Exception:
        return False

def _doc_plain_texts(doc: fitz.Document) -> List[str]:
    pages: List[str] = []
    for p in doc:
        t = (p.get_text("text") or "").strip()
        pages.append(t)
    return pages

def _join_pages(pages: List[str]) -> str:
    return "\n\n".join(pages).strip()

def extract_text_with_meta(pdf_path: str, min_chars_for_native: int = 40) -> Dict[str, Any]:
    cfg = _load_cfg()
    ocr_cfg = (cfg.get("ocr") or {})
    force_ocr = bool(ocr_cfg.get("force", False))

    meta: Dict[str, Any] = {
        "pages": 0,
        "chars_total": 0,
        "ocr_pages": [],
        "per_page": [],
        "used_ocr": False,
        "method": "native",
        "sample": ""
    }

    with fitz.open(pdf_path) as doc:
        meta["pages"] = doc.page_count
        native_pages = _doc_plain_texts(doc)
    native_total = sum(len(x) for x in native_pages)

    # Sólo devolvemos nativo de inmediato si NO estamos forzando OCR
    if native_total >= min_chars_for_native and not force_ocr:
        meta["chars_total"] = native_total
        for i, t in enumerate(native_pages, 1):
            meta["per_page"].append({"page": i, "chars": len(t), "empty": len(t.strip()) == 0, "used_ocr": False})
        meta["sample"] = (native_pages[0] or "")[:280] + "..." if native_pages else ""
        return meta

    # Intentar OCRmyPDF primero
    with tempfile.TemporaryDirectory() as td:
        ocr_pdf = os.path.join(td, "ocr.pdf")
        if _run_ocrmypdf(pdf_path, ocr_pdf, cfg):
            with fitz.open(ocr_pdf) as d2:
                ocr_pages = _doc_plain_texts(d2)
            total2 = sum(len(x) for x in ocr_pages)
            # Elegimos el mejor (más texto)
            if total2 >= native_total:
                meta["used_ocr"] = True
                meta["method"] = "ocrmypdf"
                meta["chars_total"] = total2
                for i, t in enumerate(ocr_pages, 1):
                    meta["per_page"].append({"page": i, "chars": len(t), "empty": len(t.strip()) == 0, "used_ocr": True})
                meta["ocr_pages"] = list(range(1, len(ocr_pages) + 1))
                meta["sample"] = (ocr_pages[0] or "")[:280] + "..." if ocr_pages else ""
                return meta

    # Fallback: EasyOCR (tu motor existente)
    try:
        from .ocr_engine import ocr_pages as _easyocr_pages
        with fitz.open(pdf_path) as doc:
            page_ids = list(range(len(doc)))
            ocr_map = _easyocr_pages(doc, page_ids)
        pages = [(ocr_map.get(i, "") or "") for i in range(len(page_ids))]
        total_e = sum(len(x) for x in pages)
        # Elegimos el mejor entre native y easyocr
        if total_e >= native_total:
            meta["used_ocr"] = True
            meta["method"] = "easyocr"
            meta["chars_total"] = total_e
            meta["per_page"] = [{"page": i+1, "chars": len(t), "empty": len(t.strip()) == 0, "used_ocr": True}
                                for i, t in enumerate(pages)]
            meta["ocr_pages"] = list(range(1, len(pages) + 1))
            meta["sample"] = (pages[0] or "")[:280] + "..." if pages else ""
            return meta
    except Exception:
        pass

    # Si OCR no mejoró, nos quedamos con nativo
    meta["chars_total"] = native_total
    for i, t in enumerate(native_pages, 1):
        meta["per_page"].append({"page": i, "chars": len(t), "empty": len(t.strip()) == 0, "used_ocr": False})
    meta["sample"] = (native_pages[0] or "")[:280] + "..." if native_pages else ""
    return meta

def extract_text(pdf_path: str, min_chars_for_native: int = 40) -> Tuple[str, List[str]]:
    meta = extract_text_with_meta(pdf_path, min_chars_for_native=min_chars_for_native)
    try:
        with fitz.open(pdf_path) as doc:
            pages = _doc_plain_texts(doc)
    except Exception:
        pages = []
    if not pages and meta.get("per_page"):
        pages = [""] * len(meta["per_page"])
    text_total = _join_pages(pages)
    return text_total, pages

def _run_ocrmypdf(src: str, dst: str, cfg: Dict[str, Any]) -> bool:
    ocr_root = (cfg.get("ocr") or {})
    ocr = (ocr_root.get("ocrmypdf") or {})
    if not ocr.get("enable"):
        return False

    jobs = str(ocr.get("jobs", 2))
    timeout = int(ocr.get("timeout_sec", 240))
    flags = list(ocr.get("flags", []))

    # Si se fuerza OCR en config, añadimos --force-ocr
    if ocr_root.get("force") and "--force-ocr" not in flags:
        flags.insert(0, "--force-ocr")

    # Preparar entorno para que ocrmypdf encuentre tesseract y tessdata
    env = os.environ.copy()
    texe = ((cfg.get("tesseract") or {}).get("cmd") or "").strip()
    if texe and os.path.exists(texe):
        tdir = os.path.dirname(texe)
        env["PATH"] = tdir + os.pathsep + env.get("PATH", "")
        tdata = os.path.join(tdir, "tessdata")
        if os.path.isdir(tdata):
            env["TESSDATA_PREFIX"] = tdata

    cmd = [sys.executable, "-m", "ocrmypdf", "-j", jobs, *flags, src, dst]

    try:
        cp = subprocess.run(
            cmd,
            check=True,
            timeout=timeout,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        ok = os.path.exists(dst) and os.path.getsize(dst) > 0
        if not ok:
            print("[ocrmypdf] salida:\\n" + (cp.stdout or ""))
        return ok
    except Exception as e:
        try:
            print(f"[ocrmypdf] fallo: {e}")
        except:
            pass
        return False

