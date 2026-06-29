"""ThienVoice — Giao diện Desktop (Gradio local).

Chạy:
    .venv\\Scripts\\python.exe app_ui\\app.py
    Sau đó mở trình duyệt tại: http://localhost:7860

Gọi lại core từ app_mvp — không nhân bản logic model.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import gradio as gr

os.makedirs(_REPO_ROOT / "outputs", exist_ok=True)
os.makedirs(_REPO_ROOT / "logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            _REPO_ROOT / "logs" / f"ui_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
    ],
    force=True,
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice preset metadata (không import core để UI load nhanh)
# ---------------------------------------------------------------------------
VI_VOICES = [
    ("Tường Vy",  "tuong_vy"),
    ("Ban Mai",   "ban_mai"),
    ("Lan Trinh", "lan_trinh"),
    ("Ngân Hà",   "ngan_ha"),
    ("Ngọc Huyền","ngoc_huyen"),
    ("Thảo Trinh","thao_trinh"),
]
VOICE_CHOICES  = [f"{name} ({slug})" for name, slug in VI_VOICES]
VOICE_DEFAULT  = VOICE_CHOICES[0]
SPEED_CHOICES  = ["Bình thường", "Chậm", "Nhanh"]
SPEED_MAP      = {"Bình thường": "normal", "Chậm": "slow", "Nhanh": "fast"}

OUTPUTS_DIR = _REPO_ROOT / "outputs"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _voice_slug(choice: str) -> str:
    """Trích slug từ 'Tường Vy (tuong_vy)' → 'tuong_vy'."""
    return choice.split("(")[-1].rstrip(")")


def _speed_key(label: str) -> str:
    return SPEED_MAP.get(label, "normal")


# ---------------------------------------------------------------------------
# TAB A — Text to Speech
# ---------------------------------------------------------------------------
def fn_tts(text: str, voice_choice: str, speed_label: str):
    if not text or not text.strip():
        yield "Vui lòng nhập văn bản.", None, ""
        return

    slug  = _voice_slug(voice_choice)
    speed = _speed_key(speed_label)
    out   = str(OUTPUTS_DIR / f"ui_tts_{_ts()}.wav")

    yield f"⏳ Đang tải model và tạo audio bằng giọng {voice_choice}...\n(CPU có thể mất vài phút, vui lòng chờ)", None, ""

    try:
        from app_mvp.core_engine import generate_preset_tts
        path = generate_preset_tts(
            text=text.strip(),
            voice_preset=slug,
            speed=speed,
            output_path=out,
        )
        log.info("TTS OK: %s", path)
        yield f"✅ Hoàn tất!\nFile: {path}", path, path
    except FileNotFoundError as e:
        msg = (
            f"❌ Lỗi: Chưa tải voice preset.\n"
            f"Chạy: .venv\\Scripts\\python.exe app_mvp\\download_tuong_vy.py\n\n{e}"
        )
        log.error("TTS FileNotFoundError: %s", e)
        yield msg, None, ""
    except Exception as e:
        log.exception("TTS error")
        yield f"❌ Lỗi: {type(e).__name__}: {e}", None, ""


# ---------------------------------------------------------------------------
# TAB B — Clone Voice
# ---------------------------------------------------------------------------
def fn_clone(text: str, ref_audio, ref_transcript: str, speed_label: str):
    if not text or not text.strip():
        yield "Vui lòng nhập văn bản.", None, ""
        return
    if ref_audio is None:
        yield "Vui lòng upload file audio mẫu (WAV/MP3).", None, ""
        return

    speed = _speed_key(speed_label)
    out   = str(OUTPUTS_DIR / f"ui_clone_{_ts()}.wav")
    transcript = ref_transcript.strip() if ref_transcript and ref_transcript.strip() else ""

    tip = "Đã có transcript → bỏ qua Whisper ASR." if transcript else "Chưa có transcript → sẽ dùng Whisper ASR (~1.5GB lần đầu)."
    yield f"⏳ Đang clone giọng...\n{tip}\n(CPU có thể mất vài phút)", None, ""

    try:
        from app_mvp.core_engine import generate_clone
        path = generate_clone(
            text=text.strip(),
            reference_audio_path=ref_audio,
            reference_transcript=transcript,
            speed=speed,
            output_path=out,
        )
        log.info("Clone OK: %s", path)
        yield f"✅ Hoàn tất!\nFile: {path}", path, path
    except FileNotFoundError as e:
        log.error("Clone FileNotFoundError: %s", e)
        yield f"❌ Lỗi: {e}", None, ""
    except Exception as e:
        log.exception("Clone error")
        yield f"❌ Lỗi: {type(e).__name__}: {e}", None, ""


# ---------------------------------------------------------------------------
# TAB C — Voice Design [EXPERIMENTAL]
# ---------------------------------------------------------------------------
def fn_design(text: str, description: str, speed_label: str):
    if not text or not text.strip():
        yield "Vui lòng nhập văn bản.", None, ""
        return
    if not description or not description.strip():
        yield "Vui lòng nhập mô tả giọng.", None, ""
        return

    speed = _speed_key(speed_label)
    out   = str(OUTPUTS_DIR / f"ui_design_{_ts()}.wav")

    yield f"⏳ Đang tạo giọng thiết kế...\n(Mô tả: {description.strip()})\n(CPU có thể mất vài phút)", None, ""

    try:
        from app_mvp.core_engine import generate_voice_design
        path = generate_voice_design(
            text=text.strip(),
            voice_description=description.strip(),
            speed=speed,
            output_path=out,
        )
        log.info("Design OK: %s", path)
        yield f"✅ Hoàn tất!\nFile: {path}", path, path
    except ValueError as e:
        log.error("Design ValueError: %s", e)
        yield (
            f"❌ Lỗi mô tả giọng: {e}\n\n"
            "Gợi ý: dùng 'giong nam, truong thanh' hoặc 'giong nu, thanh nien'", None, ""
        )
    except Exception as e:
        log.exception("Design error")
        yield f"❌ Lỗi: {type(e).__name__}: {e}", None, ""


# ---------------------------------------------------------------------------
# TAB D — Hệ thống
# ---------------------------------------------------------------------------
def fn_system_check():
    lines = []

    # Python
    lines.append(f"Python: {sys.version.split()[0]}")

    # torch
    try:
        import torch
        lines.append(f"PyTorch: {torch.__version__}")
        cuda = torch.cuda.is_available()
        lines.append(f"CUDA: {'Có' if cuda else 'Không có'}")
        if cuda:
            lines.append(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            # Try WMI fallback for GPU name
            try:
                import subprocess as sp
                r = sp.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True, text=True, timeout=5,
                )
                gpus = [l.strip() for l in r.stdout.splitlines() if l.strip() and l.strip() != "Name"]
                if gpus:
                    lines.append(f"GPU (CUDA không khả dụng): {', '.join(gpus)}")
            except Exception:
                pass
    except ImportError:
        lines.append("PyTorch: Chưa cài")

    # Model cache
    cache = Path.home() / ".cache" / "huggingface" / "hub" / "models--k2-fsa--OmniVoice"
    lines.append(f"Model cache: {'Có' if cache.exists() else 'Chưa tải'} ({cache})")

    # Dataset
    assets = _REPO_ROOT / "assets" / "omnivoice-vi" / "voices"
    lines.append(f"Dataset voices: {'Có' if assets.exists() else 'Chưa tải'} ({assets})")

    # 6 voices
    lines.append("")
    lines.append("Voice preset tiếng Việt:")
    for display, slug in VI_VOICES:
        pt = assets / slug / "voice.pt"
        status = "READY" if pt.exists() else "MISSING — chạy download_tuong_vy.py"
        lines.append(f"  {slug:<14} {display:<14} [{status}]")

    # Outputs dir
    lines.append("")
    out_dir = _REPO_ROOT / "outputs"
    wav_count = len(list(out_dir.rglob("*.wav"))) if out_dir.exists() else 0
    lines.append(f"Thư mục outputs: {out_dir} ({wav_count} file WAV)")

    return "\n".join(lines)


def fn_open_outputs():
    out_dir = str(_REPO_ROOT / "outputs")
    try:
        subprocess.Popen(["explorer", out_dir])
        return f"Đã mở thư mục: {out_dir}"
    except Exception as e:
        return f"Không mở được tự động.\nĐường dẫn: {out_dir}\nLỗi: {e}"


# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------

_CSS = """
/* ════════════════════════════════════════════
   THIENVOICE — Professional Dark Workspace v3
   ════════════════════════════════════════════ */

