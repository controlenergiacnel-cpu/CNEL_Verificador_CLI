from __future__ import annotations
import sys, json
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DecodedStreamObject, StreamObject, ByteStringObject

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.dump_dss <archivo.pdf>")
        raise SystemExit(1)
    path = sys.argv[1]
    r = PdfReader(path)
    out = []
    try:
        dss = r.trailer["/Root"].get_object().get("/DSS")
        if dss:
            dss = dss.get_object()
            vri = dss.get("/VRI")
            if vri:
                vri = vri.get_object()
                for k, entry in vri.items():
                    e = entry.get_object()
                    certs = e.get("/Cert")
                    items = certs if isinstance(certs, ArrayObject) else [certs] if certs else []
                    out_entry = {"key": str(k), "cert_count": 0}
                    for c in items:
                        try:
                            cstream = c.get_object()
                            if isinstance(cstream, (DecodedStreamObject, StreamObject)):
                                cbytes = cstream.get_data()
                            elif isinstance(cstream, ByteStringObject):
                                cbytes = bytes(cstream)
                            else:
                                continue
                            out_entry["cert_count"] += 1
                        except Exception:
                            continue
                    out.append(out_entry)
    except Exception:
        pass
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
