@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo 🔼 Subiendo proyecto a GitHub...
echo ==========================================

REM 1. Ir al directorio del proyecto (ajústalo si es necesario)
cd /d %~dp0

REM 2. Inicializar Git si no existe
if not exist ".git" (
    git init
    git branch -M main
    git remote add origin https://github.com/Maryori1405/Valenzuela_inventory.git
)

REM 3. Agregar todos los cambios
git add .

REM 4. Crear un mensaje de commit con fecha y hora
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH:mm:ss"') do set FECHA=%%i
git commit -m "Actualización automática %FECHA%"

REM 5. Subir a GitHub
git push -u origin main

echo ✅ Proyecto subido correctamente a GitHub.
pause
