from __future__ import annotations
import sys, json
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject, NameObject

def _name_of(v):
    try:
        if isinstance(v, NameObject):
            return str(v)
        return str(v)
    except Exception:
        return None

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.dump_sigscan <archivo.pdf>")
        raise SystemExit(1)
    path = sys.argv[1]
    r = PdfReader(path)
    out = []
    seen = set()

    def rec(x):
        if isinstance(x, IndirectObject):
            key = (x.generation, x.idnum)
            if key in seen:
                return
            seen.add(key)
            try:
                x = x.get_object()
            except Exception:
                return
        if isinstance(x, DictionaryObject):
            keys = set(map(str, x.keys()))
            has_contents = "/Contents" in keys
            has_byterange = "/ByteRange" in keys
            is_sig = ("/Type" in keys and _name_of(x.get("/Type")) == "/Sig") or (has_contents and has_byterange)
            if is_sig:
                out.append({
                    "xref": getattr(x, "idnum", None),
                    "keys": sorted(list(keys)),
                    "subfilter": str(x.get("/SubFilter", "")),
                    "has_contents": has_contents,
                    "has_byterange": has_byterange,
                    "M": str(x.get("/M", "")),
                    "Reason": str(x.get("/Reason", "")),
                    "Location": str(x.get("/Location", "")),
                })
            for k, v in x.items():
                rec(v)
        elif isinstance(x, ArrayObject):
            for v in x:
                rec(v)

    rec(r.trailer)
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
