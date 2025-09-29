import os
from typing import List
from asn1crypto import x509

def load_trust_roots(trust_dir: str) -> List[x509.Certificate]:
    roots = []
    if not trust_dir or not os.path.isdir(trust_dir):
        return roots
    for fn in os.listdir(trust_dir):
        if not fn.lower().endswith((".pem",".crt",".cer")):
            continue
        p = os.path.join(trust_dir, fn)
        try:
            data = open(p,"rb").read()
            if b"-----BEGIN CERTIFICATE-----" in data:
                cert = x509.Certificate.from_pem(data)
            else:
                cert = x509.Certificate.load(data)
            roots.append(cert)
        except Exception:
            pass
    return roots
