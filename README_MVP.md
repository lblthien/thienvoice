# OmniVoice MVP — Hướng dẫn sử dụng

## Chạy giao diện Desktop (Phase 2)

```bat
run_ui.bat
```

Trình duyệt tự mở tại `http://127.0.0.1:7860`. Để dừng: `Ctrl+C`.

### 4 tab trong UI

| Tab | Chức năng |
|---|---|
| 🎙️ Text to Speech | Nhập văn bản → chọn giọng → tạo audio |
| 🔁 Clone Voice | Upload audio mẫu → clone giọng sang văn bản mới |
| 🧪 Voice Design [Experimental] | Mô tả giọng bằng tiếng Việt → tạo audio thử |
| ⚙️ Hệ thống | Kiểm tra môi trường, voice preset, mở thư mục outputs |

### Tab Text to Speech

1. Nhập văn bản tiếng Việt
2. Chọn giọng (mặc định: Tường Vy)
3. Chọn tốc độ: Bình thường / Chậm / Nhanh
4. Nhấn **Tạo giọng đọc**
5. Nghe thử trong audio player — file lưu tự động vào `outputs/`

> ⚠️ **CPU**: Mỗi câu mất 3–7 phút trên CPU. Status hiển thị trong khi chờ.

### Tab Clone Voice

1. Nhập văn bản cần đọc
2. Upload file audio mẫu (WAV/MP3, 3–10 giây)
3. Nhập transcript của audio mẫu (tùy chọn — để trống dùng Whisper ASR ~1.5GB)
4. Nhấn **Tạo giọng clone**

### Tab Voice Design [Experimental]

1. Nhập văn bản
2. Nhập mô tả giọng: `giong nam, truong thanh` hoặc `giong nu, thanh nien`
3. Nhấn **Tạo thử**

> ⚠️ Chất lượng tiếng Việt có thể không ổn định. Dùng TTS preset thay thế.

### Tab Hệ thống

- Nhấn **Kiểm tra hệ thống** để xem Python, torch, CUDA, model cache, 6 voice status
- Nhấn **Mở thư mục outputs** để xem file WAV đã tạo

Xem chi tiết: [`UI_STATUS.md`](UI_STATUS.md)

---

## Voice Preset Tiếng Việt (Phase 1D)

6 voice preset tiếng Việt từ `STBack23/omnivoice-vi`. Đây là cách TTS mặc định — giọng nhất quán, không random.

### Setup (1 lần)

```bat
:: Tải toàn bộ dataset (6 giọng, ~5 giây)
.venv\Scripts\python.exe app_mvp\download_tuong_vy.py
```

### Liệt kê giọng có sẵn

```bat
.venv\Scripts\python.exe app_mvp\cli.py voices
```

### TTS bằng voice preset

```bat
:: Mặc định: giọng Tường Vy
.venv\Scripts\python.exe app_mvp\cli.py tts --text "Văn bản tiếng Việt..." --speed normal

:: Chọn giọng cụ thể
.venv\Scripts\python.exe app_mvp\cli.py tts --text "Văn bản..." --voice-preset ban_mai --speed normal
.venv\Scripts\python.exe app_mvp\cli.py tts --text "Văn bản..." --voice-preset lan_trinh --speed normal
```

Voice preset hợp lệ: `ban_mai`, `lan_trinh`, `ngan_ha`, `ngoc_huyen`, `thao_trinh`, `tuong_vy`

### Test nhanh 2 giọng (tuong_vy + ban_mai)

```bat
.venv\Scripts\python.exe app_mvp\test_vi_voice_quick.py
```

Output: `outputs/vi_presets/tuong_vy.wav`, `outputs/vi_presets/ban_mai.wav`

> **CPU note**: Mỗi câu ~4 phút trên CPU. GPU NVIDIA thật sẽ nhanh hơn 10-20x.

### Test 1 giọng cụ thể

```bat
.venv\Scripts\python.exe app_mvp\test_vi_voice_presets.py --voice tuong_vy
```

### Test đủ 6 giọng (CPU: ~25-30 phút)

