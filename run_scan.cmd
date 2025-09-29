@echo off
setlocal
set "SRC=C:\Users\sidney.guerrero\Desktop\documentos_prueba"
set "TRUST=C:\Users\sidney.guerrero\Desktop\trust_certs"
set "OUT=%~dp0reports"

python "%~dp0main.py" scan --input "%SRC%" --trust "%TRUST%" --out "%OUT%"
endlocal
