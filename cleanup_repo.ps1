<# cleanup_repo.ps1
   Limpieza segura del repo local:
   - Añade .gitignore (si no existe)
   - Quita del índice build/, dist/, *.spec
   - Commits correspondientes
   - Cambia remote a HTTPS y hace push
   - Salidas claras y recomendaciones en caso de fallo de red
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Ruta del repo (asume que se ejecuta desde la raíz)
$RepoPath = Get-Location

Write-Host "Working directory: $RepoPath`n" -ForegroundColor Cyan

function Run-Git {
    param($args)
    $cmd = "git $args"
    Write-Host "▶ $cmd"
    $proc = Start-Process -FilePath git -ArgumentList $args -NoNewWindow -Wait -PassThru -RedirectStandardOutput -RedirectStandardError
    $out = $proc.StandardOutput.ReadToEnd()
    $err = $proc.StandardError.ReadToEnd()
    if ($out) { Write-Host $out }
    if ($err) { Write-Host $err -ForegroundColor Red }
    return $proc.ExitCode
}

try {
    # 1) Crear .gitignore si no existe (añade patrones recomendados)
    $gitignorePath = Join-Path $RepoPath ".gitignore"
    if (-not (Test-Path $gitignorePath)) {
        Write-Host "Creando .gitignore básico..." -ForegroundColor Green
        @'
# Python
__pycache__/
*.py[cod]
venv/
.venv/

# Build / Dist
build/
dist/
*.spec
*.exe
*.zip
*.pkg

# Reports and artifacts
_audit_reports/
_sign_reports/

# Trust certs (no guardar)
trust_certs/

# Local mirror
cnel-mirror.git/

# OS / IDE
.vscode/
.DS_Store
'@ | Out-File -FilePath $gitignorePath -Encoding utf8
        Run-Git "add .gitignore"
        Run-Git 'commit -m "Añadir .gitignore para artefactos generados"'
    } else {
        Write-Host ".gitignore ya existe. Mostrando primer bloque..." -ForegroundColor Yellow
        Get-Content $gitignorePath -TotalCount 30 | ForEach-Object { Write-Host $_ }
    }

    # 2) Ver estado y listar archivos no trackeados
    Write-Host "`nEstado git (resumen):" -ForegroundColor Cyan
    Run-Git "status --short"

    Write-Host "`nArchivos no trackeados (exclude-standard):" -ForegroundColor Cyan
    Run-Git "ls-files --others --exclude-standard"

    # 3) Quitar del índice los artefactos comunes (no borran archivos locales)
    Write-Host "`nEliminando del índice: build/, dist/, CNEL_Verificador_CLI.spec, cnel_verificador.spec (si existen)..." -ForegroundColor Green
    $rmCmd = "rm -r --cached --ignore-unmatch build dist CNEL_Verificador_CLI.spec cnel_verificador.spec"
    # Usamos git rm para mayor compatibilidad:
    Run-Git "rm -r --cached build dist CNEL_Verificador_CLI.spec cnel_verificador.spec" | Out-Null
    # Commit si hay cambios
    $status = Run-Git "status --porcelain"
    if ($status -ne 0) { Write-Host "git status returned code $status (continuando)"; }
    $porcelain = (& git status --porcelain) -join "`n"
    if ($porcelain) {
        Write-Host "`nSe detectaron cambios listos para commit. Commitando..." -ForegroundColor Green
        Run-Git 'commit -m "Remove build/dist and spec files from index"'
    } else {
        Write-Host "No hay cambios para commitear (quizá ya estaban sin trackear)." -ForegroundColor Yellow
    }

    # 4) Forzar remote a HTTPS (evita problemas SSH)
    Write-Host "`nComprobando remote origin..." -ForegroundColor Cyan
    $remotes = (& git remote -v) -join "`n"
    Write-Host $remotes
    Write-Host "`nCambiando origin a HTTPS (https://github.com/controlenergiacnel-cpu/CNEL_Verificador_CLI.git)..." -ForegroundColor Green
    Run-Git "remote set-url origin https://github.com/controlenergiacnel-cpu/CNEL_Verificador_CLI.git"

    # 5) Push con manejo simple de reintentos
    Write-Host "`nIntentando push origin main..." -ForegroundColor Cyan
    $maxRetries = 3
    $i = 0
    $pushed = $false
    while ($i -lt $maxRetries -and -not $pushed) {
        $i++; Write-Host "Intento $i de $maxRetries..."
        $exit = Run-Git "push origin main"
        if ($exit -eq 0) {
            Write-Host "Push realizado correctamente." -ForegroundColor Green
            $pushed = $true
            break
        } else {
            Write-Host "Push falló (código $exit). Esperando 5s antes de reintentar..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }

    if (-not $pushed) {
        Write-Host "`nERROR: No se pudo hacer push al remoto tras $maxRetries intentos." -ForegroundColor Red
        Write-Host "Sugerencias:" -ForegroundColor Cyan
        Write-Host "- Verifica que tu conexión a Internet permita HTTPS (firewall corporativo puede bloquear)." 
        Write-Host "- Prueba desde otra red (ej. tethering de móvil) y reintenta: git push origin main"
        Write-Host "- Comprueba que el repo existe y que tienes permisos: https://github.com/controlenergiacnel-cpu/CNEL_Verificador_CLI"
        Write-Host "- Si tu empresa usa proxy, configura 'git config --global http.proxy http://proxy:port' o usa una red sin proxy."
    }

    Write-Host "`n✅ Operación finalizada (limpieza suave). Revisa git status y logs localmente." -ForegroundColor Green
    Run-Git "status --short"

} catch {
    Write-Host "`nERROR en el script: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.ToString()
    exit 1
}
