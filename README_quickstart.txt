CNEL_Verificador_CLI â€” Quickstart
=================================
1) Entorno
   cd "%USERPROFILE%\Desktop\CNEL_Verificador_CLI"
   python -m venv .\venv
   .\venv\Scripts\activate
   python -m pip install -U pip wheel
   python -m pip install -r requirements_cli.txt

2) Tesseract OCR
   winget source update
   winget install -e --id UB-Mannheim.TesseractOCR --source winget --accept-package-agreements --accept-source-agreements
   "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

3) Ejecutar
   python -m app.gui
   # o
   python -m app.cli --input "C:\RUTA\A\TU\CARPETA"

4) Confianza de firmas (opcional)
   Copia certificados raÃ­z/intermedios a config\trust\ (.pem/.crt/.cer).
