@echo off
chcp 65001 >nul
echo =====================================================
echo  OmniVoice MVP - Cai dat Dependencies
echo =====================================================
echo.
echo Python hien tai:
python --version
echo.

:: Kiem tra pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay pip. Vui long cai lai Python co kem pip.
    pause
    exit /b 1
)

echo [BUOC 1] Nang cap pip...
python -m pip install --upgrade pip

echo.
echo [BUOC 2] Cai dat PyTorch voi CUDA 12.8 (Windows)...
echo          (Neu may khong co GPU NVIDIA, thay bang: pip install torch torchaudio)
echo.
pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128

echo.
echo [BUOC 3] Cai dat cac package con lai...
pip install transformers>=5.3.0 accelerate pydub soundfile librosa numpy huggingface-hub

echo.
echo [BUOC 4] Cai dat omnivoice tu repo local...
pip install -e .

echo.
echo =====================================================
echo  Kiem tra cai dat...
echo =====================================================
python -c "import torch; print('torch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"
python -c "import soundfile; print('soundfile OK')"
python -c "import transformers; print('transformers:', transformers.__version__)"
python -c "import omnivoice; print('omnivoice:', omnivoice.__version__)"

echo.
echo =====================================================
echo  XONG! Gio co the chay: run_core_test.bat
echo =====================================================
pause
