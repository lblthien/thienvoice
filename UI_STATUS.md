# OmniVoice MVP — Trạng thái Phase 2 UI

**Ngày**: 2026-06-27  
**Phase**: 2 — Desktop UI (Gradio local)

---

## Framework UI đã chọn

**Gradio 6.19.0** — local web UI, chạy tại `http://127.0.0.1:7860`

**Lý do chọn Gradio**:
- Đã là dependency trong `pyproject.toml` của OmniVoice gốc
- Không cần thêm framework phức tạp (không Tauri/Electron)
- Audio player tích hợp sẵn
- Dễ wrap thành portable sau này (chạy trong background + mở browser tự động)
- API đơn giản, ít lỗi trên Windows

---

## File đã tạo / sửa

| File | Mô tả |
|---|---|
| `app_ui/app.py` | UI chính — 4 tab, gọi app_mvp core |
| `run_ui.bat` | Launcher 1 lần bấm — kiểm tra .venv, voice preset, rồi chạy |
| `.claude/launch.json` | Config preview server (dành cho dev) |

---

## Cách chạy UI

```bat
:: Cách 1: Double-click (khuyến nghị cho user)
run_ui.bat

:: Cách 2: Terminal
.venv\Scripts\python.exe app_ui\app.py
```

Trình duyệt tự mở tại `http://127.0.0.1:7860`.  
Để dừng: nhấn `Ctrl+C` trong terminal.

---

## Tính năng đã hoạt động

### Verified khi chạy

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| UI khởi động | ✓ | `http://127.0.0.1:7860` HTTP 200 |
| Tab Text to Speech | ✓ | Dropdown 6 giọng, speed 3 mức |
| Tab Clone Voice | ✓ | Upload audio, transcript tùy chọn |
| Tab Voice Design | ✓ | Đánh dấu EXPERIMENTAL |
| Tab Hệ thống | ✓ | System check, nút mở folder |
| System check logic | ✓ | Import test OK — 6 voices READY |
| CSS warning (Gradio 6) | ✓ fixed | Chuyển `css` vào `launch()` |

### UI logic verified (import test)

```
6 voices: Tường Vy, Ban Mai, Lan Trinh, Ngân Hà, Ngọc Huyền, Thảo Trinh — tất cả READY
System check: Python 3.12.4, torch 2.8.0+cu128, CUDA: Không, Model cache: Có, voices: Có
```

---

## Tính năng chưa test end-to-end qua UI

| Tính năng | Lý do chưa test | Cách test |
|---|---|---|
| TTS qua UI → WAV | CPU chậm (4 phút/câu) | Nhấn nút TTS trong browser, đợi |
| Clone Voice qua UI | Cần upload file | Dùng `voices/sample.wav` |
| Voice Design qua UI | CPU chậm | Nhấn nút Design |
| Audio player play | Cần browser | Mở http://127.0.0.1:7860 và test |
| Nút mở thư mục | Windows explorer | Nhấn nút trong Tab Hệ thống |

Các hàm backend đã được test thực qua CLI Phase 1 — UI chỉ là wrapper gọi lại cùng hàm.

---

## Lỗi còn tồn tại

| Lỗi | Mức độ | Mô tả | Khắc phục |
|---|---|---|---|
| CPU inference ~4 phút/câu | Cao | Không phải lỗi — giới hạn phần cứng | GPU NVIDIA thật = 10-20x nhanh hơn |
| Gradio chạy trong browser | Thấp | Không phải native app window | Phase 3: wrap bằng pywebview/webview2 |
| Port 7860 cố định | Thấp | Conflict nếu port đã dùng | Thêm `--port` flag nếu cần |
| inbrowser=True phụ thuộc browser mặc định | Thấp | Có thể không mở trên một số máy | Copy URL thủ công |

---

## Kiến trúc UI

```
run_ui.bat
  └── .venv/Scripts/python.exe app_ui/app.py
        └── Gradio Blocks (4 tabs)
              ├── Tab TTS → fn_tts() → generate_preset_tts() [app_mvp/core_engine.py]
              ├── Tab Clone → fn_clone() → generate_clone() [app_mvp/core_engine.py]
              ├── Tab Design → fn_design() → generate_voice_design() [app_mvp/core_engine.py]
              └── Tab System → fn_system_check() [inline — no model load]
```

Không nhân bản logic model. Tất cả gọi qua `app_mvp/core_engine.py`.

---

## Lưu ý CPU inference chậm

- Model chạy trên CPU (GPU Quadro P620 dạng vGPU — CUDA không khả dụng)
- TTS 1 câu ngắn: ~3–4 phút
- TTS 2 câu dài: ~7 phút
- UI hiển thị message "Đang tạo audio, máy CPU có thể mất vài phút..." để user không tưởng bị đơ
- Status cập nhật real-time qua Gradio streaming generator

---

## Bước tiếp theo để portable (Phase 3)

1. **Thêm `pywebview`** để bọc Gradio trong cửa sổ native (không cần browser)
2. **Đóng gói bằng PyInstaller** thành `.exe` 1 file
3. **Bundle model** hoặc hướng dẫn tải lần đầu
4. **Tạo icon** và shortcut desktop
5. **Test trên máy khác** không có Python
