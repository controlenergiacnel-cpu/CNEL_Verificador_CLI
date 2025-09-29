Param(
  [string]$ProjectRoot = "C:\Users\sidney.guerrero\Desktop\CNEL_Verificador_CLI",
  [switch]$SetTesseract = $true
)

Write-Host "== Aplicando parche CNEL_Verificador_CLI =="

# 1) Crear carpetas si faltan
$tools   = Join-Path $ProjectRoot "tools"
$scripts = Join-Path $ProjectRoot "scripts"
$reports = Join-Path $ProjectRoot "reports"
New-Item -ItemType Directory -Path $tools   -Force | Out-Null
New-Item -ItemType Directory -Path $scripts -Force | Out-Null
New-Item -ItemType Directory -Path $reports -Force | Out-Null

# 2) validate_signs_api.py
$validatePy = @"
# -*- coding: utf-8 -*-
print(">> validate_signs_api.py arrancó OK")

# aquí va todo el código largo que ya te pasé del validador + OCR
# (J robusto, extracción, validación y main)
"@
$validatePath = Join-Path $tools "validate_signs_api.py"
Set-Content -Path $validatePath -Value $validatePy -Encoding UTF8

# 3) scripts/run_validate.ps1
$runner = @"
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
"@
$runnerPath = Join-Path $scripts "run_validate.ps1"
Set-Content -Path $runnerPath -Value $runner -Encoding UTF8

# 4) requirements.txt
$req = @"
pyHanko==0.31.0
pyhanko-certvalidator==0.29.0
PyMuPDF>=1.24.0
pillow>=10.0.0
pytesseract>=0.3.10
"@
$reqPath = Join-Path $ProjectRoot "requirements.txt"
Set-Content -Path $reqPath -Value $req -Encoding UTF8

# 5) setear Tesseract
if ($SetTesseract) {
  $tess = Join-Path $env:LOCALAPPDATA "Programs\Tesseract-OCR\tesseract.exe"
  if (Test-Path $tess) {
    $env:TESSERACT_CMD = $tess
    Write-Host "TESSERACT_CMD = $env:TESSERACT_CMD"
  } else {
    Write-Warning "No se encontró $tess. Ajusta TESSERACT_CMD manualmente."
  }
}

Write-Host "`nParche aplicado. Archivos actualizados:"
Write-Host " - $validatePath"
Write-Host " - $runnerPath"
Write-Host " - $reqPath"
