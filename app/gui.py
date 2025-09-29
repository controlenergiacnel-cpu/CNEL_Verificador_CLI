import os, queue, webbrowser
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from .cli import load_config
from .core.ocr_engine import OcrConfig, configure_tesseract
from .core.pdf_text import extract_text_from_pdf_or_image
from .core.signatures_robust import verify_pdf_signatures_deep
from .core.energy import extract_energy_values
from .core.patterns import extract_basic_patterns
from .core.director import find_director_mentions
from .core.reporter import write_reports
from .core.utils import file_sha256

def process_folder(folder: str, progress_cb=None, no_ocr=False):
    cfg = load_config()
    ocr_cfg = OcrConfig(**cfg.get('ocr',{}))
    if no_ocr: ocr_cfg.enabled = False
    try: configure_tesseract(ocr_cfg.tesseract_bin)
    except Exception: pass

    files = []
    for root,_,fns in os.walk(folder):
        for fn in fns:
            if fn.lower().endswith(('.pdf','.png','.jpg','.jpeg','.tif','.tiff')):
                files.append(os.path.join(root, fn))
    files.sort()

    results = []
    total = len(files) or 1
    for i, fpath in enumerate(files, 1):
        if progress_cb: progress_cb(i, total, fpath)
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
            try: rec['signature'] = verify_pdf_signatures_deep(fpath, cfg.get('validation',{}))
            except Exception as e: rec['signature'] = {'status_overall':'ERROR','signatures':[],'details':str(e)}
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
    return os.path.abspath(os.path.join('outputs','reporte_bonito.html'))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CNEL_Verificador â€” GUI')
        self.geometry('720x340')
        self.configure(padx=14, pady=14)
        self.folder = tk.StringVar()
        self.no_ocr = tk.BooleanVar(value=False)
        tk.Label(self, text='Carpeta de documentos:').grid(row=0, column=0, sticky='w')
        tk.Entry(self, textvariable=self.folder, width=68).grid(row=1, column=0, columnspan=2, sticky='we')
        tk.Button(self, text='Buscar...', command=self.browse).grid(row=1, column=2, padx=6)
        tk.Checkbutton(self, text='Desactivar OCR (solo PDF con texto)', variable=self.no_ocr).grid(row=2, column=0, sticky='w', pady=(6,6))
        self.btn = tk.Button(self, text='Procesar', command=self.run); self.btn.grid(row=3, column=0, pady=8, sticky='w')
        self.pb = ttk.Progressbar(self, orient='horizontal', mode='determinate', length=520); self.pb.grid(row=4, column=0, columnspan=3, pady=10, sticky='we')
        self.status = tk.Label(self, text='', anchor='w'); self.status.grid(row=5, column=0, columnspan=3, sticky='we')
        for i in range(3): self.grid_columnconfigure(i, weight=1)

    def browse(self):
        d = filedialog.askdirectory()
        if d: self.folder.set(d)

    def run(self):
        folder = self.folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror('Error', 'Selecciona una carpeta vÃ¡lida.'); return
        q = queue.Queue()
        def progress_cb(i,total,path): q.put(('progress',i,total,path))
        def worker():
            try:
                out_html = process_folder(folder, progress_cb=progress_cb, no_ocr=self.no_ocr.get())
                q.put(('done', out_html))
            except Exception as e:
                q.put(('error', str(e)))
        import threading
        threading.Thread(target=worker, daemon=True).start()
        self.after(100, lambda: self.poll(q))

    def poll(self, q):
        try:
            while True:
                msg = q.get_nowait()
                if msg[0]=='progress':
                    i,total,path = msg[1],msg[2],msg[3]
                    self.pb['maximum']=total; self.pb['value']=i
                    self.status.config(text=f'Procesando ({i}/{total}): {path}')
                elif msg[0]=='done':
                    out_html = msg[1]
                    self.status.config(text=f'Terminado. Abriendo reporte: {out_html}')
                    try: webbrowser.open(out_html)
                    except Exception: pass
                    return
                elif msg[0]=='error':
                    self.status.config(text=f'Error: {msg[1]}'); return
        except Exception: pass
        self.after(150, lambda: self.poll(q))

def main():
    App().mainloop()

if __name__ == '__main__':
    main()
