@echo off
chcp 65001 >nul
setlocal

echo =====================================================
echo  ThienVoice - Tao goi portable
echo  (Chi can chay 1 lan tren may nay)
echo =====================================================
echo.

set RUNTIME=runtime
set MODEL_HUB=model_cache\hub
set HF_CACHE=%USERPROFILE%\.cache\huggingface\hub

:: ============================================================
:: BUOC 1: Python portable
:: ============================================================
if exist %RUNTIME%\python.exe (
    echo [OK] Python portable da co - bo qua.
) else (
    echo [1/3] Dang tai Python 3.12 portable...
    if not exist %RUNTIME% mkdir %RUNTIME%

    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-embed-amd64.zip' -OutFile '%RUNTIME%\py.zip' -UseBasicParsing"
    if errorlevel 1 (
        echo [LOI] Khong tai duoc Python. Kiem tra ket noi internet.
        pause
        exit /b 1
    )

    powershell -Command "Expand-Archive -Path '%RUNTIME%\py.zip' -DestinationPath '%RUNTIME%' -Force"
    del %RUNTIME%\py.zip

    :: Bat site-packages
    powershell -Command "(Get-Content '%RUNTIME%\python312._pth') -replace '#import site','import site' | Set-Content '%RUNTIME%\python312._pth'"

    echo [OK] Python portable da tai xong.
)

:: ============================================================
:: BUOC 2: Copy toan bo packages tu .venv
:: ============================================================
echo.
echo [2/3] Dang copy packages...
if not exist %RUNTIME%\Lib\site-packages mkdir %RUNTIME%\Lib\site-packages

xcopy /E /I /Y /Q ".venv\Lib\site-packages" "%RUNTIME%\Lib\site-packages\"

:: Xoa editable install links (dung PYTHONPATH thay the)
if exist "%RUNTIME%\Lib\site-packages\omnivoice.egg-link" del /Q "%RUNTIME%\Lib\site-packages\omnivoice.egg-link" 2>nul
for /d %%D in ("%RUNTIME%\Lib\site-packages\omnivoice-*.dist-info") do rmdir /s /q "%%D" 2>nul
for /d %%D in ("%RUNTIME%\Lib\site-packages\omnivoice-*.egg-info") do rmdir /s /q "%%D" 2>nul

echo [OK] Packages da copy xong.

:: ============================================================
:: BUOC 3: Copy model cache
:: ============================================================
echo.
echo [3/3] Dang copy model AI (co the mat 5-15 phut tuy dung luong)...
if not exist %MODEL_HUB% mkdir %MODEL_HUB%

:: OmniVoice model chinh (~3-5 GB)
if exist "%HF_CACHE%\models--k2-fsa--OmniVoice" (
    echo     Dang copy k2-fsa/OmniVoice...
    xcopy /E /I /Y /Q "%HF_CACHE%\models--k2-fsa--OmniVoice" "%MODEL_HUB%\models--k2-fsa--OmniVoice\"
    echo     [OK] OmniVoice model da copy.
) else (
    echo     [!] Chua tim thay OmniVoice model - se tu tai lan dau chay.
)

:: Audio tokenizer
if exist "%HF_CACHE%\models--eustlb--higgs-audio-v2-tokenizer" (
    echo     Dang copy audio tokenizer...
    xcopy /E /I /Y /Q "%HF_CACHE%\models--eustlb--higgs-audio-v2-tokenizer" "%MODEL_HUB%\models--eustlb--higgs-audio-v2-tokenizer\"
    echo     [OK] Audio tokenizer da copy.
)

:: Dataset voice tieng Viet
if exist "%HF_CACHE%\datasets--STBack23--omnivoice-vi" (
    echo     Dang copy voice dataset...
    xcopy /E /I /Y /Q "%HF_CACHE%\datasets--STBack23--omnivoice-vi" "%MODEL_HUB%\datasets--STBack23--omnivoice-vi\"
    echo     [OK] Voice dataset da copy.
)

:: Whisper ASR (neu da tai - dung cho Clone Voice)
if exist "%HF_CACHE%\models--openai--whisper-large-v3-turbo" (
    echo     Dang copy Whisper ASR...
    xcopy /E /I /Y /Q "%HF_CACHE%\models--openai--whisper-large-v3-turbo" "%MODEL_HUB%\models--openai--whisper-large-v3-turbo\"
    echo     [OK] Whisper ASR da copy.
)

echo.
echo =====================================================
echo  HOAN TAT!
echo.
echo  Bay gio copy TOAN BO thu muc nay sang may moi.
echo  Tren may moi: double-click vao run_thienvoice.bat
echo  (Khong can cai Python, khong can cai gi ca)
echo =====================================================
pause
