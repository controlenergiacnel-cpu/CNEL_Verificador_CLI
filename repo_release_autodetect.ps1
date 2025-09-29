# repo_release_autodetect.ps1
param(
  [switch]$DryRun,
  [string]$CommitMessage = "",
  [string]$Remote = "origin",
  [string]$Branch = "main",
  [string]$ReleasePrefix = "v",
  [string]$AdditionalFiles = ".\dist;.\tools;.\README.md;.\run_cnel.ps1",
  [switch]$CreateGithubRelease
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ROOT = (Get-Location).Path
Write-Host "[i] Repo root: $ROOT" -ForegroundColor Cyan

# detect git
$gitExists = (Get-Command git -ErrorAction SilentlyContinue) -ne $null
if (-not $gitExists) { Write-Host "[warn] git no encontrado en PATH. Saltando operaciones git." -ForegroundColor Yellow }

if ($gitExists) {
  Write-Host "[i] Estado git (git status --porcelain):" -ForegroundColor DarkGray
  git status --porcelain
}

if ($DryRun) { Write-Host "[DRYRUN] Salida temprana (dryrun)." -ForegroundColor Yellow; return }

if ($gitExists) {
  if (-not $CommitMessage) { $CommitMessage = "chore: release changes - $(Get-Date -Format yyyy-MM-dd_HHmmss)" }
  git add -A
  $diffIndex = git diff --cached --name-only
  if ($diffIndex) {
    git commit -m $CommitMessage
    Write-Host "[OK] Commit creado." -ForegroundColor Green
    git push $Remote $Branch
    Write-Host "[OK] Push completado." -ForegroundColor Green
    $tag = "$ReleasePrefix$(Get-Date -Format yyyyMMddHHmmss)"
    git tag -a $tag -m "Release $tag - automated"
    git push $Remote $tag
    Write-Host "[OK] Tag pushed: $tag" -ForegroundColor Green
  } else {
    Write-Host "[i] No hay cambios staged: saltando commit/push/tag." -ForegroundColor Yellow
    $tag = "$ReleasePrefix$(Get-Date -Format yyyyMMddHHmmss)"
  }
} else {
  $tag = "$ReleasePrefix$(Get-Date -Format yyyyMMddHHmmss)"
}

# ZIP (siempre)
$tmpFolder = Join-Path $env:TEMP "cnel_release_$($tag)"
if (Test-Path $tmpFolder) { Remove-Item -Recurse -Force $tmpFolder }
New-Item -ItemType Directory -Path $tmpFolder | Out-Null
$parts = $AdditionalFiles -split ';'
foreach ($p in $parts) {
  $ptrim = $p.Trim()
  if (-not $ptrim) { continue }
  $src = Join-Path $ROOT $ptrim
  if (Test-Path $src) {
    $dest = Join-Path $tmpFolder (Split-Path $ptrim -Leaf)
    if ((Get-Item $src).PSIsContainer) { robocopy $src $dest /MIR | Out-Null }
    else { New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Copy-Item -Path $src -Destination $dest -Force }
  } else { Write-Host "[warn] No existe: $src (se salta)" -ForegroundColor Yellow }
}

$zipName = "CNEL_Verificador_CLI_$($tag).zip"
$zipFull = Join-Path $ROOT $zipName
if (Test-Path $zipFull) { Remove-Item $zipFull -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($tmpFolder, $zipFull)
Remove-Item -Recurse -Force $tmpFolder
Write-Host "[OK] Zip creado: $zipFull" -ForegroundColor Green

# crear GH release si se pidió y gh existe + autenticado
if ($CreateGithubRelease) {
  if ((Get-Command gh -ErrorAction SilentlyContinue) -ne $null -and $gitExists) {
    gh release create $tag $zipFull --title "Release $tag" --notes "Automated release"
    Write-Host "[OK] GitHub Release creado (tag: $tag)" -ForegroundColor Green
  } else {
    Write-Host "[warn] No se puede crear GitHub Release (falta gh o git)." -ForegroundColor Yellow
  }
}

Write-Host "`n✅ Proceso finalizado. Tag: $tag  Zip: $zipFull" -ForegroundColor Magenta
