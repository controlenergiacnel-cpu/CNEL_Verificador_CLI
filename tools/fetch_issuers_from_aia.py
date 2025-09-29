# tools/fetch_issuers_from_aia.py
# Descarga emisores/CA siguiendo AIA desde los certificados de los PDFs.
# Uso:
#   python tools\fetch_issuers_from_aia.py --src "C:\carpeta\pdfs" --trust ".\trust_certs"
import os, re, base64, argparse, requests
from asn1crypto import x509
from pyhanko.pdf_utils.reader import PdfFileReader

def save_cert(cert: x509.Certificate, trust_dir: str, label_hint: str = "") -> str:
    os.makedirs(trust_dir, exist_ok=True)
    subj = cert.subject.human_friendly
    fn   = re.sub(r'[^A-Za-z0-9._-]+', '_', (label_hint or subj))[:200] + ".cer"
    path = os.path.join(trust_dir, fn)
    der  = cert.dump()
    if os.path.exists(path) and open(path, "rb").read() == der:
        return path
    with open(path, "wb") as f:
        f.write(der)
    return path

def get_aia_urls(cert: x509.Certificate):
    try:
        aia = cert['tbs_certificate']['extensions'].get_extension_for_oid('authority_information_access').native
    except Exception:
        return []
    urls = []
    for d in aia:
        if d.get('access_method') == 'ca_issuers' and 'access_location' in d:
            loc = d['access_location']
            if isinstance(loc, dict) and loc.get('type') == 'uniform_resource_identifier':
                urls.append(loc['value'])
    return urls

def download_cert(url: str):
    try:
        r = requests.get(url, timeout=20, allow_redirects=True)
        r.raise_for_status()
        data = r.content
        # DER → x509
        try:
            return x509.Certificate.load(data)
        except Exception:
            # PEM
            pem = re.findall(rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", data, re.S)
            if pem:
                block = pem[0].strip().replace(b'\r', b'').replace(b'\n', b'')
                der = base64.b64decode(block)
                return x509.Certificate.load(der)
    except Exception:
        pass
    return None

def is_self_issued(cert: x509.Certificate) -> bool:
    try:
        return cert.issuer == cert.subject
    except Exception:
        return False

def walk_chain_from(cert: x509.Certificate, trust_dir: str, visited_fps: set):
    # Guarda CA si aplica
    try:
        is_ca = bool(cert.basic_constraints.ca)
    except Exception:
        is_ca = False
    if is_ca:
        save_cert(cert, trust_dir, "CA__" + (cert.subject.native.get('common_name','UNKNOWN') or 'UNKNOWN'))
    # Sube por AIA
    for url in get_aia_urls(cert):
        up = download_cert(url)
        if not up: 
            continue
        fp = up.fingerprint  # bytes
        if fp in visited_fps:
            continue
        visited_fps.add(fp)
        save_cert(up, trust_dir, "CA__" + (up.subject.native.get('common_name','UNKNOWN') or 'UNKNOWN'))
        if not is_self_issued(up):
            walk_chain_from(up, trust_dir, visited_fps)

def process_pdf(pdf_path: str, trust_dir: str, stats: dict):
    try:
        with open(pdf_path, "rb") as fh:
            r = PdfFileReader(fh, strict=False)
            for es in r.embedded_signatures:
                chain = getattr(es, "certs", None) or []
                visited_fps = set()
                for c in chain:
                    if isinstance(c, x509.Certificate):
                        save_cert(c, trust_dir, "EE__" + (c.subject.native.get('common_name','UNKNOWN') or 'UNKNOWN'))
                        walk_chain_from(c, trust_dir, visited_fps)
                        stats["end_entities"] += 1
    except Exception as e:
        stats["errors"] += 1
        print(f"[WARN] {os.path.basename(pdf_path)}: {e}")

def main():
    ap = argparse.ArgumentParser(description="Descarga emisores/CA siguiendo AIA desde PDFs firmados.")
    ap.add_argument("--src", required=True, help="Carpeta o PDF")
    ap.add_argument("--trust", required=True, help="Carpeta destino de confianza (se crearán .cer)")
    args = ap.parse_args()

    src   = os.path.abspath(args.src)
    trust = os.path.abspath(args.trust)
    os.makedirs(trust, exist_ok=True)

    files = []
    if os.path.isfile(src) and src.lower().endswith(".pdf"):
        files = [src]
    else:
        for r,_,fns in os.walk(src):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    files.append(os.path.join(r, fn))

    stats = {"end_entities": 0, "errors": 0}
    for f in files:
        process_pdf(f, trust, stats)

    print(f"OK. Procesados: {len(files)} PDFs | EE: {stats['end_entities']} | errores: {stats['errors']}")
    print(f"Emisores/CA guardados en: {trust}")

if __name__ == "__main__":
    main()