/* ── Nền tối toàn trang — đè hết background Gradio ── */
body,
html,
.gradio-container,
.gradio-container > div,
.gradio-container > div > div,
.gradio-container > div > div > div {
    background: #0d1117 !important;
}
footer { display: none !important; }

/* ── Container sizing — chiếm toàn bộ chiều rộng viewport ── */
.gradio-container {
    max-width: 100% !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    min-height: 100vh !important;
}

/* Frame tối bao ngoài với padding */
.gradio-container > div {
    padding: 24px !important;
    max-width: 1100px !important;
    margin: 0 auto !important;
}

/* ══════════════════════════════════════
   CARD WRAPPER — gr.Column.tv-card
   Đặt sau dark rule để override lại màu trắng
   ══════════════════════════════════════ */
.tv-card,
.tv-card > div,
.tv-card > div > div {
    background: #ffffff !important;
}
.tv-card {
    border-radius: 14px !important;
    overflow: hidden !important;
    box-shadow: 0 12px 48px rgba(0,0,0,0.55) !important;
    padding: 0 !important;
    gap: 0 !important;
    border: none !important;
}

/* ── Header (inside card, self-contained HTML) ── */
.tv-hdr {
    background: #161b27;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1e2533;
}
.tv-logo { display: flex; align-items: center; gap: 10px; }
.tv-icon {
    width: 36px; height: 36px;
    background: #e63946;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 800; color: #fff;
    letter-spacing: -0.5px; flex-shrink: 0;
}
.tv-name  { color: #f1f5f9; font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }
.tv-sub   { color: #64748b; font-size: 9.5px; letter-spacing: 1px; margin-top: 2px; }
.tv-badge {
    background: #0d1117;
    border: 1px solid #1e2533;
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 11px; color: #94a3b8;
    text-align: right; line-height: 1.65;
}
.tv-badge b { color: #fbbf24; }

/* ── CPU warning ── */
.tv-warn {
    background: #fffbeb;
    border-bottom: 1px solid #fde68a;
    border-left: none;
    border-radius: 0;
    padding: 9px 20px;
    font-size: 12px; color: #78350f;
}

/* ── Body padding (gr.Column.tv-body) ── */
.tv-body {
    padding: 16px 20px 8px !important;
    gap: 12px !important;
    border: none !important;
    background: #ffffff !important;
}

/* ── Footer (self-contained HTML) ── */
.tv-foot {
    background: #f8fafc;
    border-top: 1px solid #f1f5f9;
    text-align: center;
    font-size: 11.5px;
    color: #94a3b8;
    padding: 12px 0;
}
.tv-foot strong { color: #64748b; }

/* ══════════════════════════════════════
   TABS — pill bar, equal-width, no overflow
   ══════════════════════════════════════ */

/* Ẩn nút "..." overflow của Gradio */
#tv-tabs > div:first-child > button:not([role="tab"]),
#tv-tabs > div:first-child > *:not([role="tab"]):not(button[role="tab"]):last-child {
    display: none !important;
}

#tv-tabs > div:first-child {
    display: flex !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    gap: 0 !important;
    background: #f1f5f9 !important;
    border-radius: 9px !important;
    padding: 4px !important;
    border-bottom: none !important;
    margin-bottom: 16px !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

/* Wrapper div quanh mỗi button (nếu có) */
#tv-tabs > div:first-child > * {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    display: flex !important;
    align-items: stretch !important;
}

/* Button tab */
#tv-tabs > div:first-child > * > button,
#tv-tabs > div:first-child > button[role="tab"] {
    flex: 1 1 0 !important;
    width: 100% !important;
    min-width: 0 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 9px 6px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    background: transparent !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.4 !important;
    text-align: center !important;
    transition: background 0.12s, color 0.12s !important;
}
#tv-tabs > div:first-child > * > button:hover,
#tv-tabs > div:first-child > button[role="tab"]:hover {
    background: #e2e8f0 !important;
    color: #334155 !important;
}
#tv-tabs > div:first-child > * > button.selected,
#tv-tabs > div:first-child > button[role="tab"].selected {
    background: #e63946 !important;
    color: #fff !important;
    font-weight: 600 !important;
}
#tv-tabs button::after,
#tv-tabs button::before { display: none !important; }

