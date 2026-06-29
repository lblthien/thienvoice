---
license: apache-2.0
language:
- vi
tags:
- text-to-speech
- tts
- voice-cloning
- vietnamese
- srt
- dubbing
- omnivoice
pretty_name: OmniVoice Vietnamese Voices
size_categories:
- n<1K
---

# OmniVoice VI — Giọng Việt + SRT lồng tiếng

Dataset chứa **6 giọng tiếng Việt** và công cụ `speak.py` để chạy trên **Google Colab** với [OmniVoice](https://huggingface.co/k2-fsa/OmniVoice).

## Giọng có sẵn

| Slug | Tên |
|------|-----|
| `ban_mai` | Ban Mai |
| `lan_trinh` | Lan Trinh |
| `ngan_ha` | Ngan Ha |
| `ngoc_huyen` | Ngoc Huyen |
| `thao_trinh` | Thao Trinh |
| `tuong_vy` | Tuong Vy |

Mỗi giọng gồm `profile.json`, `voice.pt` (prompt cache), audio mẫu và `ref_text.txt`.

## Chạy trên Colab

1. Mở notebook `colab/Omivoice_VI_Colab.ipynb`
2. Đặt `HF_REPO = "<repo-này>"`
3. Runtime → GPU → chạy từng cell

## Cấu trúc

```
├── voices/<slug>/     # profile + voice.pt + ref audio
├── tools/speak.py     # TTS + SRT pipeline
└── colab/             # Notebook Colab
```

## SRT merge modes

- **`native`** (mặc định): model nói nhanh native, tràn vào khoảng trống sau cue, không cắt ngắt
- **`cascade`**: giữ tốc độ tự nhiên, cue dài đẩy cue sau
- **`fit`**: kéo nén tín hiệu vừa khung SRT
- **`strict`**: ghép theo timestamp (có thể cắt audio)

## Model gốc

- [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) — tự tải khi chạy lần đầu (~GB VRAM T4)

## License

Apache-2.0 (theo OmniVoice upstream).
