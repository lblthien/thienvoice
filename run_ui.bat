@echo off
chcp 65001 >nul
setlocal

echo =====================================================
echo  OmniVoice MVP - Giao dien Desktop
echo =====================================================
echo.

:: Kiem tra .venv
if not exist .venv\Scripts\python.exe (
    echo [LOI] Chua co .venv. Chay setup_mvp_env.bat truoc.
    pause
    exit /b 1
)

:: Kiem tra voice preset
if not exist assets\omnivoice-vi\voices\tuong_vy\voice.pt (
    echo [CANH BAO] Chua co voice preset. Dang tai...
    .venv\Scripts\python.exe app_mvp\download_tuong_vy.py
    if errorlevel 1 (
        echo [LOI] Tai voice preset that bai.
        pause
        exit /b 1
    )
)

echo [OK] Moi thu san sang.
echo.
echo Dang khoi dong UI tai http://localhost:7860
echo Trinh duyet se tu dong mo. Neu khong, mo thu cong tai:
echo   http://localhost:7860
echo.
echo De dung UI: nhan Ctrl+C trong cua so nay.
echo.

.venv\Scripts\python.exe app_ui\app.py

pause