/* ══════════════════════════════════════
   INPUTS & LABELS
   ══════════════════════════════════════ */
.tv-body label > span:first-child {
    font-size: 12.5px !important;
    font-weight: 600 !important;
    color: #374151 !important;
}
.tv-body textarea,
.tv-body input[type="text"] {
    font-size: 13px !important;
    border-radius: 7px !important;
    border: 1.5px solid #e2e8f0 !important;
    background: #fafafa !important;
    color: #1e293b !important;
    font-family: 'Segoe UI', system-ui, sans-serif !important;
}
.tv-body textarea:focus,
.tv-body input[type="text"]:focus {
    border-color: #e63946 !important;
    background: #fff !important;
    box-shadow: 0 0 0 3px rgba(230,57,70,0.1) !important;
    outline: none !important;
}
.tv-body select {
    font-size: 12.5px !important;
    border-radius: 7px !important;
    border: 1.5px solid #e2e8f0 !important;
    background: #fafafa !important;
    color: #1e293b !important;
}
.status-box textarea {
    font-size: 12px !important;
    color: #475569 !important;
    background: #f8fafc !important;
    border-color: #e2e8f0 !important;
}

/* ══════════════════════════════════════
   BUTTONS
   ══════════════════════════════════════ */
.tv-body button[variant="primary"],
.tv-body button.primary {
    background: #e63946 !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    box-shadow: 0 3px 10px rgba(230,57,70,0.28) !important;
    transition: background 0.12s, box-shadow 0.12s, transform 0.1s !important;
}
.tv-body button[variant="primary"]:hover,
.tv-body button.primary:hover {
    background: #c1121f !important;
    box-shadow: 0 5px 16px rgba(230,57,70,0.4) !important;
    transform: translateY(-1px) !important;
}
.tv-body button[variant="secondary"],
.tv-body button.secondary {
    border: 1.5px solid #e63946 !important;
    color: #e63946 !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    background: transparent !important;
}

