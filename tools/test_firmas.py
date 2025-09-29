from __future__ import annotations
import sys, os, json, binascii
from typing import List, Dict, Any
import pikepdf

try:
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
except Exception:
    load_der_pkcs7_certificates = None

def _bytes_from(obj):
    try:
        return bytes(obj)
    except Exception:
        if isinstance(obj, str):
            try:
                return binascii.unhexlify(obj)
            except Exception:
                return obj.encode("latin-1", "ignore")
        return b""

def _cn_only(name):
    try:
        # CN OID = 2.5.4.3
        parts = [a.value for a in name if getattr(a, "oid", None) and a.oid.dotted_string == "2.5.4.3"]
        return parts[0] if parts else name.rfc4514_string()
    except Exception:
        return str(name)

def list_signatures(pdf_path: str) -> List[Dict[str, Any]]:
    sig_dicts = []
    with pikepdf.open(pdf_path) as pdf:
        root = getattr(pdf, "Root", None) or getattr(pdf, "root", None)
        if root:
            acro = root.get("/AcroForm", None)
            if acro:
                fields = acro.get("/Fields", []) or []
                stack = list(fields)
                seen = set()
                while stack:
                    ref = stack.pop()
                    try:
                        obj = ref.get_object()
                    except Exception:
                        continue
                    og = getattr(obj, "objgen", None)
                    if og in seen:
                        continue
                    if og is not None:
                        seen.add(og)
                    kids = obj.get("/Kids", None)
                    if kids:
                        stack.extend(kids)
                    if obj.get("/FT", None) == "/Sig":
                        v = obj.get("/V", None)
                        if v is not None:
                            sig_dicts.append(v.get_object())
        # Fallback: escáner de objetos
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Dictionary):
                if (obj.get("/Type", None) == "/Sig") or (obj.get("/Contents", None) is not None and obj.get("/ByteRange", None) is not None):
                    sig_dicts.append(obj)

    out = []
    for s in sig_dicts:
        item = {
            "name":        str(s.get("/Name", "")) if s.get("/Name", None) is not None else None,
            "time":        str(s.get("/M", "")) if s.get("/M", None) is not None else None,
            "subfilter":   str(s.get("/SubFilter", "")) if s.get("/SubFilter", None) is not None else None,
            "issuer":      None,
            "subject":     None,
            "serial":      None,
            "has_bytes":   bool(s.get("/Contents", None)),
            "has_byterange": bool(s.get("/ByteRange", None)),
        }
        if load_der_pkcs7_certificates and s.get("/Contents", None) is not None:
            try:
                contents = _bytes_from(s.get("/Contents"))
                certs = load_der_pkcs7_certificates(contents)
                chosen = None
                for c in certs:
                    try:
                        bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
                        if not bc.ca:
                            chosen = c
                            break
                    except Exception:
                        pass
                if chosen is None and certs:
                    chosen = certs[0]
                if chosen:
                    item["issuer"]  = _cn_only(chosen.issuer)
                    item["subject"] = _cn_only(chosen.subject)
                    item["serial"]  = format(chosen.serial_number, "X")
            except Exception:
                pass
        out.append(item)
    return out

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.test_firmas <archivo.pdf|carpeta>")
        raise SystemExit(1)
    target = sys.argv[1]
    files = []
    if os.path.isdir(target):
        for r, d, fns in os.walk(target):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    files.append(os.path.join(r, fn))
    else:
        files = [target]
    results = []
    for f in files:
        try:
            sigs = list_signatures(f)
            results.append({"file": f, "count": len(sigs), "signatures": sigs})
        except Exception as e:
            results.append({"file": f, "error": str(e)})
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
