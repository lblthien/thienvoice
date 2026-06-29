@echo off
chcp 65001 >nul
setlocal

:: Kiem tra da build portable chua
if not exist runtime\python.exe (
    echo =====================================================
    echo  Chua setup portable.
    echo  Vui long chay: build_portable.bat
    echo  (Chi can chay 1 lan tren may goc)
    echo =====================================================
    pause
    exit /b 1
)

:: Dat duong dan de Python tim thay code va model
set "PYTHONPATH=%~dp0"
set "HF_HOME=%~dp0model_cache"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "PYTHONIOENCODING=utf-8"

echo =====================================================
echo  ThienVoice - Tong hop giong noi tieng Viet
echo =====================================================
echo.
echo  Dang khoi dong...
echo  Trinh duyet se tu mo: http://localhost:7860
echo.
echo  (Lan dau co the mat 1-2 phut)
echo  De tat: dong cua so nay
echo.

runtime\python.exe app_ui\app.py

pause
