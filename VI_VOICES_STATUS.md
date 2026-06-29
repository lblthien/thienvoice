# Vietnamese Voice Presets — Trạng thái Phase 1D

**Ngày**: 2026-06-27  
**Dataset**: STBack23/omnivoice-vi  
**Local path**: `assets/omnivoice-vi/voices/`

---

## Dataset local path

```
assets/omnivoice-vi/voices/
├── ban_mai/     profile.json  voice.pt(22KB)  ref.mp3   ref_text.txt  ref_text_asr.txt
├── lan_trinh/   profile.json  voice.pt        ref.wav   ref_text.txt
├── ngan_ha/     profile.json  voice.pt        ref.wav   ref_text.txt
├── ngoc_huyen/  profile.json  voice.pt        ref.mp3   ref_text.txt
├── thao_trinh/  profile.json  voice.pt        ref.wav   ref_text.txt
└── tuong_vy/    profile.json  voice.pt(22KB)  ref.wav   ref_text.txt
```

---

## Kiểm tra 6 voice file

Kết quả `cli.py voices`:

| Slug | Display | voice.pt | ref_audio | ref_text | READY |
|---|---|---|---|---|---|
| ban_mai | Ban Mai | OK | ref.mp3 | OK | **READY** |
| lan_trinh | Lan Trinh | OK | ref.wav | OK | **READY** |
| ngan_ha | Ngân Hà | OK | ref.wav | OK | **READY** |
| ngoc_huyen | Ngọc Huyền | OK | ref.mp3 | OK | **READY** |
| thao_trinh | Thảo Trinh | OK | ref.wav | OK | **READY** |
| tuong_vy | Tường Vy | OK | ref.wav | OK | **READY** |

Tất cả 6 voice: `voice.pt` load OK, không cần fallback.

---

## voice.pt format

Tất cả `voice.pt` đều là Python `dict` với 3 keys:
- `ref_audio_tokens`: `torch.Tensor [8, 325]`, dtype `int64`  
- `ref_text`: transcript tiếng Việt
- `ref_rms`: float (volume reference)

Convert sang `VoiceClonePrompt` dataclass trực tiếp, không cần ASR, không cần audio tokenizer.

---

## Settings dùng

```python
language          = "Vietnamese"  # resolve → "vi"
num_step          = 32
guidance_scale    = 2.0
class_temperature = 0.4           # tự nhiên hơn greedy 0.0
speed             = 1.0 (normal)
postprocess_output = True
```

---

## Test đã chạy và kết quả

### Test: CLI tts --voice-preset tuong_vy

```
.venv\Scripts\python.exe app_mvp\cli.py tts \
  --text "Xin chao, day la ban kiem tra giong doc tieng Viet." \
  --voice-preset tuong_vy --speed normal \
  --output outputs\vi_presets\tuong_vy_cli.wav
```

**Kết quả: THÀNH CÔNG** ✓  
- Gen time: ~339 giây (CPU)  
- Output: `outputs/vi_presets/tuong_vy_cli.wav` — 2.45s audio, 24000Hz

### Test: test_vi_voice_quick.py (tuong_vy + ban_mai)

```
.venv\Scripts\python.exe app_mvp\test_vi_voice_quick.py
```

| Voice | Kết quả | Gen time | ref_tokens | Output |
|---|---|---|---|---|
| tuong_vy | **THÀNH CÔNG** ✓ | 422.7s | (8, 325) ref_rms=0.1297 | `outputs/vi_presets/tuong_vy.wav` 7.18s, 336.6 KB |
| ban_mai  | **THÀNH CÔNG** ✓ | 330.4s | (8, 399) ref_rms=0.1322 | `outputs/vi_presets/ban_mai.wav` 7.64s, 358.2 KB |

---

## Kết luận kỹ thuật

### So sánh pipeline

| | TTS legacy (random) | TTS preset (mới) | Voice Design |
|---|---|---|---|
| **Hàm** | `generate_random_tts_legacy()` | `generate_preset_tts()` / `generate_tts()` | `generate_voice_design()` |
| **CLI** | (không còn mặc định) | `cli.py tts --voice-preset <slug>` | `cli.py design` |
| **Giọng** | Model tự chọn ngẫu nhiên | Fixed, nhất quán | Controlled attributes |
| **Chất lượng VI** | Kém, không kiểm soát | **Tốt — dùng làm default** | EXPERIMENTAL |
| **Load time** | — | voice.pt < 0.1s | — |
| **Phụ thuộc ASR** | Không | Không | Không |
| **class_temperature** | 0.0 (greedy) | **0.4** (tự nhiên hơn) | 0.0 |

### Thay đổi trong Phase 1D

- `generate_tts()` → gọi `generate_preset_tts("tuong_vy")` thay vì random voice
- `generate_random_tts_legacy()` → giữ lại để debug
- `cli.py voices` → liệt kê 6 giọng với trạng thái
- `cli.py tts` → thêm `--voice-preset` (mặc định `tuong_vy`)
- `cli.py design` → đánh dấu `[EXPERIMENTAL]`

---

## Lỗi còn tồn tại

- CPU inference: ~4 phút/câu — cần GPU NVIDIA thật để dùng thực tế
- `ban_mai` và `ngoc_huyen` dùng ref.mp3 (không phải WAV) — fallback path handle được, không lỗi
- Chưa test `--all` 6 giọng (CPU tốn ~25-30 phút — có thể chạy khi cần)
- `ban_mai` và `ngoc_huyen` dùng `ref.mp3` (không phải WAV) — đã test ban_mai OK
