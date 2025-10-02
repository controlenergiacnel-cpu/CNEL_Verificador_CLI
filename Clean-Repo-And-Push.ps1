<# 
Clean-Repo-And-Push.ps1
Limpia archivos grandes del historial (git filter-repo o BFG), agrega .gitignore,
y hace push forzado vía SSH.
USO:
  .\Clean-Repo-And-Push.ps1 -RepoPath "C:\ruta\al\repo" -Branch "main" -RemoteName "origin"
#>

param(
  [string]$RepoPath = ".",
  [string]$Branch = "main",
  [string]$RemoteName = "origin",
  [int]$BlobLimitMB = 50
)

$ErrorActionPreference = "Stop"
Set-Location $RepoPath

if (!(Test-Path ".git")) { throw "No es un repo Git: $RepoPath" }

Write-Host "==> Limpiando repo en: $RepoPath" -ForegroundColor Cyan

# 1) Asegurar .gitignore actualizado
$gitignore = @"
# --- CNEL_Verificador_CLI ---
# Entornos/artefactos
venv/
.venv/
env/
build/
dist/
*.spec
__pycache__/
*.pyc
# Salidas locales
outputs/
reports/*/*.pdf
reports/*/*.xlsx
reports/*/*.zip
# Binarios/paquetes pesados
*.bundle
*.pkg
*.pack
*.zip
*.7z
*.rar
*.tar
*.tar.gz
*.jar
*.exe
*.msi
*.iso
# Logs temporales
*.log
*.tmp
*.cache
"@

$giPath = Join-Path $RepoPath ".gitignore"
$gitignore | Out-File -FilePath $giPath -Encoding UTF8
git add .gitignore
git commit -m "chore: actualizar .gitignore (excluir binarios y artefactos)" -q

# 2) Detectar si git filter-repo está disponible
function Test-FilterRepo {
  try {
    git filter-repo --help *>$null
    return $true
  } catch {
    return $false
  }
}

$useFilterRepo = Test-FilterRepo

if (-not $useFilterRepo) {
  Write-Host "==> git-filter-repo no encontrado. Intentando instalar con Python..." -ForegroundColor Yellow
  try {
    # Usa el python por defecto en Windows (py)
    py -m pip install --upgrade git-filter-repo
    $useFilterRepo = Test-FilterRepo
  } catch {
    $useFilterRepo = $false
  }
}

# 3) Reescritura del historial
if ($useFilterRepo) {
  Write-Host "==> Usando git filter-repo para limpiar historial..." -ForegroundColor Green
  # Elimina blobs > BlobLimitMB y patrones binarios frecuentes
  $patterns = @("*.bundle","*.pkg","*.pack","*.zip","*.7z","*.rar","*.tar","*.tar.gz","*.jar","*.exe","*.msi","*.iso")
  $patternArgs = $patterns | ForEach-Object { "--path-glob", $_, "--invert-paths" }

  # Primero filtrar por tamaño
  git filter-repo --strip-blobs-bigger-than "$($BlobLimitMB)M"

  # Luego eliminar rutas por patrón (si quedaron)
  foreach ($p in $patterns) {
    git filter-repo --path-glob "$p" --invert-paths
  }
}
else {
  Write-Host "==> Usando BFG como alternativa..." -ForegroundColor Yellow
  $bfg = Join-Path $env:TEMP "bfg.jar"
  if (!(Test-Path $bfg)) {
    Invoke-WebRequest -UseBasicParsing -Uri "https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar" -OutFile $bfg
  }

  # Asegurar HEAD limpio
  git checkout $Branch

  # Ejecutar BFG para borrar blobs grandes y patrones binarios
  & java -jar $bfg --strip-blobs-bigger-than ${BlobLimitMB}M

  $toDelete = @("*.bundle","*.pkg","*.pack","*.zip","*.7z","*.rar","*.tar","*.tar.gz","*.jar","*.exe","*.msi","*.iso")
  foreach ($p in $toDelete) {
    & java -jar $bfg --delete-files $p
  }

  git reflog expire --expire=now --all
  git gc --prune=now --aggressive
}

# 4) Push forzado al remoto (requiere SSH ya configurado)
Write-Host "==> Haciendo push forzado a $RemoteName/$Branch (SSH)..." -ForegroundColor Cyan
git push $RemoteName --force --all
git push $RemoteName --force --tags

Write-Host "`nListo. Repo limpio y empujado por SSH." -ForegroundColor Green
