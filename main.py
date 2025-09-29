#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, json, os, re, datetime as dt
from pathlib import Path
import runpy
from typing import Optional, List
from urllib.parse import urlparse

# ---------- Utilidades ----------
def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True); return p

def latest_subdir(base: Path) -> Optional[Path]:
    if not base.exists(): return None
    subs = [p for p in base.iterdir() if p.is_dir()]
    return max(subs, key=lambda p: p.stat().st_mtime) if subs else None

def find_project_root() -> Path:
    # Compatible con PyInstaller (usa sys._MEIPASS si existe)
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

def tools_path() -> Path:
    # En ejecución normal: <root>/tools ; en empaquetado: se copia igual
    root = Path(__file__).resolve().parent
    return root / "tools"

# ---------- Refresh trust (integrado) ----------
# Implementa la idea de: extraer certs de PDFs y subir por AIA para poblar trust_certs,
# siguiendo la lógica de tus scripts auxiliares (extract_certs / fetch_issuers_from_aia). 
# (Se simplifica y evita dependencias externas.)
# Referencias de tus utilitarios:
# - extract_certs.py: extrae cadena desde PDF. :contentReference[oaicite:2]{index=2}
# - fetch_issuers_from_aia.py: descarga emisores desde AIA/caIssuers. :contentReference[oaicite:3]{index=3}
def refresh_trust_from_src(src: Path, trust_dir: Path) -> None:
    from pyhanko.pdf_utils.reader import PdfFileReader  # local import
    from asn1crypto import x509
    import requests, base64

    ensure_dir(trust_dir)
    seen = set()

    def save_cert(cert: x509.Certificate, hint: str) -> None:
        subj = cert.subject.human_friendly
        fn   = re.sub(r'[^A-Za-z0-9._-]+','_', (hint or subj))[:200] + ".cer"
        path = trust_dir / fn
        der  = cert.dump()
        if der in seen: 
            return
        path.write_bytes(der)
        seen.add(der)

    def get_aia_urls(cert: x509.Certificate) -> List[str]:
        try:
            aia = cert['tbs_certificate']['extensions'].get_extension_for_oid('authority_information_access').native
        except Exception:
            return []
        out=[]
        for d in aia:
            if d.get('access_method') == 'ca_issuers' and 'access_location' in d:
                loc = d['access_location']
                if isinstance(loc, dict) and loc.get('type') == 'uniform_resource_identifier':
                    out.append(loc['value'])
        return out

    def download_cert(url: str) -> Optional[x509.Certificate]:
        try:
            r = requests.get(url, timeout=20, allow_redirects=True)
            r.raise_for_status()
            data = r.content
            try:
                return x509.Certificate.load(data)
            except Exception:
                # intentar PEM simple
                m = re.findall(rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", data, re.S)
                if m:
                    der = base64.b64decode(m[0].strip().replace(b'\r', b'').replace(b'\n', b''))
                    return x509.Certificate.load(der)
        except Exception:
            return None
        return None

    def walk_chain_from(cert: x509.Certificate):
        # guarda CA si aplica
        try:
            bc = cert.basic_constraints
            if bc and bool(bc.ca):
                save_cert(cert, "CA__" + cert.subject.native.get('common_name', 'UNKNOWN'))
        except Exception:
            pass
        # AIA → subir a emisores
        for url in get_aia_urls(cert):
            c_up = download_cert(url)
            if not c_up: 
                continue
            save_cert(c_up, "CA__" + c_up.subject.native.get('common_name','UNKNOWN'))

    # Recorrer todos los PDFs y cadenas embebidas
    pdfs = []
    if src.is_file() and src.suffix.lower()==".pdf":
        pdfs=[src]
    else:
        for r,_,fns in os.walk(src):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    pdfs.append(Path(r)/fn)
    for pdf in sorted(pdfs):
        try:
            with open(pdf, "rb") as fh:
                r = PdfFileReader(fh)
                for es in r.embedded_signatures:
                    chain = getattr(es, "certs", None) or []
                    for c in chain:
                        if isinstance(c, x509.Certificate):
                            # End-entity opcional
                            save_cert(c, "EE__" + c.subject.native.get('common_name','UNKNOWN'))
                            # Subir a emisores
                            walk_chain_from(c)
        except Exception as e:
            print(f"[refresh-trust] WARN {pdf.name}: {e}")

# ---------- Scan (llama a tu tools/validate_signs_api.py) ----------
def run_scan(src: Path, trust: Optional[Path], out_base: Path) -> Path:
    script = tools_path() / "validate_signs_api.py"
    if not script.exists():
        raise FileNotFoundError(f"No se encuentra {script}")
    ensure_dir(out_base)

    argv_backup = sys.argv[:]
    try:
        # Simula CLI nativa del validador (manteniendo tu interfaz)
        sys.argv = [str(script), str(src)]
        if trust: sys.argv += ["--trust", str(trust)]
        sys.argv += ["--out", str(out_base)]
        runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv = argv_backup

    # ubica la subcarpeta de timestamp más reciente
    out_dir = latest_subdir(out_base) or out_base
    return out_dir

# ---------- Report ----------
def load_json_if(path: Path) -> Optional[dict]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return None
    return None

def summarize_lote(lote_dir: Path) -> str:
    j_un = load_json_if(lote_dir / "sig_untrusted.json") or {}
    j_tr = load_json_if(lote_dir / "sig_trusted.json") or {}
    base = j_tr if j_tr else j_un
    results = base.get("results", [])
    lines = [f"Lote: {lote_dir.name} | Archivos: {len(results)}"]
    for item in results:
        f = item.get("file", "?")
        sigs = item.get("signatures", [])
        if not sigs:
            errs = item.get("errors") or []
            lines.append(f" - {Path(f).name}: sin firmas o error ({'; '.join(map(str,errs)) if errs else 'N/A'})")
            continue
        ok = sum(1 for s in sigs if s.get("integrity_ok"))
        tr = sum(1 for s in sigs if s.get("trusted"))
        st = sigs[0] if sigs else {}
        # signing_time la llena tu validador (en algunos paths puede ir como datetime serializada) :contentReference[oaicite:4]{index=4}
        lines.append(f" - {Path(f).name}: firmas={len(sigs)} | integridadOK={ok} | confiables={tr} | fecha={st.get('signing_time','N/D')}")
    rep = lote_dir / "reporte_lote.txt"
    lines.append(f"Reporte TXT: {rep}")
    return "\n".join(lines)

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(prog="CNEL_Verificador_CLI", description="Orquestador CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Ejecuta validación sobre una carpeta o PDF")
    p_scan.add_argument("--input", required=True, help="Carpeta o PDF de entrada")
    p_scan.add_argument("--trust", default=None, help="Carpeta de certificados de confianza (opcional)")
    p_scan.add_argument("--out", required=True, help="Carpeta base de reportes")
    p_scan.add_argument("--refresh-trust", action="store_true", help="Intentar poblar/actualizar TRUST a partir de PDFs antes de escanear")

    p_rep = sub.add_parser("report", help="Muestra resumen del último lote (o uno dado)")
    p_rep.add_argument("--out", required=True, help="Carpeta base de reportes")
    p_rep.add_argument("--lote", default=None, help="Nombre de subcarpeta timestamp (opcional)")

    args = ap.parse_args()

    if args.cmd == "scan":
        src  = Path(args.input).resolve()
        trust= Path(args.trust).resolve() if args.trust else None
        outb = Path(args.out).resolve()

        if args.refresh_trust and trust:
            print(f"[i] Actualizando TRUST desde {src} → {trust} ...")
            refresh_trust_from_src(src, trust)  # usa lógica basada en tus scripts auxiliares :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6}
            print("[i] TRUST actualizado.")

        out_dir = run_scan(src, trust, outb)  # llama a tools/validate_signs_api.py (tu núcleo) :contentReference[oaicite:7]{index=7}
        print("✅ Escaneo completado")
        print(summarize_lote(out_dir))
        return

    if args.cmd == "report":
        outb = Path(args.out).resolve()
        lote = Path(args.lote) if args.lote else latest_subdir(outb)
        if not lote or not lote.exists():
            print("No hay lotes en OUT aún."); sys.exit(1)
        print(summarize_lote(lote))
        return

if __name__ == "__main__":
    main()
