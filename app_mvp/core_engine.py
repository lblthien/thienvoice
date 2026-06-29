"""OmniVoice MVP Core Engine.

Provides three simple functions:
    generate_tts()          - Text to Speech (tiếng Việt)
    generate_clone()        - Voice Clone từ file audio mẫu
    generate_voice_design() - Voice Design bằng mô tả tiếng Việt

Speed mapping:
    slow   = 0.85
    normal = 1.0
    fast   = 1.15

Voice Design: mô tả tiếng Việt sẽ được map sang keyword tiếng Anh
mà OmniVoice hỗ trợ. Các từ không map được (rõ ràng, chuyên nghiệp,
tự nhiên...) sẽ bị bỏ qua.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import soundfile as sf
import torch

# Đảm bảo repo root trong sys.path để import omnivoice
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.common import get_best_device

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "k2-fsa/OmniVoice"

SPEED_MAP = {
    "slow": 0.85,
    "normal": 1.0,
    "fast": 1.15,
}

# Map từ khóa tiếng Việt → instruct keyword hợp lệ của OmniVoice
# OmniVoice chỉ chấp nhận các từ khóa cụ thể (xem omnivoice/utils/voice_design.py)
_VI_TO_INSTRUCT = {
    # Giới tính
    "giọng nam": "male",
    "giọng nữ": "female",
    # Age — phải check sau "giọng nam/nữ" nên sort by length
    "trẻ em": "child",
    "thiếu niên": "teenager",
    "thanh niên": "young adult",
    "trung niên": "middle-aged",
    "trưởng thành": "middle-aged",
    "người già": "elderly",
    "lớn tuổi": "elderly",
    # Pitch
    "âm rất thấp": "very low pitch",
    "giọng rất thấp": "very low pitch",
    "âm thấp": "low pitch",
    "giọng thấp": "low pitch",
    "âm vừa": "moderate pitch",
    "giọng vừa": "moderate pitch",
    "âm cao": "high pitch",
    "giọng cao": "high pitch",
    "âm rất cao": "very high pitch",
    "giọng rất cao": "very high pitch",
    # Style
    "thì thầm": "whisper",
    "nói thầm": "whisper",
    # Accents (chỉ hiệu quả với text tiếng Anh)
    "giọng anh": "british accent",
    "giọng mỹ": "american accent",
    "giọng úc": "australian accent",
    "giọng canada": "canadian accent",
    "giọng ấn độ": "indian accent",
    "giọng nhật": "japanese accent",
    "giọng hàn": "korean accent",
    "giọng nga": "russian accent",
    "giọng bồ đào nha": "portuguese accent",
    "giọng trung quốc": "chinese accent",
    "giọng trung": "chinese accent",
    # --- Phiên bản KHÔNG DẤU (người dùng gõ không dấu) ---
    # Tuổi
    "thieu nien": "teenager",
    "thanh nien": "young adult",
    "trung nien": "middle-aged",
    "truong thanh": "middle-aged",
    "nguoi gia": "elderly",
    "lon tuoi": "elderly",
    "tre em": "child",
    # Pitch không dấu
    "am rat thap": "very low pitch",
    "giong rat thap": "very low pitch",
    "am thap": "low pitch",
    "giong thap": "low pitch",
    "am vua": "moderate pitch",
    "giong vua": "moderate pitch",
    "am cao": "high pitch",
    "giong cao": "high pitch",
    "am rat cao": "very high pitch",
    "giong rat cao": "very high pitch",
    # Style không dấu
    "thi tham": "whisper",
    "noi tham": "whisper",
    # Accent không dấu
    "giong anh": "british accent",
    "giong my": "american accent",
    "giong uc": "australian accent",
    "giong canada": "canadian accent",
    "giong an do": "indian accent",
    "giong nhat": "japanese accent",
    "giong han": "korean accent",
    "giong nga": "russian accent",
    "giong trung quoc": "chinese accent",
}

# Fallback: từ đơn cho nam/nữ nếu không có "giọng nam/nữ"
_VI_GENDER_FALLBACK = {
    " nam ": "male",
    " nữ ": "female",
    "nam,": "male",
    "nữ,": "female",
    "(nam)": "male",
    "(nữ)": "female",
    # không dấu
    " nu ": "female",
    "nu,": "female",
    "(nu)": "female",
}

_model_cache: Optional[OmniVoice] = None


def load_model(model_name: str = DEFAULT_MODEL, device: Optional[str] = None) -> OmniVoice:
    """Load và cache OmniVoice model. Chỉ load 1 lần."""
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    device = device or get_best_device()
    logger.info("Loading OmniVoice model '%s' on device '%s' ...", model_name, device)
    dtype = torch.float16 if device != "cpu" else torch.float32
    model = OmniVoice.from_pretrained(
        model_name,
        device_map=device,
        dtype=dtype,
    )
    model.eval()
    logger.info("Model loaded OK. Sampling rate: %d Hz", model.sampling_rate)
    _model_cache = model
    return model


def _resolve_speed(speed) -> float:
    if isinstance(speed, str):
        key = speed.lower().strip()
        if key in SPEED_MAP:
            return SPEED_MAP[key]
        try:
            return float(key)
        except ValueError:
            logger.warning("Unknown speed '%s', falling back to normal (1.0)", speed)
            return 1.0
    return float(speed)


def _vi_description_to_instruct(description: str) -> Optional[str]:
    """Chuyển mô tả giọng tiếng Việt sang instruct keyword của OmniVoice.

    Ví dụ:
        "giọng nam Việt Nam, trưởng thành, rõ ràng"
        → "male, middle-aged"

    Các từ không có mapping (rõ ràng, chuyên nghiệp, tự nhiên, ...)
    sẽ bị bỏ qua. Không gây lỗi.

    Thứ tự output: gender trước, các thuộc tính khác sau.
    """
    desc = description.lower()
    gender = None
    rest = []

    # Phân loại gender riêng để luôn đặt trước (có dấu + không dấu)
    _GENDER_KEYS = {
        "giọng nam": "male", "giọng nữ": "female",
        "giong nam": "male", "giong nu": "female",
    }

    for vi_key, en_val in _GENDER_KEYS.items():
        if vi_key in desc:
            gender = en_val
            desc = desc.replace(vi_key, " ", 1)
            break

    # Sort theo độ dài giảm dần để ưu tiên match cụm từ dài hơn
    for vi_key, en_val in sorted(_VI_TO_INSTRUCT.items(), key=lambda x: -len(x[0])):
        if vi_key in _GENDER_KEYS:
            continue  # đã xử lý ở trên
        if vi_key in desc:
            if en_val not in rest and en_val not in (gender,):
                rest.append(en_val)
            desc = desc.replace(vi_key, " ", 1)

    # Fallback gender nếu chưa tìm được
    if gender is None:
        desc_padded = " " + description.lower() + " "
        for pattern, en_val in _VI_GENDER_FALLBACK.items():
            if pattern in desc_padded:
                gender = en_val
                break
        if gender is None:
            words = description.lower().split()
            if "nam" in words:
                gender = "male"
            elif "nữ" in words:
                gender = "female"

    matched = ([gender] if gender else []) + rest

    if not matched:
        logger.warning(
            "Khong map duoc mo ta '%s' -> instruct. Dung auto voice (khong instruct).",
            description,
        )
        return None

    result = ", ".join(matched)
    logger.info("Mapped: '%s' -> instruct='%s'", description, result)
    return result


def _ensure_output_dir(output_path: str):
    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)


def generate_preset_tts(
    text: str,
    voice_preset: str = "tuong_vy",
    speed: str = "normal",
    output_path: Optional[str] = None,
    num_step: int = 32,
    guidance_scale: float = 2.0,
    class_temperature: float = 0.4,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """TTS tiếng Việt dùng voice preset từ STBack23/omnivoice-vi.

    Đây là hàm TTS mặc định — dùng giọng cố định, không random.

    Args:
        text: Văn bản tiếng Việt cần đọc.
        voice_preset: Slug của voice preset (mặc định: "tuong_vy").
            Các giá trị hợp lệ: ban_mai, lan_trinh, ngan_ha,
            ngoc_huyen, thao_trinh, tuong_vy.
        speed: "slow" (0.85x) | "normal" (1.0x) | "fast" (1.15x).
        output_path: Đường dẫn output WAV. Mặc định:
            outputs/vi_presets/<voice_preset>.wav
        num_step: Số bước diffusion (32 = cân bằng chất lượng/tốc độ).
        guidance_scale: CFG scale (2.0 mặc định).
        class_temperature: Randomness (0.4 = tự nhiên hơn greedy 0.0).
        model_name: HuggingFace repo id hoặc đường dẫn local.

    Returns:
        Absolute path của file WAV đã lưu.
    """
    from app_mvp.vi_voice_profiles import resolve_voice_prompt

    if output_path is None:
        output_path = f"outputs/vi_presets/{voice_preset}.wav"

    _ensure_output_dir(output_path)
    model = load_model(model_name)
    speed_val = _resolve_speed(speed)
    device = str(model.device)

    logger.info(
        "[PresetTTS] voice=%s text='%s...' speed=%s",
        voice_preset, text[:60], speed_val,
    )

    voice_prompt = resolve_voice_prompt(voice_preset, model=model, device=device)

    audios = model.generate(
        text=text,
        language="Vietnamese",
        voice_clone_prompt=voice_prompt,
        speed=speed_val,
        num_step=num_step,
        guidance_scale=guidance_scale,
        class_temperature=class_temperature,
        postprocess_output=True,
    )
    sf.write(output_path, audios[0], model.sampling_rate)
    abs_path = os.path.abspath(output_path)
    logger.info("[PresetTTS] Da luu: %s", abs_path)
    return abs_path


def generate_tts(
    text: str,
    speed: str = "normal",
    output_path: str = "outputs/tts_output.wav",
    voice_preset: str = "tuong_vy",
    model_name: str = DEFAULT_MODEL,
) -> str:
    """TTS tiếng Việt — mặc định dùng voice preset tuong_vy.

    Wrapper gọi generate_preset_tts() với voice_preset mặc định.
    Để dùng random voice cũ, gọi generate_random_tts_legacy().

    Args:
        text: Văn bản tiếng Việt cần đọc.
        speed: "slow" | "normal" | "fast".
        output_path: Đường dẫn file WAV output.
        voice_preset: Voice preset slug (mặc định: "tuong_vy").
        model_name: HuggingFace repo id hoặc đường dẫn local.

    Returns:
        Absolute path của file WAV đã lưu.
    """
    return generate_preset_tts(
        text=text,
        voice_preset=voice_preset,
        speed=speed,
        output_path=output_path,
        model_name=model_name,
    )


def generate_random_tts_legacy(
    text: str,
    speed: str = "normal",
    output_path: str = "outputs/tts_legacy_output.wav",
    model_name: str = DEFAULT_MODEL,
) -> str:
    """[LEGACY] TTS random voice — model tự chọn giọng.

    Chất lượng tiếng Việt không ổn định. Dùng generate_tts() thay thế.
    Giữ lại để debug và so sánh.
    """
    _ensure_output_dir(output_path)
    model = load_model(model_name)
    speed_val = _resolve_speed(speed)

    logger.info("[LegacyTTS] text='%s...' speed=%s", text[:60], speed_val)
    audios = model.generate(
        text=text,
        language="vi",
        speed=speed_val,
    )
    sf.write(output_path, audios[0], model.sampling_rate)
    abs_path = os.path.abspath(output_path)
    logger.info("[LegacyTTS] Da luu: %s", abs_path)
    return abs_path


def generate_clone(
    text: str,
    reference_audio_path: str,
    reference_transcript: str = "",
    speed: str = "normal",
    output_path: str = "outputs/clone_output.wav",
    model_name: str = DEFAULT_MODEL,
) -> str:
    """Clone giọng từ audio mẫu rồi đọc văn bản tiếng Việt.

    Args:
        text: Văn bản tiếng Việt cần đọc.
        reference_audio_path: Đường dẫn file WAV/MP3 mẫu giọng (3–10 giây tốt nhất).
        reference_transcript: Transcript của audio mẫu. Để trống ("") để tự động
            nhận dạng bằng Whisper ASR (cần tải thêm model ~1.5GB lần đầu).
        speed: "slow" | "normal" | "fast".
        output_path: Đường dẫn file WAV output.
        model_name: HuggingFace repo id hoặc đường dẫn local.

    Returns:
        Absolute path của file WAV đã lưu.
    """
    if not os.path.isfile(reference_audio_path):
        raise FileNotFoundError(
            f"Không tìm thấy file audio mẫu: {reference_audio_path}\n"
            "Hãy đặt file WAV/MP3 mẫu vào đường dẫn trên."
        )
    _ensure_output_dir(output_path)
    model = load_model(model_name)
    speed_val = _resolve_speed(speed)
    ref_text = reference_transcript.strip() if reference_transcript.strip() else None

    logger.info(
        "[Clone] text='%s...' ref='%s' ref_text=%r speed=%s",
        text[:60], reference_audio_path, ref_text, speed_val,
    )
    audios = model.generate(
        text=text,
        language="vi",
        ref_audio=reference_audio_path,
        ref_text=ref_text,
        speed=speed_val,
    )
    sf.write(output_path, audios[0], model.sampling_rate)
    abs_path = os.path.abspath(output_path)
    logger.info("[Clone] Đã lưu: %s", abs_path)
    return abs_path


def generate_voice_design(
    text: str,
    voice_description: str,
    speed: str = "normal",
    output_path: str = "outputs/design_output.wav",
    model_name: str = DEFAULT_MODEL,
) -> str:
    """Tạo audio với giọng thiết kế từ mô tả tiếng Việt.

    Mô tả tiếng Việt sẽ tự động map sang keyword OmniVoice:
        "giọng nam Việt Nam, trưởng thành"  → instruct="male, middle-aged"
        "giọng nữ, nhẹ nhàng, tự nhiên"    → instruct="female"
        "giọng nữ, thì thầm, âm cao"       → instruct="female, whisper, high pitch"

    Keyword hợp lệ OmniVoice:
        Giới tính : male, female
        Tuổi      : child, teenager, young adult, middle-aged, elderly
        Độ cao    : very low pitch, low pitch, moderate pitch, high pitch, very high pitch
        Phong cách: whisper
        Giọng EN  : american/british/australian/canadian/indian/
                    japanese/korean/russian/portuguese/chinese accent

    Args:
        text: Văn bản tiếng Việt cần đọc.
        voice_description: Mô tả giọng bằng tiếng Việt.
        speed: "slow" | "normal" | "fast".
        output_path: Đường dẫn file WAV output.
        model_name: HuggingFace repo id hoặc đường dẫn local.

    Returns:
        Absolute path của file WAV đã lưu.
    """
    _ensure_output_dir(output_path)
    model = load_model(model_name)
    speed_val = _resolve_speed(speed)
    instruct = _vi_description_to_instruct(voice_description)

    logger.info(
        "[Design] text='%s...' desc='%s' → instruct='%s' speed=%s",
        text[:60], voice_description, instruct, speed_val,
    )
    audios = model.generate(
        text=text,
        language="vi",
        instruct=instruct,
        speed=speed_val,
    )
    sf.write(output_path, audios[0], model.sampling_rate)
    abs_path = os.path.abspath(output_path)
    logger.info("[Design] Đã lưu: %s", abs_path)
    return abs_path