/* ── Experimental warning ── */
.exp-warn {
    background: #fff8e1;
    border: 1px solid #fde68a;
    border-left: 3px solid #f59e0b;
    border-radius: 7px;
    padding: 9px 14px;
    font-size: 12px; color: #78350f;
    margin-bottom: 14px;
}
"""

_SPEED_INFO = "Bình thường = 1.0x  ·  Chậm = 0.85x  ·  Nhanh = 1.15x"

_HEADER_HTML = """
<div class="tv-hdr">
  <div class="tv-logo">
    <div class="tv-icon">TV</div>
    <div>
      <div class="tv-name">ThienVoice</div>
      <div class="tv-sub">TỔNG HỢP GIỌNG NÓI TIẾNG VIỆT</div>
    </div>
  </div>
  <div class="tv-badge">
    <b>CPU mode</b> &nbsp;·&nbsp; mỗi câu ~3–7 phút<br>
    GPU NVIDIA = 10–20× nhanh hơn
  </div>
</div>
"""

_CPU_WARN_HTML = """
<div class="tv-warn">
  &#9888; &nbsp;<strong>Lưu ý:</strong> Máy đang chạy bằng CPU.
  Mỗi lần tạo audio có thể mất 3–7 phút — vui lòng chờ sau khi nhấn nút, đừng nhấn lại.
