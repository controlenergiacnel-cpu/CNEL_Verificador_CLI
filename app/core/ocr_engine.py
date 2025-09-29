from __future__ import annotations
import io, os, json, sys, tempfile, subprocess, hashlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# EasyOCR (fallback por p?gina)
try:
    import easyocr
except Exception:
    easyocr = None

# --- Config helpers ---
_CFG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.json"

def _load_cfg() -> dict:
    try:
        with open(_CFG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}

def _cfg_get(path: List[str], default=None):
    cfg = _load_cfg()
    node = cfg
    try:
        for p in path:
            node = node[p]
        return node
    except Exception:
        return default

# --- Herramientas de imagen/PyMuPDF ---
def _page_to_pil(page: fitz.Page, scale: float = 2.0) -> Image.Image:
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def _ensure_easyocr(langs: List[str]) -> Optional["easyocr.Reader"]:
    if easyocr is None:
        return None
    return easyocr.Reader(langs, gpu=False, verbose=False)

# --- OCRmyPDF ---
def _tesseract_dir_from_cfg() -> Optional[str]:
    cmd = _cfg_get(["tesseract", "cmd"])
    if not cmd:
        return None
    try:
        return str(Path(cmd).resolve().parent)
    except Exception:
        return None

def _ocrmypdf_flags_from_cfg() -> List[str]:
    flags = _cfg_get(["ocr", "ocrmypdf", "flags"], None)
    if isinstance(flags, list) and flags:
        return [str(x) for x in flags]
    # Defaults razonables
    return [
        "--rotate-pages","--deskew","--clean-final","--remove-background",
        "--redo-ocr","--skip-big","45",
        "--tesseract-timeout","90",
        "-l","spa+eng"
    ]

def _ocrmypdf_jobs_from_cfg() -> int:
    val = _cfg_get(["ocr", "ocrmypdf", "jobs"], 2)
    try:
        return int(val)
    except Exception:
        return 2

def _ocrmypdf_timeout_from_cfg() -> int:
    val = _cfg_get(["ocr", "ocrmypdf", "timeout_sec"], 120)
    try:
        return int(val)
    except Exception:
        return 120

def _ocr_cache_dir() -> Path:
    d = _cfg_get(["ocr", "cache_dir"], ".ocr_cache")
    p = Path(d)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[2] / d
    p.mkdir(parents=True, exist_ok=True)
    return p

def _hash_for_file(pdf_path: str) -> str:
    st = os.stat(pdf_path)
    h = hashlib.sha256()
    h.update(str(Path(pdf_path).resolve()).encode("utf-8", "ignore"))
    h.update(str(st.st_mtime_ns).encode())
    h.update(str(st.st_size).encode())
    return h.hexdigest()[:24]

def _run_ocrmypdf(pdf_path: str) -> Optional[str]:
    """Genera un PDF OCR en cache y devuelve su ruta; None si falla."""
    # Respetar enable
    if not _cfg_get(["ocr", "ocrmypdf", "enable"], False):
        return None

    cache_dir = _ocr_cache_dir()
    key = _hash_for_file(pdf_path)
    out_pdf = cache_dir / f"{key}.ocr.pdf"
    if out_pdf.exists() and out_pdf.stat().st_size > 0:
        return str(out_pdf)

    # Construir comando: usamos python -m ocrmypdf para evitar PATH raros
    cmd = [sys.executable, "-m", "ocrmypdf"]
    cmd += _ocrmypdf_flags_from_cfg()
    jobs = _ocrmypdf_jobs_from_cfg()
    if jobs and jobs > 0:
        cmd += ["--jobs", str(jobs)]
    cmd += ["--quiet"]
    cmd += [pdf_path, str(out_pdf)]

    # Preparar env con Tesseract en PATH si est? configurado
    env = os.environ.copy()
    tess_dir = _tesseract_dir_from_cfg()
    if tess_dir:
        env["PATH"] = tess_dir + os.pathsep + env.get("PATH", "")

    timeout = _ocrmypdf_timeout_from_cfg()
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
        if res.returncode == 0 and out_pdf.exists() and out_pdf.stat().st_size > 0:
            return str(out_pdf)
    except Exception:
        pass
    # si falla, limpiar posible archivo vac?o
    try:
        if out_pdf.exists():
            out_pdf.unlink(missing_ok=True)  # type: ignore
    except Exception:
        pass
    return None

# --- API principal ---
def ocr_pages(doc: fitz.Document, page_indices: List[int], scale: float = 2.0, langs: Optional[List[str]] = None) -> Dict[int, str]:
    """Fallback por p?gina con EasyOCR (mantiene compatibilidad)."""
    if not page_indices:
        return {}
    if langs is None:
        langs = _cfg_get(["ocr", "langs"], ["es", "en"])
    reader = _ensure_easyocr(langs)
    out: Dict[int, str] = {}
    for i in page_indices:
        try:
            pg = doc[i]
            img = _page_to_pil(pg, scale=scale)
            if reader:
                # Evitamos numpy si no est?; EasyOCR requiere np.array:
                import numpy as _np  # type: ignore
                arr = _np.array(img)
                result = reader.readtext(arr, detail=0, paragraph=True)
                txt = "\n".join([r.strip() for r in result if r and r.strip()])
            else:
                txt = ""
            out[i] = txt.strip()
        except Exception:
            out[i] = ""
    return out

def ocrmypdf_pre_ocr_if_needed(pdf_path: str, min_chars_for_native: int = 40) -> Tuple[Optional[str], Dict[str, any]]:
    """
    Si el PDF parece escaneado (o force==true), ejecuta OCRmyPDF y devuelve (path_ocr, meta).
    path_ocr=None si no se us? o fall?.
    """
    cfg = _load_cfg()
    force = bool(cfg.get("ocr", {}).get("force", False))
    used = False
    method = None

    # Revisi?n r?pida de texto nativo
    try:
        with fitz.open(pdf_path) as doc:
            native_chars = 0
            for page in doc:
                t = (page.get_text("text") or "").strip()
                native_chars += len(t)
            looks_scanned = native_chars < min_chars_for_native
    except Exception:
        looks_scanned = True

    if force or looks_scanned:
        ocr_pdf = _run_ocrmypdf(pdf_path)
        if ocr_pdf:
            used = True
            method = "ocrmypdf"
            return ocr_pdf, {"used": used, "method": method}
    return None, {"used": used, "method": method}
