<# cleanup_repo_fixed.ps1
   Versión corregida del cleanup_repo.ps1 para PowerShell.
   - Usa llamada directa a git (& git ...) y captura salida.
   - Realiza la limpieza suave (rm --cached), commit y push a HTTPS con reintentos.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoPath = Get-Location
Write-Host "Working directory: $RepoPath`n" -ForegroundColor Cyan

function Run-Git {
    param([string]$Args)
    $fullCmd = "git $Args"
    Write-Host "▶ $fullCmd"
    # Ejecuta git y captura stdout/stderr
    $output = & git $Args 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        # Mostrar la salida línea por línea para que se vea ordenada
        if ($output -is [System.Array]) {
            $output | ForEach-Object { Write-Host $_ }
        } else {
            Write-Host $output
        }
    }
    return $exitCode
}

try {
    # 1) Crear .gitignore si no existe
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
        $ret = Run-Git "add .gitignore"
        if ($ret -eq 0) { Run-Git 'commit -m "Añadir .gitignore para artefactos generados"' }
    } else {
        Write-Host ".gitignore ya existe. Primer bloque:" -ForegroundColor Yellow
        Get-Content $gitignorePath -TotalCount 30 | ForEach-Object { Write-Host $_ }
    }

    # 2) Estado resumido
    Write-Host "`nEstado git (resumen):" -ForegroundColor Cyan
    Run-Git "status --short"

    Write-Host "`nArchivos no trackeados (exclude-standard):" -ForegroundColor Cyan
    Run-Git "ls-files --others --exclude-standard"

    # 3) Quitar del índice los artefactos comunes
    Write-Host "`nEliminando del índice: build/, dist/, CNEL_Verificador_CLI.spec, cnel_verificador.spec (si existen)..." -ForegroundColor Green
    Run-Git "rm -r --cached --ignore-unmatch build dist CNEL_Verificador_CLI.spec cnel_verificador.spec" | Out-Null

    # Comprobar si hay cambios para commitear
    $porcelain = & git status --porcelain
    if ($porcelain) {
        Write-Host "`nSe detectaron cambios listos para commit. Commitando..." -ForegroundColor Green
        Run-Git 'commit -m "Remove build/dist and spec files from index"'
    } else {
        Write-Host "No hay cambios para commitear (quizá ya estaban sin trackear)." -ForegroundColor Yellow
    }

    # 4) Forzar remote a HTTPS
    Write-Host "`nComprobando remote origin..." -ForegroundColor Cyan
    $remotes = (& git remote -v) -join "`n"
    Write-Host $remotes
    Write-Host "`nCambiando origin a HTTPS..." -ForegroundColor Green
    Run-Git "remote set-url origin https://github.com/controlenergiacnel-cpu/CNEL_Verificador_CLI.git"

    # 5) Push con reintentos simples
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
        Write-Host "- Verifica conexión a Internet / proxy / firewall."
        Write-Host "- Prueba desde otra red (tethering móvil)."
        Write-Host "- Revisa permisos en GitHub y usa un PAT si te solicita credenciales."
        Write-Host "- Si necesitas, ejecuta la reescritura con mirror en otra máquina/archivo bundle."
    }

    Write-Host "`n✅ Operación finalizada (limpieza suave). Revisa git status y logs localmente." -ForegroundColor Green
    Run-Git "status --short"

} catch {
    Write-Host "`nERROR en el script: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.ToString()
    exit 1
}

