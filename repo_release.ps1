<#
  repo_release.ps1
  Automatiza: git add/commit/push + tag + zip de release + (opcional) crear Release en GitHub con gh.
  Uso:
    # Revisión interactiva:
    powershell -ExecutionPolicy Bypass -File .\repo_release.ps1 -DryRun

    # Commit + push + tag + zip + intentar crear release con gh:
    powershell -ExecutionPolicy Bypass -File .\repo_release.ps1
#>

param(
  [switch]$DryRun,
  [string]$CommitMessage = "",
  [string]$Remote = "origin",
  [string]$Branch = "main",
  [string]$ReleasePrefix = "v",
  [string]$ReleaseName = "",
  [string]$AdditionalFiles = ".\dist;.\tools;.\README.md;.\run_cnel.ps1",
  [switch]$CreateGithubRelease   # requiere 'gh' autenticado si se usa
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Root del repo (carpeta de script)
$ROOT = (Get-Location).Path
Write-Host "[i] Repo root: $ROOT" -ForegroundColor Cyan

# 1) Mostrar estado git
Write-Host "`n[i] Estado git (git status --porcelain):" -ForegroundColor DarkGray
git status --porcelain

if ($DryRun) {
  Write-Host "`n[DRYRUN] No haré commits ni push. Revise el estado arriba." -ForegroundColor Yellow
  return
}

# 2) Staging
if (-not $CommitMessage) {
  # Mensaje por defecto con timestamp y resumen corto
  $CommitMessage = "chore: release changes - $(Get-Date -Format yyyy-MM-dd_HHmmss)"
}

Write-Host "`n[i] Añadiendo todos los cambios (git add -A)..." -ForegroundColor DarkGray
git add -A

# 3) Commit si hay cambios
$diffIndex = git diff --cached --name-only
if (-not $diffIndex) {
  Write-Host "`n[!] No hay cambios staged. Nada que commitear." -ForegroundColor Yellow
} else {
  Write-Host "[i] Commit message: $CommitMessage" -ForegroundColor DarkGray
  git commit -m $CommitMessage
  Write-Host "[OK] Commit creado." -ForegroundColor Green
}

# 4) Push al remote
Write-Host "`n[i] Push a $Remote/$Branch ..." -ForegroundColor DarkGray
git push $Remote $Branch
Write-Host "[OK] Push completado." -ForegroundColor Green

# 5) Tag semiautomático (timestamp) y push tag
$tag = "$ReleasePrefix$(Get-Date -Format yyyyMMddHHmmss)"
Write-Host "`n[i] Creando tag: $tag" -ForegroundColor DarkGray
git tag -a $tag -m "Release $tag - automated"
git push $Remote $tag
Write-Host "[OK] Tag pushed: $tag" -ForegroundColor Green

# 6) Crear ZIP de release (incluye files/carpetas listadas en $AdditionalFiles)
$zipName = "CNEL_Verificador_CLI_$($tag).zip"
$tmpFolder = Join-Path $env:TEMP "cnel_release_$($tag)"
if (Test-Path $tmpFolder) { Remove-Item -Recurse -Force $tmpFolder }
New-Item -ItemType Directory -Path $tmpFolder | Out-Null

Write-Host "`n[i] Empaquetando release en $zipName ..." -ForegroundColor DarkGray
# parse AdditionalFiles (separador ';')
$parts = $AdditionalFiles -split ';'
foreach ($p in $parts) {
  $ptrim = $p.Trim()
  if (-not $ptrim) { continue }
  $src = Join-Path $ROOT $ptrim
  if (Test-Path $src) {
    $dest = Join-Path $tmpFolder (Split-Path $ptrim -Leaf)
    if ((Get-Item $src).PSIsContainer) {
      # copiar recursivamente
      robocopy $src $dest /MIR | Out-Null
    } else {
      New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
      Copy-Item -Path $src -Destination $dest -Force -ErrorAction SilentlyContinue
    }
  } else {
    Write-Host "[warn] No existe: $src (se salta)" -ForegroundColor Yellow
  }
}

# Crear zip
$zipFull = Join-Path $ROOT $zipName
if (Test-Path $zipFull) { Remove-Item $zipFull -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($tmpFolder, $zipFull)
Write-Host "[OK] Zip creado: $zipFull" -ForegroundColor Green

# limpiar temp
Remove-Item -Recurse -Force $tmpFolder

# 7) (opcional) Crear Release en GitHub con 'gh' (si se pide)
if ($CreateGithubRelease) {
  Write-Host "`n[i] Intentando crear Release en GitHub con gh..." -ForegroundColor DarkGray
  if (Get-Command gh -ErrorAction SilentlyContinue) {
    if (-not $ReleaseName) { $ReleaseName = "Release $tag" }
    gh release create $tag $zipFull --title "$ReleaseName" --notes "Automated release $tag"
    Write-Host "[OK] GitHub Release creado (tag: $tag)" -ForegroundColor Green
  } else {
    Write-Host "[warn] 'gh' no está instalado o no está autenticado. Salta la creación de Release." -ForegroundColor Yellow
  }
}

Write-Host "`n✅ Proceso finalizado. Tag: $tag  Zip: $zipFull" -ForegroundColor Magenta
