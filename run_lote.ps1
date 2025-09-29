param(
  [Parameter(Mandatory=$true)] [string]$Src,
  [string]$Trust = "",
  [string]$OutBase = "_sign_reports"
)

$ts  = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $OutBase $ts
New-Item -ItemType Directory -Force -Path $out | Out-Null

$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

Write-Host "1/4 Validación SIN confianza..."
python -m tools.validate_signs_api $Src | Set-Content -Encoding UTF8 "$out\sig_untrusted.json"

Write-Host "2/4 Validación CON confianza..."
if ($Trust -ne "") {
  python -m tools.validate_signs_api $Src $Trust | Set-Content -Encoding UTF8 "$out\sig_trusted.json"
} else {
  "[]" | Set-Content -Encoding UTF8 "$out\sig_trusted.json"
}

Write-Host "3/4 OCR de apariencias de firma..."
python .\tools\ocr_sig_appearance.py $Src | Set-Content -Encoding UTF8 "$out\sig_appearance_ocr.json"

Write-Host "4/4 Construyendo reporte TXT..."
python .\tools\build_lote_report.py `
  "$out\sig_untrusted.json" `
  "$out\sig_trusted.json" `
  "$out\sig_appearance_ocr.json" | Set-Content -Encoding UTF8 "$out\reporte_lote.txt"

Write-Host "Listo: $out"
