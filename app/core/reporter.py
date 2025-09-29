import os, json, html
from typing import List, Dict, Any
def _ensure_outputs(outdir: str):
    os.makedirs(outdir, exist_ok=True)
def _safe(obj):
    try: return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception: return str(obj)
def _badge(status: str) -> str:
    if status == 'VALIDA': return 'ok'
    if status == 'INVALIDA': return 'err'
    if status == 'PRESENTE_NO_VALIDADA': return 'warn'
    return ''
def write_reports(results: List[Dict[str, Any]], outdir: str = 'outputs'):
    _ensure_outputs(outdir)
    with open(os.path.join(outdir, 'resumen.txt'), 'w', encoding='utf-8') as jf:
        for r in results: jf.write(json.dumps(r, ensure_ascii=False)+'\n')
    txt_lines = []
    for r in results:
        sig = r.get('signature',{})
        txt_lines.append(f'=== {r.get("file_name","")} ===')
        txt_lines.append(f'SHA256: {r.get("sha256","")}')
        txt_lines.append(f'Firma (global): {sig.get("status_overall")} | {sig.get("details","")}')
        for idx, s in enumerate(sig.get('signatures',[]), 1):
            txt_lines.append(f'  [{idx}] {s.get("status")} | CN: {s.get("signer_cn")} | Issuer: {s.get("issuer_cn")} | Time: {s.get("signing_time")} | TSA: {s.get("timestamp_token")} | Digest: {s.get("digest_algo")}')
        en = r.get('energy',{})
        txt_lines.append(f'EnergÃ­a (kWh): {en.get("summary",{}).get("energy_kwh",[])} | Total kWh: {en.get("totals",{}).get("total_energy_kwh",0)}')
        txt_lines.append(f'Director detectado: {r.get("director",{}).get("found")} | {r.get("director",{}).get("matches")}')
        txt_lines.append(f'Patrones: {r.get("patterns",{})}')
        txt_lines.append('')
    with open(os.path.join(outdir, 'reporte_bonito.txt'), 'w', encoding='cp1252', errors='ignore') as tf:
        tf.write('\n'.join(txt_lines))
    md = ['# Reporte de documentos\n']
    for r in results:
        sig = r.get('signature',{})
        md.append(f'## {r.get("file_name","")}')
        md.append(f'- SHA256: {r.get("sha256","")}')
        md.append(f'- Firma (global): **{sig.get("status_overall")}** â€” {sig.get("details","")}')
        if sig.get('signatures'):
            md.append(f'- Firmas:')
            for idx, s in enumerate(sig['signatures'], 1):
                md.append(f'  - [{idx}] **{s.get("status")}** â€” CN: {s.get("signer_cn")}, Issuer: {s.get("issuer_cn")}, Time: {s.get("signing_time")}, TSA: {s.get("timestamp_token")}, Digest: {s.get("digest_algo")}')
        md.append(f'- EnergÃ­a (kWh): {r.get("energy",{}).get("summary",{}).get("energy_kwh",[])}')
        md.append(f'- Total kWh: {r.get("energy",{}).get("totals",{}).get("total_energy_kwh",0)}')
        md.append(f'- Director: {r.get("director",{}).get("found")}')
        md.append(f'- Patrones: {_safe(r.get("patterns",{}))}  ')
        md.append('')
    with open(os.path.join(outdir, 'reporte_bonito.md'), 'w', encoding='utf-8') as mf:
        mf.write('\n'.join(md))
    html_parts = ["""
<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Reporte CNEL_Verificador</title>
<style>
 body{font-family:Segoe UI,Roboto,Arial,sans-serif;margin:24px;background:#0b1220;color:#e6edf3}
 h1,h2{color:#91d1ff}
 .card{background:#121a2a;border:1px solid #22304a;border-radius:16px;padding:16px;margin-bottom:16px;box-shadow:0 1px 6px rgba(0,0,0,.3)}
 .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;margin-left:8px}
 .ok{background:#0b7a3b} .warn{background:#7a5d0b} .err{background:#7a0b2b}
 table{width:100%;border-collapse:collapse;margin:8px 0}
 th,td{border:1px solid #22304a;padding:8px;text-align:left}
 code,pre{background:#0e1728;border:1px solid #22304a;border-radius:10px;padding:8px;display:block;white-space:pre-wrap;color:#c8e1ff}
 .mono{font-family:Consolas,Menlo,monospace}
</style></head><body><h1>Reporte CNEL_Verificador</h1>""" ]
    for r in results:
        sig = r.get('signature',{}); st = sig.get('status_overall','')
        def _b(s): 
            return 'ok' if s=='VALIDA' else ('err' if s=='INVALIDA' else ('warn' if s=='PRESENTE_NO_VALIDADA' else ''))
        css = _b(st)
        html_parts.append(f"<div class='card'><h2>{html.escape(r.get('file_name',''))} <span class='badge {css}'>{html.escape(st)}</span></h2>")
        html_parts.append(f"<p class='mono'><b>SHA256:</b> {html.escape(r.get('sha256',''))}</p>")
        html_parts.append(f"<p><b>Firma (global):</b> {html.escape(sig.get('details',''))}</p>")
        if sig.get('signatures'):
            html_parts.append("<table><thead><tr><th>#</th><th>Estado</th><th>CN Firmante</th><th>Emisor (CN)</th><th>Fecha firma</th><th>TSA</th><th>Digest</th></tr></thead><tbody>")
            for idx, s in enumerate(sig['signatures'], 1):
                css_i = _b(s.get('status'))
                html_parts.append(f"<tr><td>{idx}</td><td><span class='badge {css_i}'>{html.escape(s.get('status',''))}</span></td><td>{html.escape(str(s.get('signer_cn') or ''))}</td><td>{html.escape(str(s.get('issuer_cn') or ''))}</td><td>{html.escape(str(s.get('signing_time') or ''))}</td><td>{'SÃ­' if s.get('timestamp_token') else 'No'}</td><td>{html.escape(str(s.get('digest_algo') or ''))}</td></tr>")
            html_parts.append("</tbody></table>")
        d = r.get('director',{})
        html_parts.append(f"<p><b>Director detectado:</b> {d.get('found')} â€” {html.escape(str(d.get('matches',[])))}</p>")
        en = r.get('energy',{})
        html_parts.append(f"<p><b>Total energÃ­a (kWh):</b> {en.get('totals',{}).get('total_energy_kwh',0)}</p>")
        html_parts.append("<pre>"+html.escape(json.dumps(r.get('patterns',{}), ensure_ascii=False, indent=2))+"</pre></div>")
    html_parts.append("</body></html>")
    with open(os.path.join(outdir, 'reporte_bonito.html'), 'w', encoding='utf-8') as hf:
        hf.write(''.join(html_parts))
