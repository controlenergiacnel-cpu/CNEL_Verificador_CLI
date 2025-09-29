from __future__ import annotations
import datetime as _dt
import re
from typing import List, Dict, Any, Optional, Set, Tuple

from pypdf import PdfReader
from pypdf.generic import (
    DictionaryObject, ArrayObject, IndirectObject, ByteStringObject,
    NameObject, DecodedStreamObject, StreamObject,
)

HEX_RE = re.compile(r"^[0-9A-Fa-f\s><]+$")

def _name_of(v) -> Optional[str]:
    try:
        if isinstance(v, NameObject):
            return str(v)
        return str(v)
    except Exception:
        return None

def _as_str(v) -> Optional[str]:
    try:
        if v is None:
            return None
        if isinstance(v, (str, int, float)):
            return str(v)
        if isinstance(v, NameObject):
            return str(v)
        if isinstance(v, ByteStringObject):
            return bytes(v).decode("latin-1", errors="ignore")
        return str(v)
    except Exception:
        return None

def _maybe_hex_to_bytes(s: str) -> Optional[bytes]:
    try:
        txt = s.strip()
        if txt.startswith("<") and txt.endswith(">"):
            txt = txt[1:-1].strip()
        if HEX_RE.match(txt):
            txt = re.sub(r"[^0-9A-Fa-f]", "", txt)
            if len(txt) % 2 == 1:
                txt += "0"
            return bytes.fromhex(txt)
    except Exception:
        pass
    return None

def _get_bytes(contents) -> Optional[bytes]:
    try:
        if contents is None:
            return None
        if isinstance(contents, ByteStringObject):
            return bytes(contents)
        if isinstance(contents, (DecodedStreamObject, StreamObject)):
            return contents.get_data()
        if isinstance(contents, (bytes, bytearray)):
            return bytes(contents)
        s = _as_str(contents)
        if s is not None:
            b = _maybe_hex_to_bytes(s)
            if b is not None:
                return b
            return s.encode("latin-1", errors="ignore")
    except Exception:
        pass
    return None

