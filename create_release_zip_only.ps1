# create_release_zip_only.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ROOT = (Get-Location).Path
$tag = "local_$(Get-Date -Format yyyyMMddHHmmss)"
$zipName = "CNEL_Verificador_CLI_$tag.zip"
$tmpFolder = Join-Path $env:TEMP "cnel_release_$($tag)"
if (Test-Path $tmpFolder) { Remove-Item -Recurse -Force $tmpFolder }
New-Item -ItemType Directory -Path $tmpFolder | Out-Null

# Ajusta qué incluir aquí:
$itemsToInclude = @(".\tools", ".\run_cnel.ps1", ".\README.md", ".\dist", ".\main.py")

foreach ($it in $itemsToInclude) {
  $src = Join-Path $ROOT $it
  if (-not (Test-Path $src)) { Write-Host "[warn] No existe: $src" -ForegroundColor Yellow; continue }
  $dest = Join-Path $tmpFolder (Split-Path $it -Leaf)
  if ((Get-Item $src).PSIsContainer) {
    robocopy $src $dest /MIR | Out-Null
  } else {
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item -Path $src -Destination $dest -Force
  }
}

$zipFull = Join-Path $ROOT $zipName
if (Test-Path $zipFull) { Remove-Item $zipFull -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($tmpFolder, $zipFull)
Remove-Item -Recurse -Force $tmpFolder

Write-Host "✅ ZIP creado: $zipFull" -ForegroundColor Green
