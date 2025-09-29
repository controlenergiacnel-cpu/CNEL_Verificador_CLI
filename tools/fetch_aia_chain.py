import os, sys, re, json, base64, pathlib
import requests
from asn1crypto import x509
from pyhanko.pdf_utils.reader import PdfFileReader

TRUST = r"C:\Users\sidney.guerrero\Desktop\trust_certs"
SRC   = r"C:\Users\sidney.guerrero\Desktop\documentos_prueba"

os.makedirs(TRUST, exist_ok=True)
seen = set()

def save_cert(cert: x509.Certificate, label_hint=""):
    subj = cert.subject.human_friendly
    fn   = re.sub(r'[^A-Za-z0-9._-]+','_', (label_hint or subj))[:200] + ".cer"
    path = os.path.join(TRUST, fn)
    der  = cert.dump()
    if der in seen: 
        return path, False
    with open(path, "wb") as f:
        f.write(der)
    seen.add(der)
    return path, True

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
        # puede venir DER, PEM o PKCS7
        # intentamos DER->x509, si falla, intentamos PEM, si falla intentamos extraer de PKCS7 (muy básico)
        try:
            return x509.Certificate.load(data)
        except Exception:
            pem = re.findall(rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", data, re.S)
            if pem:
                # toma el primero
                block = pem[0].strip().replace(b'\r', b'').replace(b'\n', b'')
                der = base64.b64decode(block)
                return x509.Certificate.load(der)
            # intento básico de PKCS7: buscar bloques de cert dentro
            # (esto es mínimo; si no hay, lo dejamos)
    except Exception:
        return None
    return None

def is_self_issued(cert: x509.Certificate):
    try:
        return cert.issuer == cert.subject
    except Exception:
        return False

def walk_chain_from(cert: x509.Certificate):
    # guarda el cert actual si es CA
    try:
        bc = cert.basic_constraints
        is_ca = bool(bc.ca)
    except Exception:
        is_ca = False
    if is_ca:
        save_cert(cert, "CA__" + cert.subject.native.get('common_name','UNKNOWN'))
    # sigue AIA
    for url in get_aia_urls(cert):
        up = download_cert(url)
        if not up:
            continue
        save_cert(up, "CA__" + up.subject.native.get('common_name','UNKNOWN'))
        if not is_self_issued(up):
            walk_chain_from(up)

def process_pdf(pdf_path: str):
    try:
        with open(pdf_path, "rb") as fh:
            r = PdfFileReader(fh)
            for es in r.embedded_signatures:
                chain = getattr(es, "certs", None) or []
                for c in chain:
                    if isinstance(c, x509.Certificate):
                        # guarda end-entity (opcional)
                        save_cert(c, "EE__" + c.subject.native.get('common_name','UNKNOWN'))
                        # intenta subir por AIA
                        walk_chain_from(c)
    except Exception as e:
        print(f"[WARN] {pdf_path}: {e}")

for root, _, files in os.walk(SRC):
    for f in files:
        if f.lower().endswith(".pdf"):
            process_pdf(os.path.join(root, f))

print(f"OK. Descargados/guardados emisores en: {TRUST}")
