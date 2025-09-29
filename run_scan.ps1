param(
  [string]$SRC = "C:\Users\sidney.guerrero\Desktop\documentos_prueba",
  [string]$TRUST = "C:\Users\sidney.guerrero\Desktop\trust_certs",
  [string]$OUT = "$PSScriptRoot\reports",
  [switch]$RefreshTrust
)
$ErrorActionPreference = "Stop"
python --version | Out-Null

$rt = ""
if ($RefreshTrust) { $rt = "--refresh-trust" }

python "$PSScriptRoot\main.py" scan --input "$SRC" --trust "$TRUST" --out "$OUT" $rt
