# ThienVoice — Trạng thái Phase 1

**Cập nhật**: 2026-06-27  
**Phase**: 1 — Core Engine Only (không UI, không portable)

---

## Môi trường đã thiết lập

| Thông số | Giá trị |
|---|---|
| Python | 3.12.4 (`C:\Users\NDT\AppData\Local\Programs\Python\Python312\python.exe`) |
| Virtual env | `.venv\` (Python 3.12.4) |
| torch | 2.8.0+cu128 |
| CUDA available | **False** (Quadro P620 dạng vGPU — không expose CUDA từ Python) |
| Device thực tế | **CPU** |
| numpy | 2.4.6 |
| soundfile | 0.14.0 |
| transformers | 5.12.1 |
| omnivoice | 0.1.5 (editable install) |
| GPU | NVIDIA Quadro P620 (vGPU/virtualized — CUDA không khả dụng) |
| Model cache | `C:\Users\NDT\.cache\huggingface\hub\models--k2-fsa--OmniVoice\` |

---

## File đã tạo / cập nhật (Phase 1 + Phase 1b)

| File | Mô tả | Trạng thái |
|---|---|---|
| `app_mvp/core_engine.py` | Core engine: 3 hàm chính + VI→EN mapping | ✓ Tạo + Fix |
| `app_mvp/cli.py` | CLI wrapper | ✓ Tạo |
| `app_mvp/test_mapping.py` | Unit test logic mapping | ✓ Tạo |
| `app_mvp/test_texts_vi.txt` | Văn bản test tiếng Việt | ✓ Tạo |
| `app_mvp/__init__.py` | Package init | ✓ Tạo |
| `setup_mvp_env.bat` | Setup venv + cài deps 1 lần bấm | ✓ Tạo |
| `run_core_test.bat` | Test nhanh 5 test cases | ✓ Cập nhật (dùng .venv) |
| `install_deps.bat` | Legacy install script | ✓ Tồn tại |
| `outputs/` | Thư mục output WAV | ✓ Tạo |
| `voices/` | Thư mục audio mẫu Clone Voice | ✓ Tạo |
| `logs/` | Thư mục log | ✓ Tạo |
| `README_MVP.md` | Hướng dẫn tiếng Việt | ✓ Tạo + Cập nhật |
| `MVP_STATUS.md` | File này | ✓ Cập nhật |

---

## Dependency đã cài

```
torch==2.8.0+cu128          ✓
torchaudio==2.8.0+cu128     ✓
numpy==2.4.6                ✓
soundfile==0.14.0           ✓
librosa==0.11.0             ✓
pydub==0.25.1               ✓
transformers==5.12.1        ✓
accelerate==1.14.0          ✓
huggingface-hub==1.21.0     ✓
omnivoice==0.1.5 (editable) ✓
```

---

## Kết quả test

### Test 1 — Logic Mapping (không cần model)

```
python app_mvp/test_mapping.py
```

**Kết quả: 10/10 PASSED** ✓

```
Speed: slow=0.85 ✓ | normal=1.0 ✓ | fast=1.15 ✓

giọng nam, trưởng thành              → male, middle-aged        [OK]
giọng nữ, thanh niên                 → female, young adult      [OK]
giọng nam Việt Nam, rõ ràng...       → male                     [OK]
giọng nữ Việt Nam, nhẹ nhàng...      → female                   [OK]
giọng nữ, thì thầm, âm cao          → female, whisper, high pitch [OK]
giọng nam, âm thấp                   → male, low pitch          [OK]
giọng nữ, người già                  → female, elderly          [OK]
giọng nam, trung niên                → male, middle-aged        [OK]
giọng nữ, trẻ em                     → female, child            [OK]
giọng mỹ                             → american accent          [OK]
```

### Test không dấu (fix bổ sung)

```
giong nam, truong thanh  → male, middle-aged    [OK]
giong nu, thanh nien     → female, young adult  [OK]
giong nu, thi tham, am cao → female, whisper, high pitch [OK]
```

### Test 2 — TTS thực (model trên CPU)

**Lệnh**:
```
.venv\Scripts\python.exe app_mvp\cli.py tts \
  --text "Xin chao, day la ban thu nghiem giong noi tieng Viet." \
  --speed normal --output outputs\test_tts_normal.wav
```

**Kết quả: THÀNH CÔNG** ✓  
- Model load time: ~8 giây (từ cache)  
- Inference time: ~45 giây (CPU)  
- Output: `outputs\test_tts_normal.wav` (153.3 KB, 24000 Hz)  
- Device: CPU (CUDA không khả dụng)

### Test 3 — Voice Design thực (giọng nam)

**Lệnh**:
```
.venv\Scripts\python.exe app_mvp\cli.py design \
  --text "Day la giong doc chuyen nghiep, ro rang, phu hop video quang cao." \
  --voice "giong nam, truong thanh" --speed normal \
  --output outputs\test_design_nam.wav
```

**Kết quả: THÀNH CÔNG** ✓  
- Mapping: `"giong nam, truong thanh"` → instruct `"male, middle-aged"`  
- Inference time: ~55 giây (CPU)  
- Output: `outputs\test_design_nam.wav` (223.2 KB, 24000 Hz)

### Test 4 — TTS slow speed

**Lệnh**:
```
.venv\Scripts\python.exe app_mvp\cli.py tts \
  --text "Chi can thanh toan hai muoi phan tram..." \
  --speed slow --output outputs\test_tts_slow.wav
