@echo off
chcp 65001 >nul
setlocal

echo =====================================================
echo  ThienVoice - Core Engine Test
echo  Chay tu thu muc: %CD%
echo =====================================================
echo.

:: Dung Python trong .venv neu co, fallback sang python global
if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
    echo [CANH BAO] Khong tim thay .venv. Dung Python toan cuc.
    echo            Chay setup_mvp_env.bat truoc de cai dependency.
)
echo [INFO] Python: %PYTHON%

:: Tao thu muc outputs va logs neu chua co
if not exist outputs mkdir outputs
if not exist logs mkdir logs
if not exist voices mkdir voices

echo.
echo [THONG TIN] Model se duoc tai tu HuggingFace lan dau chay.
echo             k2-fsa/OmniVoice  ~ 3-5 GB
echo             Ket noi internet la bat buoc.
echo             Sau lan dau, model duoc cache lai, khong tai lai nua.
echo.

:: ====================================================
:: TEST 1: TTS - giong mac dinh
:: ====================================================
echo =====================================================
echo TEST 1: Text to Speech (giong mac dinh)
echo =====================================================
echo Van ban: "Xin chao, day la ban thu nghiem giong noi tieng Viet."
echo.

%PYTHON% app_mvp\cli.py tts ^
  --text "Xin chao, day la ban thu nghiem giong noi tieng Viet." ^
  --speed normal ^
  --output outputs\test1_tts_normal.wav

if errorlevel 1 (
    echo [THAT BAI] TEST 1 that bai. Xem log trong thu muc logs\
) else (
    echo [THANH CONG] TEST 1 xong. File: outputs\test1_tts_normal.wav
)

echo.

:: ====================================================
:: TEST 2: TTS - toc do slow
:: ====================================================
echo =====================================================
echo TEST 2: TTS toc do cham (slow = 0.85x)
echo =====================================================
echo.

%PYTHON% app_mvp\cli.py tts ^
  --text "Vlasta Premier Phu Thuan so huu vi tri noi bat tren cung duong Dao Tri, Quan 7." ^
  --speed slow ^
  --output outputs\test2_tts_slow.wav

if errorlevel 1 (
    echo [THAT BAI] TEST 2 that bai.
) else (
    echo [THANH CONG] TEST 2 xong. File: outputs\test2_tts_slow.wav
)

echo.

:: ====================================================
:: TEST 3: TTS - toc do fast
:: ====================================================
echo =====================================================
echo TEST 3: TTS toc do nhanh (fast = 1.15x)
echo =====================================================
echo.

%PYTHON% app_mvp\cli.py tts ^
  --text "Chi can thanh toan hai muoi phan tram den khi nhan nha, an han lai goc len den bay nam." ^
  --speed fast ^
  --output outputs\test3_tts_fast.wav

if errorlevel 1 (
    echo [THAT BAI] TEST 3 that bai.
) else (
    echo [THANH CONG] TEST 3 xong. File: outputs\test3_tts_fast.wav
)

echo.

:: ====================================================
:: TEST 4: Voice Design - giong nam
:: ====================================================
echo =====================================================
echo TEST 4: Voice Design - giong nam, truong thanh
echo =====================================================
echo.

%PYTHON% app_mvp\cli.py design ^
  --text "Day la giong doc chuyen nghiep, ro rang, phu hop video quang cao bat dong san." ^
  --voice "giong nam, truong thanh" ^
  --speed normal ^
  --output outputs\test4_design_nam.wav

if errorlevel 1 (
    echo [THAT BAI] TEST 4 that bai.
) else (
    echo [THANH CONG] TEST 4 xong. File: outputs\test4_design_nam.wav
)

echo.

:: ====================================================
:: TEST 5: Voice Design - giong nu
:: ====================================================
echo =====================================================
echo TEST 5: Voice Design - giong nu, thanh nien
echo =====================================================
echo.

%PYTHON% app_mvp\cli.py design ^
  --text "Xin chao quy khach, cam on quy vi da quan tam den du an cua chung toi." ^
  --voice "giong nu, thanh nien" ^
  --speed normal ^
  --output outputs\test5_design_nu.wav

if errorlevel 1 (
    echo [THAT BAI] TEST 5 that bai.
) else (
    echo [THANH CONG] TEST 5 xong. File: outputs\test5_design_nu.wav
)

echo.

:: ====================================================
:: TEST 6 (TUY CHON): Clone Voice
:: ====================================================
echo =====================================================
echo TEST 6 (TUY CHON): Clone Voice
echo =====================================================

if exist voices\sample.wav (
    echo Tim thay voices\sample.wav - Chay Clone Voice test...
    echo.
    %PYTHON% app_mvp\cli.py clone ^
      --text "Xin chao, day la thu nghiem clone giong noi." ^
      --ref voices\sample.wav ^
      --ref-text "" ^
      --speed normal ^
      --output outputs\test6_clone.wav

    if errorlevel 1 (
        echo [THAT BAI] TEST 6 that bai. Xem log.
    ) else (
        echo [THANH CONG] TEST 6 xong. File: outputs\test6_clone.wav
    )
) else (
    echo [BO QUA] voices\sample.wav chua co.
    echo          De chay Clone Voice, dat file WAV mau vao: voices\sample.wav
    echo          Yeu cau: file WAV/MP3, khuyen nghi 3-10 giay.
    echo          Sau do chay lenh:
    echo.
    echo          %PYTHON% app_mvp\cli.py clone ^
    echo            --text "Van ban can doc" ^
    echo            --ref voices\sample.wav ^
    echo            --ref-text "" ^
    echo            --speed normal
)

echo.
echo =====================================================
echo  TONG KET TEST
echo =====================================================
echo  File output nam trong: outputs\
echo  File log nam trong   : logs\
echo.
echo  Mo file WAV bang Windows Media Player hoac VLC.
echo =====================================================
pause

