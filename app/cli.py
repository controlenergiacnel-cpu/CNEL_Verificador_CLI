# app/core/ocr_engine.py
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# ------------ Config ------------

@dataclass
class OcrConfig:
    enabled: bool = True
    tesseract_bin: Optional[str] = None
    langs: List[str] = None
    min_chars_for_native: int = 80
    raw: Dict[str, Any] = None

    @staticmethod
    def from_config(cfg: Dict[str, Any]) -> "OcrConfig":
        text = cfg.get("text", {}) or {}
        ocr = cfg.get("ocr", {}) or {}
        tess = cfg.get("tesseract", {}) or {}

        force = bool(ocr.get("force", False))
        enable_flag = bool(ocr.get("enable", True))
        enabled = force or enable_flag

        tesseract_bin = tess.get("cmd") or cfg.get("tesseract_bin")

        langs = ocr.get("langs") or cfg.get("ocr_langs")
        if isinstance(langs, str):
            langs = [p for p in langs.replace("+", ",").split(",") if p.strip()]
        if not langs:
            langs = ["es", "en"]
        langs = ["es" if x == "spa" else ("en" if x == "eng" else x) for x in langs]

        min_chars = int(ocr.get("min_chars_for_native", text.get("min_chars_for_native", 80)))

        return OcrConfig(
            enabled=enabled,
            tesseract_bin=tesseract_bin,
            langs=langs,
            min_chars_for_native=min_chars,
            raw=cfg,
        )

def configure_tesseract(tesseract_bin: Optional[str]) -> None:
    """Configura ruta de Tesseract si se especifica."""
    if tesseract_bin and os.path.exists(tesseract_bin):
        pytesseract.pytesseract.tesseract_cmd = tesseract_bin

# ------------ Resultado OCR ------------

@dataclass
class ExtractResult:
    text: str
    is_scanned_hint: bool
    page_text_lengths: List[int]
    ocr_text_lengths: List[int]

# ------------ Utilidades internas ------------

def _pdf_has_native_text(pdf_path: str) -> bool:
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                if page.get_text().strip():
                    return True
    except Exception:
        pass
    return False

def _ocr_image_pil(img: Image.Image, langs: List[str]) -> str:
    lang = "+".join(langs) if langs else "spa+eng"
    return pytesseract.image_to_string(img, lang=lang)

# ------------ API pública usada por cli.py ------------

def extract_text_from_pdf_or_image(path: str, cfg: OcrConfig) -> ExtractResult:
    """
    Lee texto nativo de PDF con PyMuPDF y, si no hay suficiente texto, hace OCR con Tesseract.
    Para imágenes, solo OCR.
    """
    text = ""
    is_scanned_hint = False
    page_lens: List[int] = []
    ocr_lens: List[int] = []

    lower = path.lower()
    if lower.endswith(".pdf"):
        # 1) Texto nativo
        native_text = []
        try:
            with fitz.open(path) as doc:
                for page in doc:
                    t = page.get_text()
                    native_text.append(t or "")
                    page_lens.append(len(t or ""))
        except Exception:
            native_text = []

        text_native_joined = "\n".join(native_text)
        has_native = len(text_native_joined) >= cfg.min_chars_for_native

        # 2) OCR si no hay suficiente texto nativo y OCR está habilitado
        if cfg.enabled and not has_native:
            is_scanned_hint = True
            try:
                with fitz.open(path) as doc:
                    ocr_text_pages = []
                    for page in doc:
                        pix = page.get_pixmap(dpi=200)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        t = _ocr_image_pil(img, cfg.langs)
                        ocr_text_pages.append(t or "")
                        ocr_lens.append(len(t or ""))
                text = "\n".join(ocr_text_pages)
            except Exception:
                # si el OCR falla, al menos devolvemos lo nativo
                text = text_native_joined
        else:
            text = text_native_joined

    else:
        # Imagen: OCR directo si enabled, si no, vacío
        if cfg.enabled:
            try:
                img = Image.open(path)
                text = _ocr_image_pil(img, cfg.langs)
                ocr_lens.append(len(text or ""))
            except Exception:
                text = ""
        else:
            text = ""

    return ExtractResult(
        text=text or "",
        is_scanned_hint=is_scanned_hint,
        page_text_lengths=page_lens,
        ocr_text_lengths=ocr_lens,
    )
