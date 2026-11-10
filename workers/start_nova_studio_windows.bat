@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv" (
  py -3.11 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo Python kunde inte skapa den lokala miljoen.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r workers\requirements.txt
if not "%COMFYUI_DIR%"=="" if exist "%COMFYUI_DIR%\\run_nvidia_gpu.bat" (
  echo Startar ComfyUI...
  start "ComfyUI" /D "%COMFYUI_DIR%" run_nvidia_gpu.bat
  timeout /t 30 /nobreak >nul
)
if "%NOVA_STUDIO_WORKER_TOKEN%"=="" (
  echo.
  echo Satt NOVA_STUDIO_WORKER_TOKEN i Windows miljo variabler innan du startar arbetaren.
  pause
  exit /b 1
)
echo Kontrollerar att ComfyUI svarar pa localhost:8188...
".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8188/system_stats',timeout=5)"
if errorlevel 1 (
  echo Starta ComfyUI forst och kor sedan detta script igen.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" workers\nova_studio_worker.py
pause
