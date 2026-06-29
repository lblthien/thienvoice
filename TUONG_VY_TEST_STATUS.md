# Kết quả Test Voice Preset tuong_vy

**Ngày**: 2026-06-27  
**Dataset**: STBack23/omnivoice-vi  
**Voice**: tuong_vy (Tường Vy)

---

## Dataset tải được chưa

**THÀNH CÔNG** ✓

```
python app_mvp/download_tuong_vy.py
```

Tải về `assets/omnivoice-vi/` trong ~5 giây (28 files, dataset nhỏ).

---

## Đường dẫn local

```
assets/omnivoice-vi/
└── voices/
    └── tuong_vy/
        ├── profile.json   (0.3 KB)
        ├── voice.pt       (22.2 KB)
        ├── ref.wav        (363.4 KB)
        └── ref_text.txt   (0.3 KB)
```

---

## File tuong_vy tìm thấy

| File | Tìm thấy | Kích thước | Ghi chú |
|---|---|---|---|
| `profile.json` | ✓ | 0.3 KB | language=Vietnamese, model=k2-fsa/OmniVoice |
| `voice.pt` | ✓ | 22.2 KB | dict: {ref_audio_tokens, ref_text, ref_rms} |
| `ref_text.txt` | ✓ | 0.3 KB | Transcript tiếng Việt đầy đủ |
| `ref.wav` | ✓ | 363.4 KB | Audio mẫu giọng Tường Vy |

---

## voice.pt load được không

**THÀNH CÔNG — không cần fallback** ✓

`voice.pt` là Python `dict` với 3 keys:

| Key | Giá trị |
|---|---|
| `ref_audio_tokens` | `torch.Tensor` shape `[8, 325]`, dtype `int64` |
| `ref_text` | `'Mau mau xem mau. Nghe nói Thất công chúa đến đây...'` |
| `ref_rms` | `0.12971411645412445` |

Được convert sang `VoiceClonePrompt` dataclass trực tiếp — không qua ASR, không qua audio tokenizer.

---

## Fallback

Không cần dùng fallback. `voice.pt` load thành công.

Fallback được implement sẵn trong `test_tuong_vy_preset.py` nếu `voice.pt` bị lỗi: dùng `model.create_voice_clone_prompt(ref_audio, ref_text)`.

---

## Lệnh đã chạy

```bash
# Bước 1: Tải dataset
.venv\Scripts\python.exe app_mvp\download_tuong_vy.py

# Bước 2: Generate audio
.venv\Scripts\python.exe app_mvp\test_tuong_vy_preset.py
```

---

## Output WAV

**THÀNH CÔNG** ✓

| Thông số | Giá trị |
|---|---|
| File | `outputs/tuong_vy_test.wav` |
| Kích thước | 328.2 KB |
| Duration | 7.00 giây |
| Sample rate | 24,000 Hz |
| Channels | 1 (mono) |

---

## Thời gian generate

| Bước | Thời gian |
|---|---|
| Model load (từ cache) | 2.8 giây |
| voice.pt load + convert | < 0.1 giây |
| Language resolve | < 0.1 giây |
| **Inference (CPU)** | **260.4 giây** (~4.3 phút) |

Text test: 2 câu tiếng Việt (~160 ký tự) → 7 giây audio.

---

## Settings đã dùng

```python
language        = "Vietnamese"   # → resolve thành "vi"
num_step        = 32
guidance_scale  = 2.0
class_temperature = 0.4
speed           = 1.0
postprocess_output = True
# Không ép duration
# Không dùng instruct (Voice Design)
```

---

## Lỗi

Không có lỗi. Một warning không blocking:

```
UserWarning: local_dir_use_symlinks argument is deprecated
```
→ Đã fix trong `download_tuong_vy.py`.

---

## Kết luận kỹ thuật: Pipeline preset khác gì TTS random voice cũ

| Tiêu chí | TTS random voice (Phase 1) | Voice preset tuong_vy |
|---|---|---|
| **Nguồn giọng** | Model tự chọn ngẫu nhiên | Fixed: giọng Tường Vy từ dataset VI |
| **Input** | text + language + instruct | text + VoiceClonePrompt |
| **VoiceClonePrompt** | Tạo từ ref.wav lúc runtime (qua audio tokenizer) | Pre-computed, load từ voice.pt (~0.1s) |
| **class_temperature** | 0.0 (greedy) | 0.4 (thêm randomness → tự nhiên hơn) |
| **Phụ thuộc ASR** | Không (TTS) hoặc có (Clone) | Không (đã encode sẵn) |
| **Chất lượng giọng** | Không kiểm soát được | Ổn định, đúng giọng VI |
| **Thời gian chuẩn bị** | Tải Whisper nếu clone | Load voice.pt < 0.1 giây |
| **Tái sử dụng** | Không cache được | voice.pt dùng nhiều lần |

**Ưu điểm rõ ràng của preset**: giọng nhất quán, không cần ASR, không cần audio mẫu lúc chạy, load nhanh.

---

## Bước tiếp theo

1. Nghe thử `outputs/tuong_vy_test.wav` để đánh giá chất lượng giọng thực tế
2. Nếu OK → tích hợp 6 giọng còn lại (ban_mai, lan_trinh, ngan_ha, ngoc_huyen, thao_trinh)
3. Phase 2 UI có thể dùng voice preset làm default thay TTS random
