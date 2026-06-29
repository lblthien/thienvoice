@echo off
chcp 65001 >nul
setlocal

if not exist runtime\python.exe (
    echo [LOI] Chua co runtime. Chay build_portable.bat truoc.
    pause
    exit /b 1
)

set "PYTHONPATH=%~dp0"
set "HF_HOME=%~dp0model_cache"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "PYTHONIOENCODING=utf-8"

echo Dang chay ThienVoice...
echo Log se luu vao: %~dp0loi.txt
echo.

runtime\python.exe app_ui\app.py > "%~dp0loi.txt" 2>&1

echo.
echo =====================================================
echo  CHUONG TRINH DA THOAT. Noi dung log:
echo =====================================================
type "%~dp0loi.txt"
echo =====================================================
pause
