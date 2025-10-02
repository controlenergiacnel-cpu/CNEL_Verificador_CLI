# ... (imports de tu archivo)

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class OcrConfig:
    enabled: bool = True
    tesseract_bin: Optional[str] = None
    langs: Optional[List[str]] = None
    min_chars_for_native: int = 80
    # guardamos el resto por si quieres usarlos luego
    raw: Dict[str, Any] = None

    @staticmethod
    def from_config(cfg: Dict[str, Any]) -> "OcrConfig":
        """
        Soporta tu JSON actual:
        - text.min_chars_for_native
        - ocr.enable / ocr.force
        - ocr.langs
        - tesseract.cmd (ruta binaria)
        - y conserva todo en .raw para futuros usos (ocrmypdf, tiling, etc.)
        """
        text = cfg.get("text", {}) or {}
        ocr  = cfg.get("ocr", {}) or {}
        tess = cfg.get("tesseract", {}) or {}

        # enabled: si hay 'force', manda más que 'enable'
        force = bool(ocr.get("force", False))
        enable_flag = bool(ocr.get("enable", True))
        enabled = force or enable_flag

        tesseract_bin = tess.get("cmd") or cfg.get("tesseract_bin")

        langs = ocr.get("langs") or cfg.get("ocr_langs")
        if isinstance(langs, str):
            # admite "spa+eng" -> ["spa","eng"] o "es,en" -> ["es","en"]
            langs = [p for p in langs.replace('+', ',').split(',') if p.strip()]
        # normaliza idiomas comunes
        if langs and any(x in ("spa","eng") for x in langs):
            langs = ["es" if x=="spa" else ("en" if x=="eng" else x) for x in langs]

        min_chars = int(ocr.get("min_chars_for_native", text.get("min_chars_for_native", 80)))

        return OcrConfig(
            enabled=enabled,
            tesseract_bin=tesseract_bin,
            langs=langs or ["es","en"],
            min_chars_for_native=min_chars,
            raw=cfg
        )
