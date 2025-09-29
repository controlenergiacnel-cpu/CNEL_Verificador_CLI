param(
  [string]$Src = "C:\Users\sidney.guerrero\Desktop\documentos_prueba",
  [string]$Trust = "C:\Users\sidney.guerrero\Desktop\trust_certs"
)

$ErrorActionPreference = "Stop"

# Consola y Python en UTF-8 (evita UnicodeEncodeError)
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

# Carpeta de salida con timestamp
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path -Path "_audit_reports" -ChildPath $stamp
New-Item -ItemType Directory -Force -Path $out | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $out "ocr") | Out-Null

# 1) OCR "diagnÃ³stico" por archivo (solo lee, no escribe PDFs)
$files = Get-ChildItem -Path $Src -Recurse -Filter *.pdf -ErrorAction SilentlyContinue
$idx = 0
foreach ($f in $files) {
  $idx++
  Write-Host ("[{0}/{1}] OCR meta: {2}" -f $idx, $files.Count, $f.FullName)
  $rep = Join-Path $out "ocr\$($f.BaseName).json"
  python -m tools.diag_ocr "$($f.FullName)" | Set-Content -Encoding UTF8 $rep
}

# 2) ValidaciÃ³n de firmas (sin trust explÃ­cito)
Write-Host "ValidaciÃ³n de firmas (sin trust) ..."
python .\tools\sig_validate.py $Src | Set-Content -Encoding UTF8 (Join-Path $out "sig_untrusted.json")

# 3) ValidaciÃ³n de firmas (con trust, si existe carpeta)
if (Test-Path $Trust) {
  Write-Host "ValidaciÃ³n de firmas (con trust: $Trust) ..."
  python -m tools.validate_signs_api $Src $Trust | Set-Content -Encoding UTF8 (Join-Path $out "sig_trusted.json")
} else {
  Write-Warning "Carpeta de trust no existe: $Trust. Saltando validaciÃ³n confiable."
  Set-Content -Encoding UTF8 -Path (Join-Path $out "sig_trusted.json") -Value "[]"
}

# 4) OCR de apariencia de firmas (tesseract si estÃ¡; fallback a EasyOCR)
Write-Host "OCR de apariencia de firmas..."
python .\tools\ocr_sig_appearance.py $Src | Set-Content -Encoding UTF8 (Join-Path $out "sig_appearance_ocr.json")

# 5) Merge -> CSV
Write-Host "Generando resumen CSV..."
python .\tools\merge_audit.py $out | Tee-Object -Variable merge_res | Out-Null
Write-Host "Listo. Carpeta:" $out
