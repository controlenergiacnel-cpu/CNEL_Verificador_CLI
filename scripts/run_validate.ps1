Param(
  [string]$SRC   = "C:\Users\sidney.guerrero\Desktop\documentos_prueba",
  [string]$TRUST = "C:\Users\sidney.guerrero\Desktop\trust_certs",
  [string]$OUT   = "C:\Users\sidney.guerrero\Desktop\CNEL_Verificador_CLI\reports"
)

$ErrorActionPreference = "Stop"

Write-Host "== CNEL_Verificador_CLI: Validación de firmas + OCR =="
Write-Host "SRC   = $SRC"
Write-Host "TRUST = $TRUST"
Write-Host "OUT   = $OUT"

python ".\tools\validate_signs_api.py" "$SRC" --trust "$TRUST" --out "$OUT"
