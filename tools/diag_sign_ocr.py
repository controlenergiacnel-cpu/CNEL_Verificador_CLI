import sys
from ..app.core.ocr_engine import OcrConfig, configure_tesseract
from ..app.core.pdf_text import extract_text_from_pdf_or_image
from ..app.core.signatures_robust import verify_pdf_signatures_deep
def main():
    if len(sys.argv)<2:
        print('Uso: python -m tools.diag_sign_ocr archivo.pdf [ruta\\tesseract.exe]')
        sys.exit(1)
    path = sys.argv[1]
    tess = sys.argv[2] if len(sys.argv)>2 else None
    ocr_cfg = OcrConfig(enabled=True, langs='spa+eng', dpi=350, force_all_pages=True, fallback_if_short_chars=160, tesseract_bin=tess)
    configure_tesseract(tess)
    ex = extract_text_from_pdf_or_image(path, ocr_cfg)
    print('TEXTO_NATIVO_LEN/pg:', ex.page_text_lengths)
    print('OCR_LEN/pg:', ex.ocr_text_lengths)
    if path.lower().endswith('.pdf'):
        print('FIRMAS:', verify_pdf_signatures_deep(path, {'trust_dir':'config/trust','allow_fetching':True}))
if __name__ == '__main__':
    main()