```bat
.venv\Scripts\python.exe app_mvp\test_vi_voice_presets.py --all
```

Output: `outputs/vi_presets/*.wav`  
Xem kết quả: [`VI_VOICES_STATUS.md`](VI_VOICES_STATUS.md)

---

## Tổng quan repo

Repo này là **OmniVoice** — model TTS đa ngôn ngữ (600+ ngôn ngữ) của Xiaomi AI Lab / Next-gen Kaldi team, sử dụng kiến trúc Diffusion Language Model.

- **Framework**: Python thuần + HuggingFace Transformers + Gradio (cho demo web)  
- **Model**: `k2-fsa/OmniVoice` trên HuggingFace Hub (~3–5 GB, tải tự động lần đầu)  
- **Audio tokenizer**: `eustlb/higgs-audio-v2-tokenizer` (tích hợp trong model)  
- **Sampling rate**: 24,000 Hz  
- **Hỗ trợ tiếng Việt**: có, language code = `"vi"`

## Cấu trúc thư mục MVP

```
OmniVoice/
├── app_mvp/
│   ├── core_engine.py      ← Module core: 3 hàm chính
│   ├── cli.py              ← CLI test từ terminal
│   └── test_texts_vi.txt   ← Văn bản tiếng Việt test sẵn
├── outputs/                ← File WAV output (tạo tự động)
├── voices/                 ← Đặt file audio mẫu cho Clone Voice ở đây
├── logs/                   ← Log lỗi (tạo tự động)
├── run_core_test.bat       ← Script test nhanh trên Windows
└── omnivoice/              ← Source code gốc (KHÔNG sửa)
```

## Yêu cầu hệ thống

- Python 3.10+
- PyTorch 2.4+ (CUDA hoặc CPU)
- RAM: ≥ 8 GB (CUDA: ≥ 6 GB VRAM khuyến nghị)
- Kết nối internet lần đầu chạy (tải model ~3–5 GB)

### Cài đặt dependencies

```bash
# Cài đặt với pip (sau khi vào thư mục repo)
pip install -e .

# Hoặc với uv (nhanh hơn, khuyến nghị)
uv sync
```

## Cách load model

Model load tự động từ HuggingFace khi gọi lần đầu:

```python
from omnivoice.models.omnivoice import OmniVoice
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda")
```

Model được cache tại `~/.cache/huggingface/hub/`. Lần sau không cần tải lại.

---

## Cách chạy TTS

### Qua CLI (khuyến nghị để test)

```bash
python app_mvp/cli.py tts --text "Xin chào, đây là bản thử nghiệm." --speed normal
```

### Qua Python

```python
from app_mvp.core_engine import generate_tts

path = generate_tts(
    text="Xin chào, đây là bản thử nghiệm giọng nói tiếng Việt.",
    speed="normal",
    output_path="outputs/my_tts.wav",
)
print(f"Đã lưu: {path}")
```

---

## Cách chạy Clone Voice

Cần có file audio mẫu (WAV hoặc MP3, khuyến nghị 3–10 giây).

**Bước 1**: Chuẩn bị file mẫu  
Đặt file WAV hoặc MP3 của giọng bạn muốn clone vào:
```
voices/sample.wav
```
Yêu cầu: âm thanh rõ ràng, không nhiễu, 3–10 giây là tốt nhất.

**Bước 2**: Chạy Clone Voice

```bash
# Dùng .venv (khuyến nghị)
.venv\Scripts\python.exe app_mvp\cli.py clone ^
  --text "Xin chào, đây là giọng clone." ^
  --ref voices\sample.wav ^
  --ref-text "" ^
  --speed normal
```

- `--ref-text ""`: Để trống → tự động nhận dạng transcript bằng Whisper ASR  
  *(lần đầu tải thêm ~1.5 GB cho `openai/whisper-large-v3-turbo`)*
- `--ref-text "Nội dung audio mẫu."`: Cung cấp transcript thủ công → nhanh hơn, bỏ qua ASR

