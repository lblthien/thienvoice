"""Test voice preset tuong_vy từ dataset STBack23/omnivoice-vi.

Pipeline:
  1. Load voice.pt (dict) → VoiceClonePrompt
  2. Gọi model.generate() với voice_clone_prompt
  3. Lưu output vào outputs/tuong_vy_test.wav

Chạy:
    .venv\\Scripts\\python.exe app_mvp\\test_tuong_vy_preset.py

Yêu cầu: đã chạy download_tuong_vy.py trước.
"""

import logging
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import soundfile as sf
import torch

from omnivoice.models.omnivoice import OmniVoice, VoiceClonePrompt
from omnivoice.utils.common import get_best_device

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
VOICE_DIR   = _REPO_ROOT / "assets" / "omnivoice-vi" / "voices" / "tuong_vy"
OUTPUT_PATH = _REPO_ROOT / "outputs" / "tuong_vy_test.wav"
MODEL_NAME  = "k2-fsa/OmniVoice"

TEST_TEXT = (
    "Xin chào, đây là bản kiểm tra giọng đọc tiếng Việt bằng ThienVoice. "
    "Hôm nay tôi sẽ giới thiệu một dự án bất động sản nổi bật tại khu Nam Sài Gòn."
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
os.makedirs(_REPO_ROOT / "logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load voice.pt → VoiceClonePrompt
# ---------------------------------------------------------------------------
def load_voice_preset(voice_dir: Path, device: str) -> VoiceClonePrompt:
    """Load voice.pt và tạo VoiceClonePrompt.

    voice.pt là dict: {ref_audio_tokens, ref_text, ref_rms}
    Chuyển sang VoiceClonePrompt dataclass và đưa tensor lên đúng device.
    """
    pt_path = voice_dir / "voice.pt"
    if not pt_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay {pt_path}\n"
            "Chay truoc: .venv\\Scripts\\python.exe app_mvp\\download_tuong_vy.py"
        )

    log.info("Loading voice.pt from %s ...", pt_path)
    data = torch.load(str(pt_path), map_location="cpu", weights_only=False)

    if not isinstance(data, dict) or "ref_audio_tokens" not in data:
        raise ValueError(
            f"voice.pt co format la {type(data)} — khong phai dict voi ref_audio_tokens. "
            "Can dung fallback ref.wav + ref_text.txt."
        )

    prompt = VoiceClonePrompt(
        ref_audio_tokens=data["ref_audio_tokens"].to(device),
        ref_text=data["ref_text"],
        ref_rms=float(data["ref_rms"]),
    )
    log.info(
        "Voice preset loaded: ref_audio_tokens=%s, ref_text=%r..., ref_rms=%.4f",
        tuple(prompt.ref_audio_tokens.shape),
        prompt.ref_text[:60],
        prompt.ref_rms,
    )
    return prompt


# ---------------------------------------------------------------------------
# Fallback: tạo VoiceClonePrompt từ ref.wav + ref_text.txt
# ---------------------------------------------------------------------------
def load_voice_fallback(voice_dir: Path, model: OmniVoice) -> VoiceClonePrompt:
    """Fallback: dùng ref audio + ref_text để tạo prompt qua API gốc."""
    log.warning("Fallback: tao VoiceClonePrompt tu ref audio + ref_text.txt")

    ref_audio = next(
        (voice_dir / f for f in ("ref.wav", "ref.mp3") if (voice_dir / f).exists()),
        None,
    )
    if ref_audio is None:
        raise FileNotFoundError(f"Khong tim thay ref.wav hoac ref.mp3 trong {voice_dir}")

    ref_text_path = voice_dir / "ref_text.txt"
    ref_text = None
    if ref_text_path.exists():
        ref_text = ref_text_path.read_text(encoding="utf-8").strip() or None
        if ref_text:
            log.info("ref_text tu file: %r...", ref_text[:60])

    prompt = model.create_voice_clone_prompt(
        ref_audio=str(ref_audio),
        ref_text=ref_text,
        preprocess_prompt=False,
    )
    log.info("Fallback prompt created OK.")
    return prompt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Test voice preset: tuong_vy")
    print("=" * 60)

    # --- 1. Chon device ---
    device = get_best_device()
    log.info("Device: %s", device)
    # VoiceClonePrompt can tensor tren dung device voi model
    # Neu CPU thi dung float32
    dtype = torch.float16 if device != "cpu" else torch.float32

    # --- 2. Load model ---
    t0 = time.time()
    log.info("Loading model %s ...", MODEL_NAME)
    model = OmniVoice.from_pretrained(MODEL_NAME, device_map=device, dtype=dtype)
    model.eval()
    log.info("Model loaded in %.1fs", time.time() - t0)

    # --- 3. Load voice preset ---
    voice_prompt = None
    load_method = None

    try:
        voice_prompt = load_voice_preset(VOICE_DIR, device=str(model.device))
        load_method = "voice.pt"
    except Exception as e:
        log.warning("voice.pt load that bai: %s — thu fallback ref.wav", e)
        try:
            voice_prompt = load_voice_fallback(VOICE_DIR, model)
            load_method = "fallback (ref.wav + ref_text.txt)"
        except Exception as e2:
            log.error("Ca hai cach load deu that bai: %s", e2)
            sys.exit(1)

    log.info("Voice prompt loaded via: %s", load_method)

    # --- 4. Resolve language ---
    # Profile dung "Vietnamese" — OmniVoice chap nhan ten ngon ngu day du
    language = "Vietnamese"
    try:
        from omnivoice.models.omnivoice import _resolve_language
        resolved = _resolve_language(language)
        if resolved is None:
            language = "vi"
            log.warning("'Vietnamese' khong resolve duoc, fallback sang 'vi'")
        else:
            log.info("Language resolved: '%s' -> '%s'", language, resolved)
    except Exception:
        language = "vi"
        log.warning("Loi resolve language, fallback sang 'vi'")

    # --- 5. Generate ---
    os.makedirs(OUTPUT_PATH.parent, exist_ok=True)

    log.info("Generating audio for: %r...", TEST_TEXT[:60])
    log.info(
        "Settings: language=%s num_step=32 guidance_scale=2.0 "
        "class_temperature=0.4 speed=1.0 postprocess_output=True",
        language,
    )

    t_gen = time.time()
    audios = model.generate(
        text=TEST_TEXT,
        language=language,
        voice_clone_prompt=voice_prompt,
        num_step=32,
        guidance_scale=2.0,
        class_temperature=0.4,
        speed=1.0,
        postprocess_output=True,
    )
    gen_time = time.time() - t_gen

    # --- 6. Luu output ---
    sf.write(str(OUTPUT_PATH), audios[0], model.sampling_rate)
    duration = len(audios[0]) / model.sampling_rate

    log.info(
        "Saved: %s (%.2fs audio, generated in %.1fs)",
        OUTPUT_PATH, duration, gen_time,
    )

    print()
    print("=" * 60)
    print(f"THANH CONG")
    print(f"  Voice  : tuong_vy  ({load_method})")
    print(f"  Output : {OUTPUT_PATH}")
    print(f"  Duration : {duration:.2f}s  |  Gen time: {gen_time:.1f}s")
    print(f"  Device : {device}")
    print("=" * 60)


if __name__ == "__main__":
    main()

