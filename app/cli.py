import os, sys, json, argparse, glob
from loguru import logger
from .core.ocr_engine import OcrConfig, configure_tesseract
from .core.pdf_text import extract_text_from_pdf_or_image
from .core.signatures_robust import verify_pdf_signatures_deep
from .core.energy import extract_energy_values
from .core.patterns import extract_basic_patterns
from .core.director import find_director_mentions
from .core.reporter import write_reports
from .core.utils import file_sha256

def load_config(cfg_path='config/config.json'):
    with open(cfg_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def gather_inputs(path: str):
    if os.path.isdir(path):
        files = sorted([p for p in glob.glob(os.path.join(path, '**', '*.*'), recursive=True)
                        if p.lower().endswith(('.pdf','.png','.jpg','.jpeg','.tif','.tiff'))])
        return files
    return [path]

def main():
    ap = argparse.ArgumentParser(description='CNEL_Verificador CLI')
    ap.add_argument('--input', required=True, help='Carpeta o archivo a procesar')
    ap.add_argument('--no-ocr', action='store_true', help='Desactivar OCR (solo texto nativo PDF)')
    args = ap.parse_args()

    cfg = load_config()
    ocr_cfg = OcrConfig(**cfg.get('ocr',{}))
    if args.no_ocr: ocr_cfg.enabled = False

    try: configure_tesseract(ocr_cfg.tesseract_bin)
    except Exception as e: logger.warning(f'No se pudo configurar Tesseract: {e}')

    files = gather_inputs(args.input)
    if not files:
        logger.error('No se encontraron archivos admitidos en la ruta de entrada.')
        sys.exit(2)

    results = []
    for i, fpath in enumerate(files, 1):
        logger.info(f'Procesando ({i}/{len(files)}): {fpath}')
        rec = {'file_name': os.path.basename(fpath), 'file_path': fpath, 'sha256': file_sha256(fpath)}
        try:
            ex = extract_text_from_pdf_or_image(fpath, ocr_cfg)
            text = ex.text or ''
            rec['is_scanned_hint'] = ex.is_scanned_hint
            rec['page_text_lengths'] = ex.page_text_lengths
            rec['ocr_text_lengths'] = ex.ocr_text_lengths
        except Exception as e:
            text = ''
            rec['text_error'] = f'Error extrayendo texto: {e}'

        if fpath.lower().endswith('.pdf'):
            try:
                rec['signature'] = verify_pdf_signatures_deep(fpath, cfg.get('validation',{}))
            except Exception as e:
                rec['signature'] = {'status_overall':'ERROR','signatures':[],'details':str(e)}
        else:
            rec['signature'] = {'status_overall':'N/A','signatures':[],'details':'No es PDF'}

        try: rec['energy'] = extract_energy_values(text)
        except Exception as e: rec['energy'] = {'error': str(e)}

        try: rec['patterns'] = extract_basic_patterns(text, region_code='EC')
        except Exception as e: rec['patterns'] = {'error': str(e)}

        try:
            director = cfg.get('director_comercial','')
            aliases = cfg.get('director_aliases',[])
            rec['director'] = find_director_mentions(text, director, aliases)
        except Exception as e:
            rec['director'] = {'error': str(e)}

        results.append(rec)

    write_reports(results, outdir='outputs')
    logger.info('Listo. Revisa outputs/reporte_bonito.html | .txt | .md | resumen.txt')

if __name__ == '__main__':
    main()
