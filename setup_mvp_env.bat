@echo off
chcp 65001 >nul
setlocal

echo =====================================================
echo  OmniVoice MVP - Setup Environment (Python 3.12)
echo =====================================================
echo.

:: Kiem tra Python 3.12
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay Python 3.12.
    echo       Tai Python 3.12 tai: https://www.python.org/downloads/
    echo       Chon "Add to PATH" khi cai dat.
    pause
    exit /b 1
)

echo Python 3.12 tim thay:
py -3.12 --version

echo.

:: Tao .venv neu chua co
if not exist .venv (
    echo [BUOC 1/6] Tao virtual environment .venv voi Python 3.12...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo [LOI] Tao venv that bai.
        pause
        exit /b 1
    )
    echo [OK] Da tao .venv
) else (
    echo [BUOC 1/6] .venv da ton tai, bo qua.
)

echo.

:: Nang cap pip
echo [BUOC 2/6] Nang cap pip, setuptools, wheel...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel --quiet
echo [OK] pip da cap nhat.

echo.

:: Kiem tra torch da cai chua
.venv\Scripts\python.exe -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo [BUOC 3/6] Cai PyTorch 2.8.0 CUDA 12.8 cho Windows...
    echo            Download khoang 2-3 GB. Vui long cho...
    .venv\Scripts\pip.exe install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
    if errorlevel 1 (
        echo [THAT BAI] Cai CUDA torch that bai. Thu cai CPU-only...
        .venv\Scripts\pip.exe install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
    )
) else (
    echo [BUOC 3/6] PyTorch da cai, bo qua.
)

echo.

:: Kiem tra numpy da cai chua
.venv\Scripts\python.exe -c "import soundfile" >nul 2>&1
if errorlevel 1 (
    echo [BUOC 4/6] Cai audio/data packages...
    .venv\Scripts\pip.exe install numpy soundfile librosa pydub --quiet
) else (
    echo [BUOC 4/6] audio/data packages da cai, bo qua.
)

echo.

:: Kiem tra transformers da cai chua
.venv\Scripts\python.exe -c "import transformers" >nul 2>&1
if errorlevel 1 (
    echo [BUOC 5/6] Cai HuggingFace packages...
    .venv\Scripts\pip.exe install "transformers>=5.3.0" accelerate huggingface-hub --quiet
) else (
    echo [BUOC 5/6] HuggingFace packages da cai, bo qua.
)

echo.

:: Kiem tra omnivoice da cai chua
.venv\Scripts\python.exe -c "import omnivoice" >nul 2>&1
if errorlevel 1 (
    echo [BUOC 6/7] Cai omnivoice tu repo local...
    .venv\Scripts\pip.exe install -e . --no-deps --quiet
) else (
    echo [BUOC 6/7] omnivoice da cai, bo qua.
)

echo.

:: Kiem tra gradio da cai chua (can cho UI Phase 2)
.venv\Scripts\python.exe -c "import gradio" >nul 2>&1
if errorlevel 1 (
    echo [BUOC 7/7] Cai Gradio UI framework...
    .venv\Scripts\pip.exe install gradio --quiet
) else (
    echo [BUOC 7/7] Gradio da cai, bo qua.
)

echo.
echo =====================================================
echo  Kiem tra ket qua cai dat...
echo =====================================================
.venv\Scripts\python.exe -c "import torch; import numpy; import soundfile; import transformers; import omnivoice; print('torch:', torch.__version__, '| CUDA:', torch.cuda.is_available()); print('numpy:', numpy.__version__); print('soundfile OK'); print('transformers:', transformers.__version__); print('omnivoice:', omnivoice.__version__)"

echo.
echo =====================================================
echo  Chay test logic mapping...
echo =====================================================
.venv\Scripts\python.exe app_mvp\test_mapping.py

echo.
echo =====================================================
echo  SETUP HOAN TAT!
echo.
echo  De chay TTS:
echo    .venv\Scripts\python.exe app_mvp\cli.py tts --text "Van ban..." --speed normal
echo.
echo  De chay Voice Design:
echo    .venv\Scripts\python.exe app_mvp\cli.py design --text "Van ban..." --voice "giong nam, truong thanh" --speed normal
echo.
echo  De chay Clone Voice (can file voices\sample.wav):
echo    .venv\Scripts\python.exe app_mvp\cli.py clone --text "Van ban..." --ref voices\sample.wav --speed normal
echo.
echo  Hoac chay day du test:
echo    run_core_test.bat
echo =====================================================
pause
