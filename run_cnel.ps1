Param(
  [Parameter(Mandatory=$true, Position=0)]
  [ValidateSet("scan","report")]
  [string]$cmd,

  [Parameter(Position=1)]
  [string]$input = ".\documentos_prueba",

  [Parameter(Position=2)]
  [string]$trust = ".\trust_certs",

  [Parameter(Position=3)]
  [string]$out   = ".\reports",

  [switch]$refresh_trust
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Helper: normaliza a ruta absoluta si puede (si no existe, compone con PSScriptRoot)
function _abs([string]$p) {
  if ([string]::IsNullOrWhiteSpace($p)) { return $p }
  try {
    if ([IO.Path]::IsPathRooted($p)) { return $p }
    return (Resolve-Path -Path $p -ErrorAction Stop).Path
  } catch {
    return Join-Path $PSScriptRoot $p
  }
}

# Normalizar variables y mostrar debug corto
$input = _abs $input
$trust = _abs $trust
$out   = _abs $out

Write-Host "[debug] cmd  = '$cmd'"
Write-Host "[debug] input= '$input'"
Write-Host "[debug] trust= '$trust'"
Write-Host "[debug] out  = '$out'"

# Backend preferido: EXE one-folder > venv python > python global
$exe = Join-Path $PSScriptRoot "dist\CNEL_Verificador_CLI\CNEL_Verificador_CLI.exe"
$py  = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

# Construir argumentos *como una sola cadena por argumento* (evita separaciÃ³n incorrecta)
if ($cmd -eq "scan") {
  $argv = @("--input=`"$input`"", "--out=`"$out`"")
  if (-not [string]::IsNullOrWhiteSpace($trust)) { $argv += "--trust=`"$trust`"" }
  if ($refresh_trust) { $argv += "--refresh-trust" }
  # el subcomando debe ir primero
  $argv = @("scan") + $argv
} else {
  $argv = @("report", "--out=`"$out`"")
}

# Mostrar la lÃ­nea a ejecutar (legible)
if (Test-Path $exe) {
  Write-Host "[i] Ejecutando EXE:" $exe ($argv -join ' ') -ForegroundColor Cyan
  & $exe @argv
}
elseif (Test-Path $py) {
  Write-Host "[i] Ejecutando VENV:" $py ".\main.py" ($argv -join ' ') -ForegroundColor Cyan
  & $py ".\main.py" @argv
}
else {
  Write-Host "[i] Ejecutando PY:" "python .\main.py" ($argv -join ' ') -ForegroundColor Cyan
  & python ".\main.py" @argv
}