# --- PDF date to ISO utility ---
_PDF_DATE_RE = re.compile(r"^D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz]|[+\-]\d{2}'?\d{2}'?)?$")
def _pdf_date_to_iso(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    m = _PDF_DATE_RE.match(s)
    if not m:
        return None
    y = int(m.group(1)); mo = int(m.group(2) or "1"); d = int(m.group(3) or "1")
    hh = int(m.group(4) or "0"); mm = int(m.group(5) or "0"); ss = int(m.group(6) or "0")
    tz = m.group(7)
    try:
        if tz is None:
            dt = _dt.datetime(y, mo, d, hh, mm, ss)
            return dt.isoformat()
        if tz.upper() == "Z":
            dt = _dt.datetime(y, mo, d, hh, mm, ss, tzinfo=_dt.timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        tz = tz.replace("'", "")
        sign = 1 if tz[0] == "+" else -1
        th = int(tz[1:3]); tm = int(tz[3:5])
        offset = _dt.timedelta(hours=th, minutes=tm) * sign
        dt = _dt.datetime(y, mo, d, hh, mm, ss, tzinfo=_dt.timezone(offset))
        return dt.isoformat()
    except Exception:
        return None

# --- ASN.1 helpers ---
def _cn_from_asn1_name(name_obj) -> Optional[str]:
    try:
        for r in name_obj.chosen:
            for atv in r:
                if atv["type"].native == "common_name":
                    return atv["value"].native
    except Exception:
        pass
    return None

def _dn_string(name_obj) -> Optional[str]:
    try:
        parts = []
        for r in name_obj.chosen:
            for atv in r:
                n = atv["type"].native
                v = atv["value"].native
                parts.append("{}={}".format(n, v))
        return ", ".join(parts) if parts else None
    except Exception:
        return None

def _parse_pkcs7_info(pkcs7_bytes: bytes) -> Dict[str, Optional[str]]:
    info = {
        "signer_cn": None,
        "issuer_cn": None,
        "signing_time": None,
        "sid_issuer_dn": None,
        "sid_serial_hex": None,
    }
    if not pkcs7_bytes:
        return info
    pkcs7_bytes = pkcs7_bytes.strip(b"\x00")
    try:
        from asn1crypto import cms, x509
        content = cms.ContentInfo.load(pkcs7_bytes)
        if content["content_type"].native != "signed_data":
            return info
        sd = content["content"]

        certs = []
        if sd["certificates"] is not None:
            for c in sd["certificates"]:
                if isinstance(c.chosen, x509.Certificate):
                    certs.append(c.chosen)

        for si in sd["signer_infos"]:
            # signing_time
            try:
                for attr in si["signed_attrs"]:
                    # por nombre
                    if attr["type"].native == "signing_time":
                        t = attr["values"][0].native
                        if isinstance(t, _dt.datetime):
                            info["signing_time"] = t.isoformat()
                        else:
                            info["signing_time"] = str(t)
                    # intento de ESSCertID/ESSCertIDv2
                    if attr["type"].native in ("signing_certificate", "signing_certificate_v2") or \
                       getattr(attr["type"], "dotted", "") in ("1.2.840.113549.1.9.16.2.12", "1.2.840.113549.1.9.16.2.47"):
                        try:
                            data = attr["values"][0]
                            dn = None; serial_hex = None
                            try:
                                nat = data.native
                                # v1
                                if "certs" in nat and nat["certs"]:
                                    c0 = nat["certs"][0]
                                    iss = c0.get("issuer_serial", {}).get("issuer")
                                    serial = c0.get("issuer_serial", {}).get("serial_number")
                                    if iss:
                                        dn = ", ".join(["{}={}".format(k, v) for k, v in iss[0].items()])
                                    if serial is not None:
                                        serial_hex = format(int(serial), "X") if isinstance(serial, int) else str(serial)
                            except Exception:
                                pass
                            if dn and not info["sid_issuer_dn"]:
                                info["sid_issuer_dn"] = dn
                            if serial_hex and not info["sid_serial_hex"]:
                                info["sid_serial_hex"] = serial_hex
                        except Exception:
                            pass
            except Exception:
                pass

            signer_cert = None
            sid = si["sid"]

            if sid.name == "issuer_and_serial_number":
                iasn = sid.chosen
                try:
                    info["sid_issuer_dn"] = info["sid_issuer_dn"] or _dn_string(iasn["issuer"])
                    cn_from_sid = _cn_from_asn1_name(iasn["issuer"])
                    if cn_from_sid and not info["issuer_cn"]:
                        info["issuer_cn"] = cn_from_sid
                except Exception:
                    pass
                try:
                    serial = iasn["serial_number"].native
                    info["sid_serial_hex"] = info["sid_serial_hex"] or (format(serial, "X") if isinstance(serial, int) else str(serial))
                except Exception:
                    pass
                for c in certs:
                    try:
                        if (c.issuer == iasn["issuer"].chosen
                            and c.serial_number == iasn["serial_number"].native):
                            signer_cert = c
                            break
                    except Exception:
                        continue

            elif sid.name == "subject_key_identifier":
                skid = sid.native
                for c in certs:
                    if c.key_identifier == skid:
                        signer_cert = c
                        break

            if signer_cert:
                try:
                    subj_cn = _cn_from_asn1_name(signer_cert.subject)
                    issuer_cn = _cn_from_asn1_name(signer_cert.issuer)
                    if subj_cn:
                        info["signer_cn"] = subj_cn
                    if issuer_cn and not info["issuer_cn"]:
                        info["issuer_cn"] = issuer_cn
                except Exception:
                    pass

            if info["issuer_cn"] or info["sid_issuer_dn"] or info["signer_cn"]:
                break

    except Exception:
        pass
    return info

def _append_unique(out: List[Dict[str, Any]], rec: Dict[str, Any]) -> None:
    for r in out:
        if r.get("xref") == rec.get("xref") and r.get("subfilter") == rec.get("subfilter"):
            return
    out.append(rec)

# --- Appearance text via PyMuPDF (best-effort) ---
def _appearance_texts(pdf_path: str) -> List[str]:
    texts: List[str] = []
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            for page in doc:
                try:
                    widgets = page.widgets()
                except Exception:
                    widgets = None
                if not widgets:
                    continue
                for w in widgets:
                    try:
                        rect = getattr(w, "rect", None)
                        if rect is None:
                            continue
                        # un peque?o padding para captar textos cercanos
                        pad = 6
                        R = fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)
                        t = page.get_textbox(R) or ""
                        t = t.strip()
                        if t:
                            texts.append(t)
                    except Exception:
                        continue
    except Exception:
        pass
    return texts

# --- Full text name guess (por si no hay sello visible) ---
_NAME_PATTERNS = [
    re.compile(r"(?i)firmado(?:\s+electr[o?]nicamente)?\s+por[:\s]*([A-Z??????][A-Za-z??????\.\- ]{2,})"),
    re.compile(r"(?i)signed\s+by[:\s]*([A-Z][A-Za-z\.\- ]{2,})"),
    re.compile(r"(?i)suscrito\s+por[:\s]*([A-Z??????][A-Za-z??????\.\- ]{2,})"),
]

def _guess_name_from_text(s: str) -> Optional[str]:
    for pat in _NAME_PATTERNS:
        m = pat.search(s)
        if m:
            g = m.group(1).strip(" .-")
            return g.strip()
    return None

def _fulltext_name_guess(pdf_path: str) -> Optional[str]:
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            for page in doc:
                t = (page.get_text("text") or "").strip()
                if not t:
                    continue
                g = _guess_name_from_text(t)
                if g:
                    return g
    except Exception:
        pass
    return None

def extract_signatures(pdf_path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        reader = PdfReader(pdf_path)
    except Exception:
        return out

    seen: Set[Tuple[int, int]] = set()
    ap_texts = _appearance_texts(pdf_path)  # may be empty
    global_guess = _fulltext_name_guess(pdf_path)  # puede ser None

    def _emit_from_dict(sobj: DictionaryObject, status_hint: str):
        subfilter = _name_of(sobj.get("/SubFilter"))
        reason = _as_str(sobj.get("/Reason"))
        location = _as_str(sobj.get("/Location"))
        mdate_raw = _as_str(sobj.get("/M"))
        mdate_iso = _pdf_date_to_iso(mdate_raw) if mdate_raw else None
        name_hint = _as_str(sobj.get("/Name"))
        contact_info = _as_str(sobj.get("/ContactInfo"))
        pkcs7 = sobj.get("/Contents")

        signer_cn = issuer_cn = signing_time = None
        sid_issuer_dn = sid_serial_hex = None

        raw = _get_bytes(pkcs7)
        info = None
        if raw:
            info = _parse_pkcs7_info(raw)
            signer_cn = info.get("signer_cn")
            issuer_cn = info.get("issuer_cn")
            signing_time = info.get("signing_time") or mdate_iso or mdate_raw
            sid_issuer_dn = info.get("sid_issuer_dn")
            sid_serial_hex = info.get("sid_serial_hex")

        appearance_text = ap_texts[0] if ap_texts else None
        signer_guess = _guess_name_from_text(appearance_text) if appearance_text else None
        if not signer_guess:
            signer_guess = global_guess

        # signer_display: best available
        signer_display = signer_cn or signer_guess or name_hint or issuer_cn
        if not signer_display and (sid_serial_hex or sid_issuer_dn):
            signer_display = "{}@{}".format(sid_serial_hex or "serial", issuer_cn or sid_issuer_dn or "issuer")

        rec = {
            "xref": getattr(sobj, "idnum", None),
            "status": "timestamp" if (subfilter and isinstance(subfilter, str) and "timestamp" in subfilter.lower()) else status_hint,
            "subfilter": subfilter,
            "reason": reason,
            "location": location,
            "signing_time": signing_time,
            "signing_time_iso": (info.get("signing_time") if (info and info.get("signing_time")) else mdate_iso),
            "signer_cn": signer_cn,
            "issuer_cn": issuer_cn,
            "sid_issuer_dn": sid_issuer_dn,
            "sid_serial_hex": sid_serial_hex,
            "name_hint": name_hint,
            "contact_info": contact_info,
            "appearance_text": appearance_text,
            "signer_guess": signer_guess,
            "signer_display": signer_display,
        }
        _append_unique(out, rec)

    # 1) AcroForm
    try:
        root = reader.trailer["/Root"]
        acro = root.get_object().get("/AcroForm")
        if acro:
            fields = acro.get_object().get("/Fields", [])
            for f in fields:
                try:
                    fobj = f.get_object()
                    if fobj.get("/FT") == NameObject("/Sig"):
                        sig = fobj.get("/V")
                        if not sig:
                            continue
                        sobj = sig.get_object()
                        _emit_from_dict(sobj, "signed")
                except Exception:
                    continue
    except Exception:
        pass

    # 2) DocMDP
    try:
        root_obj = reader.trailer["/Root"].get_object()
        perms = root_obj.get("/Perms")
        if perms:
            docmdp = perms.get_object().get("/DocMDP")
            if docmdp:
                s = docmdp.get_object()
                _emit_from_dict(s, "certification")
    except Exception:
        pass

    # 3) Deep scan
    def _walk(obj, reader: PdfReader, seen: Set[Tuple[int, int]]) -> List[DictionaryObject]:
        found: List[DictionaryObject] = []
        def _recurse(x):
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
                is_sig = ("/Type" in keys and _name_of(x.get("/Type")) == "/Sig") \
                         or ("/ByteRange" in keys and "/Contents" in keys)
                if is_sig:
                    found.append(x)
                for _, v in x.items():
                    _recurse(v)
            elif isinstance(x, ArrayObject):
                for v in x:
                    _recurse(v)
        try:
            _recurse(reader.trailer)
        except Exception:
            pass
        return found

    try:
        candidates = _walk(reader, reader, seen)
        for o in candidates:
            try:
                _emit_from_dict(o, "signed")
            except Exception:
                continue
    except Exception:
        pass

    # 4) DSS flag
    try:
        root_obj = reader.trailer["/Root"].get_object()
        if root_obj.get("/DSS") is not None:
            _append_unique(out, {
                "xref": None,
                "status": "dss-present",
                "subfilter": None,
                "reason": None,
                "location": None,
                "signing_time": None,
                "signing_time_iso": None,
                "signer_cn": None,
                "issuer_cn": None,
                "sid_issuer_dn": None,
                "sid_serial_hex": None,
                "name_hint": None,
                "contact_info": None,
                "appearance_text": None,
                "signer_guess": None,
                "signer_display": None,
            })
    except Exception:
        pass

    return out

if __name__ == "__main__":
    import json, sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Uso: python -m app.core.signatures_robust <archivo.pdf>")
        raise SystemExit(1)
    print(json.dumps(extract_signatures(path), ensure_ascii=False, indent=2))
