# CNEL_Verificador_CLI

Sistema CLI/GUI para CNEL EP que:
- Valida firmas electrónicas en PDF (PDFBox/BouncyCastle).
- Extrae texto y datos con OCR (PyMuPDF, Tesseract, EasyOCR fallback).
- Detecta nombres, fechas, cédulas, valores energéticos.
- Empaquetado como `.exe` (PyInstaller) e instalador (Inno Setup).

## Requisitos
- Python 3.11+ (recomendado 3.12/3.13)
- Tesseract OCR instalado (si aplica)
- Java Runtime (para módulo PDFBox)

## Uso rápido
```bash
python -m app.cli --input "C:\ruta\documentos"
