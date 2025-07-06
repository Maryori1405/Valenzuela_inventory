@echo off
echo ==========================================
echo  🔧 Iniciando entorno virtual en Windows
echo ==========================================

REM 1. Crear el entorno virtual si no existe
if not exist venv (
    echo ▶️  Creando entorno virtual...
    python -m venv venv
) else (
    echo ✅ Entorno virtual ya existe.
)

REM 2. Activar el entorno virtual
echo ▶️  Activando entorno virtual...
call venv\Scripts\activate

REM 3. Instalar dependencias necesarias
echo ▶️  Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt

REM 4. Ejecutar la aplicación Flask
echo ▶️  Iniciando app Flask...
python app.py

REM 5. Mantener ventana abierta en caso de error
pause