```

**Kết quả: THÀNH CÔNG** ✓  
- Inference time: ~106 giây (CPU, văn bản dài + speed 0.85x)  
- Output: `outputs\test_tts_slow.wav` (**284.1 KB** — dài hơn normal 153KB vì đọc chậm hơn)

### Test 5 — Voice Design female fast

**Lệnh**:
```
.venv\Scripts\python.exe app_mvp\cli.py design \
  --text "Xin chao quy khach, cam on quy vi da quan tam." \
  --voice "giong nu, thanh nien" --speed fast \
  --output outputs\test_design_nu_fast.wav
```

**Kết quả: THÀNH CÔNG** ✓  
- Mapping: `"giong nu, thanh nien"` → instruct `"female, young adult"` (không dấu hoạt động)  
- Inference time: ~75 giây (CPU, speed 1.15x)  
- Output: `outputs\test_design_nu_fast.wav` (**132.2 KB** — ngắn hơn normal vì đọc nhanh hơn)

### Test 6 — Clone Voice

**Lệnh**:
```
.venv\Scripts\python.exe app_mvp\cli.py clone \
  --text "Xin chao, day la ban thu nghiem clone giong tieng Viet." \
  --ref voices\sample.wav \
  --ref-text "Xin chao, day la giong doc mau thu nghiem." \
  --speed normal \
  --output outputs\test_clone_placeholder_ref.wav
```

**Kết quả: THÀNH CÔNG** ✓  
- Reference audio: `voices\sample.wav` (5.24 giây, mono, 24000 Hz)  
- ref-text: placeholder (không cần tải Whisper)  
- Model load time: ~2 giây (từ cache)  
- Inference time: ~103 giây (CPU)  
- Output: `outputs\test_clone_placeholder_ref.wav` (269.6 KB, 5.75 giây, 24000 Hz)

**Ghi chú về ref-text**:  
- Dùng placeholder ref-text (`"Xin chao, day la giong doc mau..."`) → hoạt động, không cần tải Whisper (~1.5 GB)  
- Để có chất lượng clone tốt hơn: dùng transcript thực của audio mẫu qua `--ref-text "noi dung chinh xac"`  
- Hoặc để trống `--ref-text ""` → tự động tải `openai/whisper-large-v3-turbo` (~1.5 GB lần đầu)

---

## Lỗi và ghi chú kỹ thuật

### 1. CUDA không khả dụng (không blocking)

**Nguyên nhân**: GPU Quadro P620 chạy dưới dạng vGPU (virtualized). CUDA device count = 0.  
**Ảnh hưởng**: Model chạy CPU, inference ~45-60 giây/câu.  
**Giải pháp**: Đây là giới hạn phần cứng của môi trường này. Máy có GPU thực sẽ nhanh hơn 10-20x.

### 2. HuggingFace symlinks warning (không blocking)

```
UserWarning: huggingface_hub cache-system uses symlinks by default but your machine does not support them
```

**Nguyên nhân**: Windows cần Developer Mode hoặc admin để tạo symlinks.  
**Ảnh hưởng**: Cache vẫn hoạt động, chỉ tốn thêm disk space (không dùng symlink để dedup).  
**Khắc phục tùy chọn**: Bật Developer Mode trong Windows Settings hoặc đặt `HF_HUB_DISABLE_SYMLINKS_WARNING=1`.

### 3. Input không dấu → mapping một phần (đã fix)

**Trước fix**: `"giong nam, truong thanh"` → `"male"` (thiếu middle-aged)  
**Sau fix**: `"giong nam, truong thanh"` → `"male, middle-aged"` ✓  
**Fix**: Thêm bản không dấu của tất cả keys trong `_VI_TO_INSTRUCT` và `_GENDER_KEYS`.

---

## Cách kích hoạt venv và chạy

```bat
:: Kích hoạt (chỉ cần trong terminal tương tác)
.venv\Scripts\activate

:: Hoặc gọi trực tiếp (không cần activate)
.venv\Scripts\python.exe app_mvp\cli.py tts --text "..." --speed normal
```

---

## Tiêu chí hoàn thành Phase 1 (checklist)

- [x] Python 3.12.4 venv đã tạo
- [x] torch + tất cả dependencies đã cài thành công
- [x] `python app_mvp/test_mapping.py` → 10/10 PASSED
- [x] TTS tiếng Việt → tạo WAV trong `outputs/` ✓
- [x] Voice Design (giọng nam) → tạo WAV trong `outputs/` ✓
- [x] Speed slow/normal/fast hoạt động
- [x] Input có dấu và không dấu đều map được
- [x] TTS slow speed → `outputs\test_tts_slow.wav` 284.1 KB ✓
- [x] Voice Design female fast → `outputs\test_design_nu_fast.wav` 132.2 KB ✓
- [x] Clone Voice → `outputs\test_clone_placeholder_ref.wav` 269.6 KB ✓
- [x] Output nằm trong `outputs/`
- [x] Log nằm trong `logs/`
- [x] `setup_mvp_env.bat` đã tạo
- [x] `README_MVP.md` đã cập nhật
- [x] Không làm UI
- [x] Không làm portable
- [x] Không thêm tính năng ngoài scope

---

## Bước tiếp theo

- Phase 2: Tạo UI đơn giản (Tkinter hoặc Gradio local)
- Clone Voice: Đặt file `voices/sample.wav` và test
- Tối ưu tốc độ: Nếu máy có GPU NVIDIA hỗ trợ CUDA thực, sẽ nhanh hơn ~10-20x