**Ví dụ đầy đủ với transcript**:
```bash
.venv\Scripts\python.exe app_mvp\cli.py clone ^
  --text "Vlasta Premier Phu Thuan so huu vi tri noi bat." ^
  --ref voices\sample.wav ^
  --ref-text "Xin chao quy vi, toi la nguoi doc mau." ^
  --speed normal ^
  --output outputs\clone_result.wav
```

### Qua Python

```python
from app_mvp.core_engine import generate_clone

path = generate_clone(
    text="Xin chào, đây là giọng clone.",
    reference_audio_path="voices/sample.wav",
    reference_transcript="",   # để trống để auto ASR
    speed="normal",
    output_path="outputs/clone.wav",
)
```

---

## Cách chạy Voice Design

Mô tả giọng bằng **tiếng Việt** — hệ thống tự động map sang keyword OmniVoice.

```bash
python app_mvp/cli.py design \
  --text "Vlasta Premier Phú Thuận sở hữu vị trí nổi bật trên cung đường Đào Trí, Quận 7." \
  --voice "giọng nam, trưởng thành" \
  --speed normal
```

### Ví dụ mô tả giọng hợp lệ

| Mô tả tiếng Việt | Instruct OmniVoice |
|---|---|
| `giọng nam, trưởng thành` | `male, middle-aged` |
| `giọng nữ, thanh niên` | `female, young adult` |
| `giọng nam, âm thấp, thì thầm` | `male, low pitch, whisper` |
| `giọng nữ, âm cao` | `female, high pitch` |
| `giọng nam, trung niên` | `male, middle-aged` |
| `giọng nữ, người già` | `female, elderly` |

> **Lưu ý**: Các từ như *rõ ràng*, *chuyên nghiệp*, *tự nhiên*, *nhẹ nhàng*, *Việt Nam* không có trong từ điển OmniVoice — sẽ bị bỏ qua tự động (không gây lỗi).

### Keyword hợp lệ hoàn chỉnh

- **Giới tính**: `male` / `female`
- **Tuổi**: `child`, `teenager`, `young adult`, `middle-aged`, `elderly`
- **Độ cao giọng**: `very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch`
- **Phong cách**: `whisper`
- **Giọng tiếng Anh**: `american accent`, `british accent`, `australian accent`, `canadian accent`, `indian accent`, `japanese accent`, `korean accent`, `russian accent`, `portuguese accent`, `chinese accent`

---

## Cách chỉnh Speed

| Tham số | Hệ số | Mô tả |
|---|---|---|
| `slow` | 0.85x | Đọc chậm hơn |
| `normal` | 1.0x | Tốc độ chuẩn |
| `fast` | 1.15x | Đọc nhanh hơn |

Tất cả lệnh CLI đều có `--speed slow|normal|fast`.

---

## Output nằm ở đâu

Tất cả file WAV output lưu vào thư mục `outputs/`:

```
outputs/
├── tts_20250101_120000.wav
├── clone_20250101_120500.wav
└── design_20250101_121000.wav
```

Tên file bao gồm timestamp để tránh ghi đè. Có thể chỉ định tên cụ thể bằng `--output`.

---

## Lỗi thường gặp

### 1. `No module named 'omnivoice'`
```
pip install -e .
```
Chạy từ thư mục gốc repo (nơi có `pyproject.toml`).

### 2. `CUDA out of memory`
Thêm `--model k2-fsa/OmniVoice` và chạy trên CPU:
```python
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
```
Hoặc giảm `num_step` xuống 16 để tiết kiệm VRAM.

### 3. Clone Voice lỗi `File không tồn tại`
Đặt file WAV/MP3 vào đường dẫn `voices/sample.wav` trước khi chạy.

### 4. `ValueError: Unsupported instruct items`
Mô tả giọng có chứa keyword tiếng Việt không được nhận dạng. Hãy dùng ví dụ trong bảng ở trên, hoặc kiểm tra log để biết từ nào bị bỏ qua.

### 5. Lần đầu chạy rất lâu
Model ~3–5 GB cần tải từ internet. Sau lần đầu, model được cache và không tải lại. Kiểm tra tiến độ trong log.

### 6. Audio output bị lỗi / không nghe được
Thử giảm `num_step=16`, hoặc xem log trong `logs/` để debug.
