"""Vietnamese voice preset manager cho STBack23/omnivoice-vi.

Quản lý 6 voice preset tiếng Việt, hỗ trợ load voice.pt trực tiếp
thành VoiceClonePrompt, fallback sang ref.wav nếu cần.

Dataset: STBack23/omnivoice-vi
Local:   assets/omnivoice-vi/voices/<slug>/
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent
ASSETS_DIR = _REPO_ROOT / "assets" / "omnivoice-vi" / "voices"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VI_VOICE_SLUGS: List[str] = [
    "ban_mai",
    "lan_trinh",
    "ngan_ha",
    "ngoc_huyen",
    "thao_trinh",
    "tuong_vy",
]

DEFAULT_VI_VOICE = "tuong_vy"

_DISPLAY_NAMES: Dict[str, str] = {
    "ban_mai":   "Ban Mai",
    "lan_trinh": "Lan Trinh",
    "ngan_ha":   "Ngân Hà",
    "ngoc_huyen":"Ngọc Huyền",
    "thao_trinh":"Thảo Trinh",
    "tuong_vy":  "Tường Vy",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class VIVoiceAssets:
    slug: str
    display_name: str
    voice_dir: Path
    profile: dict
    voice_pt_path: Optional[Path]   # None nếu không có
    ref_audio_path: Optional[Path]  # None nếu không có
    ref_text: Optional[str]         # None nếu không có
    voice_pt_ok: bool = False       # True sau khi verify load được
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_default_vi_voice() -> str:
    return DEFAULT_VI_VOICE


def slug_to_display_name(slug: str) -> str:
    return _DISPLAY_NAMES.get(slug, slug.replace("_", " ").title())


def list_vi_profiles() -> List[str]:
    return list(VI_VOICE_SLUGS)


def load_vi_profile(slug: str) -> VIVoiceAssets:
    """Load metadata của một voice preset (không load tensor).

    Args:
        slug: Tên voice, e.g. "tuong_vy"

    Returns:
        VIVoiceAssets với thông tin file và ref_text.

    Raises:
        ValueError: Nếu slug không hợp lệ.
        FileNotFoundError: Nếu thư mục voice chưa tải về.
    """
    if slug not in VI_VOICE_SLUGS:
        raise ValueError(
            f"Voice '{slug}' khong hop le. "
            f"Cac voice hop le: {', '.join(VI_VOICE_SLUGS)}"
        )

    voice_dir = ASSETS_DIR / slug
    if not voice_dir.exists():
        raise FileNotFoundError(
            f"Chua tim thay thu muc voice: {voice_dir}\n"
            f"Chay truoc: .venv\\Scripts\\python.exe app_mvp\\download_tuong_vy.py"
        )

    # Load profile.json
    profile_path = voice_dir / "profile.json"
    profile = {}
    if profile_path.exists():
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)

    # voice.pt
    pt_path = voice_dir / "voice.pt"
    voice_pt_path = pt_path if pt_path.exists() else None

    # ref audio (có thể .wav hoặc .mp3)
    ref_audio = next(
        (voice_dir / ext for ext in ("ref.wav", "ref.mp3")
         if (voice_dir / ext).exists()),
        None,
    )

    # ref_text: ưu tiên ref_text.txt, fallback ref_text_asr.txt
    ref_text = None
    for txt_name in ("ref_text.txt", "ref_text_asr.txt"):
        txt_path = voice_dir / txt_name
        if txt_path.exists():
            content = txt_path.read_text(encoding="utf-8").strip()
            if content:
                ref_text = content
                break

    return VIVoiceAssets(
        slug=slug,
        display_name=slug_to_display_name(slug),
        voice_dir=voice_dir,
        profile=profile,
        voice_pt_path=voice_pt_path,
        ref_audio_path=ref_audio,
        ref_text=ref_text,
    )


def load_voice_prompt(slug: str, device: str = "cpu"):
    """Load VoiceClonePrompt từ voice.pt (fallback: ref.wav + ref_text).

    Args:
        slug: Tên voice preset.
        device: Device string để đặt tensor lên ("cpu", "cuda", ...).

    Returns:
        VoiceClonePrompt object sẵn sàng truyền vào model.generate().
    """
    import torch
    from omnivoice.models.omnivoice import VoiceClonePrompt

    assets = load_vi_profile(slug)

    # --- Cách 1: Load voice.pt trực tiếp ---
    if assets.voice_pt_path is not None:
        try:
            data = torch.load(
                str(assets.voice_pt_path),
                map_location="cpu",
                weights_only=False,
            )
            if isinstance(data, dict) and "ref_audio_tokens" in data:
                prompt = VoiceClonePrompt(
                    ref_audio_tokens=data["ref_audio_tokens"].to(device),
                    ref_text=data["ref_text"],
                    ref_rms=float(data["ref_rms"]),
                )
                logger.info(
                    "[%s] voice.pt loaded: tokens=%s ref_rms=%.4f",
                    slug, tuple(prompt.ref_audio_tokens.shape), prompt.ref_rms,
                )
                return prompt
            else:
                logger.warning(
                    "[%s] voice.pt format la %s, khong phai dict -> fallback",
                    slug, type(data),
                )
        except Exception as e:
            logger.warning("[%s] voice.pt load loi: %s -> fallback", slug, e)

    # --- Cách 2: Fallback ref.wav / ref.mp3 + ref_text ---
    if assets.ref_audio_path is None:
        raise FileNotFoundError(
            f"[{slug}] Khong co voice.pt hay ref audio trong {assets.voice_dir}"
        )

    logger.warning(
        "[%s] Fallback: dung %s + ref_text",
        slug, assets.ref_audio_path.name,
    )

    # Import model để tạo prompt (cần model đã được load ở ngoài)
    # Trả về tuple để caller dùng model.create_voice_clone_prompt
    return _FallbackPromptRequest(
        ref_audio_path=str(assets.ref_audio_path),
        ref_text=assets.ref_text,
    )


class _FallbackPromptRequest:
    """Sentinel object khi voice.pt không dùng được.

    Caller phải gọi model.create_voice_clone_prompt() với thông tin này.
    """
    def __init__(self, ref_audio_path: str, ref_text: Optional[str]):
        self.ref_audio_path = ref_audio_path
        self.ref_text = ref_text


def resolve_voice_prompt(slug: str, model, device: str = "cpu"):
    """Load VoiceClonePrompt, tự động handle fallback cần model.

    Args:
        slug: Voice preset slug.
        model: OmniVoice model instance (chỉ cần khi fallback).
        device: Device string.

    Returns:
        VoiceClonePrompt
    """
    result = load_voice_prompt(slug, device=device)

    if isinstance(result, _FallbackPromptRequest):
        logger.info("[%s] Dang tao prompt tu ref audio qua model...", slug)
        return model.create_voice_clone_prompt(
            ref_audio=result.ref_audio_path,
            ref_text=result.ref_text,
            preprocess_prompt=False,
        )

    return result


def validate_vi_voice_assets() -> Dict[str, dict]:
    """Kiểm tra trạng thái file của tất cả 6 voice preset.

    Returns:
        Dict[slug -> {display_name, voice_pt, ref_audio, ref_text, ready}]
    """
    import torch

    results = {}
    for slug in VI_VOICE_SLUGS:
        info = {
            "display_name": slug_to_display_name(slug),
            "voice_pt": False,
            "ref_audio": False,
            "ref_text": False,
            "voice_pt_loadable": False,
            "error": None,
            "ready": False,
        }
        try:
            assets = load_vi_profile(slug)
            info["voice_pt"]   = assets.voice_pt_path is not None
            info["ref_audio"]  = assets.ref_audio_path is not None
            info["ref_text"]   = assets.ref_text is not None

            if assets.voice_pt_path:
                try:
                    data = torch.load(
                        str(assets.voice_pt_path),
                        map_location="cpu",
                        weights_only=False,
                    )
                    info["voice_pt_loadable"] = (
                        isinstance(data, dict) and "ref_audio_tokens" in data
                    )
                except Exception as e:
                    info["error"] = f"voice.pt load error: {e}"

            info["ready"] = info["voice_pt_loadable"] or (
                info["ref_audio"] and info["ref_text"]
            )

        except FileNotFoundError as e:
            info["error"] = str(e)
        except Exception as e:
            info["error"] = str(e)

        results[slug] = info

    return results
