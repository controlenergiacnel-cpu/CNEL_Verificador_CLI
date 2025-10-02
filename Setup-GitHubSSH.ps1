<# 
Setup-GitHubSSH.ps1
Configura autenticación SSH con GitHub y cambia el remoto del repo a SSH.
USO:
  .\Setup-GitHubSSH.ps1 -RepoPath "C:\ruta\al\repo" -GithubRepo "controlenergiacnel-cpu/CNEL_Verificador_CLI" -UserEmail "tu_email@cnel.gob.ec" -UserName "Tu Nombre"
#>

param(
  [string]$RepoPath = ".",
  [string]$GithubRepo = "",
  [string]$UserEmail = "",
  [string]$UserName = ""
)

$ErrorActionPreference = "Stop"

Write-Host "==> Iniciando configuración SSH para GitHub..." -ForegroundColor Cyan

# 1) Config Git opcional (nombre y correo)
if ($UserEmail -and $UserName) {
  git config --global user.email $UserEmail
  git config --global user.name $UserName
  Write-Host "   ✔ Configurado user.name y user.email globales"
}

# 2) Asegurar que el servicio ssh-agent esté activo
Write-Host "==> Habilitando ssh-agent..."
Get-Service ssh-agent -ErrorAction SilentlyContinue | Set-Service -StartupType Automatic
Start-Service ssh-agent

# 3) Generar clave si no existe
$sshDir = Join-Path $env:USERPROFILE ".ssh"
$privateKey = Join-Path $sshDir "id_ed25519"
$publicKey  = Join-Path $sshDir "id_ed25519.pub"

if (!(Test-Path $publicKey)) {
  Write-Host "==> No existe clave SSH. Generando nueva id_ed25519..."
  if (!(Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir | Out-Null }
  ssh-keygen -t ed25519 -C "$($env:USERNAME)@$($env:COMPUTERNAME)" -f $privateKey -N ""
} else {
  Write-Host "   ✔ Clave SSH ya existente. Usando $publicKey"
}

# 4) Cargar clave al agente
ssh-add $privateKey | Out-Null
Write-Host "   ✔ Clave cargada en ssh-agent"

# 5) Copiar la clave pública al portapapeles para pegarla en GitHub
Get-Content $publicKey | Set-Clipboard
Write-Host "==> Tu clave pública se copió al portapapeles."
Write-Host "   Abre GitHub → Settings → SSH and GPG keys → New SSH key y pega el contenido."
Write-Host "   Título sugerido: $($env:COMPUTERNAME)-$($env:USERNAME)"

# 6) Cambiar remoto a SSH si se indicó el repo
if ($GithubRepo) {
  if (Test-Path $RepoPath) { Set-Location $RepoPath }
  Write-Host "==> Configurando remoto 'origin' a SSH para $GithubRepo ..."
  git remote set-url origin "git@github.com:$GithubRepo.git"
  Write-Host "   ✔ Remoto actualizado"
}

# 7) Probar conexión con GitHub
Write-Host "==> Probando conexión SSH con GitHub..."
ssh -T git@github.com

Write-Host "`nListo. Si ves un mensaje de 'successfully authenticated', la conexión está OK." -ForegroundColor Green
