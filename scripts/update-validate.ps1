param(
  [switch]$FromClipboard,
  [string]$FromFile,
  [string]$FromUrl,
  [switch]$RunAfterUpdate  # si lo pasas, ejecuta el validador al final
)

$ErrorActionPreference = 'Stop'

# Rutas del proyecto
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$ToolsDir    = Join-Path $ProjectRoot 'tools'
$TargetFile  = Join-Path $ToolsDir 'validate_signs_api.py'

# Asegura estructura
if (-not (Test-Path $ToolsDir)) { New-Item -ItemType Directory -Path $ToolsDir | Out-Null }

# Contenido de origen
[string]$content = $null
if ($FromClipboard) {
  $content = Get-Clipboard -Raw
} elseif ($FromFile) {
  if (-not (Test-Path $FromFile)) { throw "No existe el archivo: $FromFile" }
  $content = Get-Content -LiteralPath $FromFile -Raw -Encoding UTF8
} elseif ($FromUrl) {
  $resp = Invoke-WebRequest -Uri $FromUrl -UseBasicParsing
  $content = $resp.Content
} else {
  throw "Indica un origen: -FromClipboard | -FromFile <ruta> | -FromUrl <url>"
}

if (-not $content) { throw "No se obtuvo contenido para actualizar." }

# Backup si existía
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = $null
if (Test-Path $TargetFile) {
  $backup = "$TargetFile.$timestamp.bak"
  Copy-Item -LiteralPath $TargetFile -Destination $backup -Force
}

# Escribe SIN BOM para evitar rarezas en Python
Set-Content -LiteralPath $TargetFile -Value $content -Encoding utf8NoBOM

Write-Host "Archivo actualizado: $TargetFile"

# Valida compilación de Python (usa el venv si existe)
$python = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' } # fallback

try {
  & $python -m py_compile $TargetFile
  Write-Host "✓ Compilación OK"
} catch {
  Write-Warning "✗ Error de compilación. Revirtiendo al backup…"
  if ($backup) {
    Copy-Item -LiteralPath $backup -Destination $TargetFile -Force
    Write-Host "Restaurado: $backup → $TargetFile"
  }
  throw
}

# Ejecuta el validador si se pidió
if ($RunAfterUpdate) {
  if (-not $env:SRC -and -not $SRC)  { Write-Warning "Variable SRC no definida."; }
  if (-not $env:TRUST -and -not $TRUST) { Write-Warning "Variable TRUST no definida."; }
  if (-not $env:OUT -and -not $OUT)  { Write-Warning "Variable OUT no definida."; }

  $SRC   = if ($SRC)   { $SRC }   elseif ($env:SRC)   { $env:SRC }   else { "" }
  $TRUST = if ($TRUST) { $TRUST } elseif ($env:TRUST) { $env:TRUST } else { "" }
  $OUT   = if ($OUT)   { $OUT }   elseif ($env:OUT)   { $env:OUT }   else { "" }

  Push-Location $ProjectRoot
  try {
    & $python $TargetFile $SRC --trust $TRUST --out $OUT
  } finally {
    Pop-Location
  }
}
