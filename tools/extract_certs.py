import os, sys, json
from pyhanko.pdf_utils.reader import PdfFileReader
from asn1crypto import x509

pdf = sys.argv[1]
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
with open(pdf, "rb") as fh:
    r = PdfFileReader(fh)
    for i, es in enumerate(r.embedded_signatures, start=1):
        chain = getattr(es, "certs", None) or []
        for j, cert in enumerate(chain, start=1):
            if isinstance(cert, x509.Certificate):
                der = cert.dump()
                open(os.path.join(out, f"sig{i}_cert{j}.cer"), "wb").write(der)
print("Extraídos certs a:", out)
