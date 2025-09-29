from __future__ import annotations
import sys, binascii, json
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, ArrayObject, IndirectObject, NameObject, ByteStringObject, DecodedStreamObject, StreamObject
import re

HEX_RE = re.compile(r"^[0-9A-Fa-f\s><]+$")

def maybe_bytes(v):
    try:
        if isinstance(v, ByteStringObject):
            return bytes(v)
        if isinstance(v, (DecodedStreamObject, StreamObject)):
            return v.get_data()
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
        if isinstance(v, str):
            t = v.strip()
            if t.startswith("<") and t.endswith(">"):
                t = t[1:-1].strip()
            if HEX_RE.match(t):
                t = re.sub(r"[^0-9A-Fa-f]", "", t)
                if len(t) % 2 == 1:
                    t += "0"
                return bytes.fromhex(t)
            return t.encode("latin-1", errors="ignore")
    except Exception:
        pass
    return None

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.peek_pkcs7 <archivo.pdf>")
        sys.exit(1)
    r = PdfReader(sys.argv[1])
    found = []
    seen = set()

    def rec(x):
        if isinstance(x, IndirectObject):
            key = (x.generation, x.idnum)
            if key in seen: return
            seen.add(key)
            try: x = x.get_object()
            except Exception: return
        if isinstance(x, DictionaryObject):
            keys = set(map(str, x.keys()))
            if ("/ByteRange" in keys and "/Contents" in keys) or ("/Type" in keys and str(x.get("/Type")) == "/Sig"):
                found.append(x)
            for _, v in x.items():
                rec(v)
        elif isinstance(x, ArrayObject):
            for v in x: rec(v)

    rec(r.trailer)
    if not found:
        print("[]"); return
    sig = found[0]
    raw = maybe_bytes(sig.get("/Contents"))
    if not raw:
        print(json.dumps({"len": 0, "der_like": False, "head": ""}, indent=2, ensure_ascii=False)); return
    head = binascii.hexlify(raw[:32]).decode()
    out = {"len": len(raw), "der_like": raw[:1] == b"\x30", "head": head}
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