</div>
"""

_EXP_WARN_HTML = """
<div class="exp-warn">
  <strong>Voice Design là tính năng thử nghiệm.</strong>
  Chất lượng phát âm tiếng Việt có thể không ổn định —
  nên dùng tab <strong>Text to Speech</strong> với giọng preset để có kết quả tốt hơn.
</div>
"""

_FOOTER_HTML = """
<div class="tv-foot">
  &copy; 2026 &nbsp;<strong>ThienVoice</strong>&nbsp;&nbsp;&middot;&nbsp;&nbsp;Bản quyền thuộc về &nbsp;<strong>Nguyễn Đức Thiện</strong>&nbsp;&nbsp;&middot;&nbsp;&nbsp;0906 000 040
</div>
"""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="ThienVoice") as demo:

        with gr.Column(elem_classes="tv-card"):

            # ── Header & warning (standalone, closed HTML) ──
            gr.HTML(_HEADER_HTML)
            gr.HTML(_CPU_WARN_HTML)

            with gr.Column(elem_classes="tv-body"):

                with gr.Tabs(elem_id="tv-tabs"):

                    # ============================================================
                    # A. Text to Speech
                    # ============================================================
                    with gr.TabItem("Text to Speech"):
                        with gr.Row():
                            with gr.Column(scale=3):
                                tts_text = gr.Textbox(
                                    label="Văn bản tiếng Việt",
                                    lines=5,
                                    placeholder=(
                                        "Nhập văn bản cần đọc ở đây...\n\n"
                                        "Ví dụ: Xin chào, đây là bản thử nghiệm giọng đọc tiếng Việt bằng ThienVoice."
                                    ),
                                )
                                with gr.Row():
                                    tts_voice = gr.Dropdown(
                                        label="Chọn giọng",
                                        choices=VOICE_CHOICES,
                                        value=VOICE_DEFAULT,
                                    )
                                    tts_speed = gr.Dropdown(
                                        label="Tốc độ",
                                        choices=SPEED_CHOICES,
                                        value="Bình thường",
                                        info=_SPEED_INFO,
                                    )
                                tts_btn = gr.Button("Tạo giọng đọc", variant="primary", size="lg")
                            with gr.Column(scale=2):
                                tts_status = gr.Textbox(
                                    label="Trạng thái",
                                    lines=3,
                                    interactive=False,
                                    elem_classes="status-box",
                                    value="Sẵn sàng — nhập văn bản và nhấn Tạo giọng đọc",
                                )
                                tts_audio = gr.Audio(label="Nghe thử", type="filepath")
                                tts_path  = gr.Textbox(label="File đã lưu", interactive=False)

                        tts_btn.click(fn_tts, [tts_text, tts_voice, tts_speed],
                                      [tts_status, tts_audio, tts_path])

                    # ============================================================
                    # B. Clone Voice
                    # ============================================================
                    with gr.TabItem("Clone Voice"):
                        with gr.Row():
                            with gr.Column(scale=3):
                                clone_text = gr.Textbox(
                                    label="Văn bản cần đọc",
                                    lines=4,
                                    placeholder="Nhập văn bản tiếng Việt cần đọc bằng giọng clone...",
                                )
                                clone_ref = gr.Audio(
                                    label="File audio mẫu  (WAV/MP3, khuyến nghị 3–10 giây)",
                                    type="filepath",
                                    sources=["upload"],
                                )
                                clone_transcript = gr.Textbox(
                                    label="Transcript audio mẫu  (tùy chọn)",
                                    lines=2,
                                    placeholder="Nội dung đang nói trong audio mẫu — nên điền để chất lượng tốt hơn...",
                                    info="Để trống → tự nhận dạng bằng Whisper ASR (tải ~1.5 GB lần đầu)",
                                )
                                clone_speed = gr.Dropdown(
                                    label="Tốc độ",
                                    choices=SPEED_CHOICES,
                                    value="Bình thường",
                                    info=_SPEED_INFO,
                                )
                                clone_btn = gr.Button("Tạo giọng clone", variant="primary", size="lg")
                            with gr.Column(scale=2):
                                clone_status = gr.Textbox(
                                    label="Trạng thái",
                                    lines=3,
                                    interactive=False,
                                    elem_classes="status-box",
                                    value="Sẵn sàng — upload audio mẫu và nhập văn bản",
                                )
                                clone_audio = gr.Audio(label="Nghe thử", type="filepath")
                                clone_path  = gr.Textbox(label="File đã lưu", interactive=False)

                        clone_btn.click(fn_clone,
                                        [clone_text, clone_ref, clone_transcript, clone_speed],
                                        [clone_status, clone_audio, clone_path])

                    # ============================================================
                    # C. Voice Design
                    # ============================================================
                    with gr.TabItem("Voice Design"):
                        gr.HTML(_EXP_WARN_HTML)
                        with gr.Row():
                            with gr.Column(scale=3):
                                design_text = gr.Textbox(
                                    label="Văn bản tiếng Việt",
                                    lines=4,
                                    placeholder="Nhập văn bản cần đọc...",
                                )
                                design_desc = gr.Textbox(
                                    label="Mô tả giọng",
                                    lines=2,
                                    placeholder=(
                                        "Ví dụ:  giong nam, truong thanh\n"
                                        "         giong nu, thanh nien, am cao"
                                    ),
                                    info="Từ khóa: giong nam · giong nu · truong thanh · thanh nien · am cao · am thap · thi tham",
                                )
                                design_speed = gr.Dropdown(
                                    label="Tốc độ",
                                    choices=SPEED_CHOICES,
                                    value="Bình thường",
                                    info=_SPEED_INFO,
                                )
                                design_btn = gr.Button("Tạo thử", variant="secondary", size="lg")
                            with gr.Column(scale=2):
                                design_status = gr.Textbox(
                                    label="Trạng thái",
                                    lines=3,
                                    interactive=False,
                                    elem_classes="status-box",
                                    value="Sẵn sàng — nhập văn bản và mô tả giọng",
                                )
                                design_audio = gr.Audio(label="Nghe thử", type="filepath")
                                design_path  = gr.Textbox(label="File đã lưu", interactive=False)

                        design_btn.click(fn_design,
                                         [design_text, design_desc, design_speed],
                                         [design_status, design_audio, design_path])

                    # ============================================================
                    # D. Hệ thống
                    # ============================================================
                    with gr.TabItem("Hệ thống"):
                        with gr.Row():
                            sys_btn  = gr.Button("Kiểm tra hệ thống", variant="primary")
                            open_btn = gr.Button("Mở thư mục outputs")
                        sys_info = gr.Textbox(
                            label="Thông tin hệ thống",
                            lines=18,
                            interactive=False,
                            value="Nhấn 'Kiểm tra hệ thống' để xem thông tin...",
                        )
                        open_status = gr.Textbox(label="", interactive=False, lines=1)
                        sys_btn.click(fn_system_check,  [], [sys_info])
                        open_btn.click(fn_open_outputs, [], [open_status])

            # ── Footer (standalone, closed HTML) ──
            gr.HTML(_FOOTER_HTML)

    return demo


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("Starting ThienVoice UI (Gradio %s)", gr.__version__)
    demo = build_ui()
    demo.queue().launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
        quiet=False,
        css=_CSS,
    )


if __name__ == "__main__":
    main()
