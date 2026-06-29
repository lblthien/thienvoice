"""Đọc văn bản / file / SRT bằng voice profile (.pt).

Ví dụ:
    python tools/speak.py voices
    python tools/speak.py --profile voices/ban_mai/profile.json build
    python tools/speak.py --profile voices/ban_mai/profile.json text --text "..." -o out.wav
    python tools/speak.py --profile voices/ban_mai/profile.json srt --input video.srt
    python tools/speak.py --profile voices/ban_mai/profile.json srt --input video.srt --merge -o dub.wav --fit-duration
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import librosa
import numpy as np
import soundfile as sf
import torch

from omnivoice.models.omnivoice import OmniVoice, VoiceClonePrompt

ROOT = Path(__file__).resolve().parents[1]
VOICES_DIR = ROOT / "voices"
DEFAULT_VOICE_SLUG = "tuong_vy"
DEFAULT_PROFILE = VOICES_DIR / DEFAULT_VOICE_SLUG / "profile.json"

# Mặc định biểu cảm: bật lấy mẫu token có nhiệt độ thay vì greedy (0.0).
# Greedy khiến ngữ điệu phẳng, "máy móc"; 0.4 cho nhấn nhá vừa phải, ổn định.
DEFAULT_CLASS_TEMPERATURE = 0.4
DEFAULT_GUIDANCE_SCALE = 2.0


@dataclass
class SrtCue:
    index: int
    start_sec: float
    end_sec: float
    text: str


def discover_profiles() -> List[Path]:
    if not VOICES_DIR.exists():
        return []
    return sorted(
        p for p in VOICES_DIR.glob("*/profile.json") if p.is_file()
    )


def profile_slug(profile_path: Path) -> str:
    return profile_path.parent.name


def load_profile(profile_path: Path) -> dict:
    with profile_path.open(encoding="utf-8") as f:
        profile = json.load(f)
    base = profile_path.parent
    profile["_base"] = base
    profile["_profile_path"] = str(profile_path)
    profile["slug"] = profile.get("slug", profile_slug(profile_path))
    profile["ref_audio_path"] = str(base / profile["ref_audio"])
    profile["ref_text_path"] = str(base / profile["ref_text_file"])
    profile["voice_prompt_path"] = str(base / profile["voice_prompt"])
    return profile


def default_output_dir(profile: dict, stem: str) -> Path:
    return ROOT / "output" / profile["slug"] / stem


def read_ref_text(profile: dict) -> str:
    return Path(profile["ref_text_path"]).read_text(encoding="utf-8").strip()


def load_model(profile: dict) -> OmniVoice:
    return OmniVoice.from_pretrained(
        profile.get("model", "k2-fsa/OmniVoice"),
        device_map=profile.get("device", "cuda:0"),
        dtype=torch.float16,
    )


def build_voice_prompt(model: OmniVoice, profile: dict) -> VoiceClonePrompt:
    preprocess = profile.get("preprocess_prompt", True)
    auto_transcribe = profile.get("auto_transcribe", False)

    if auto_transcribe:
        ref_text = None
        logging.info(
            "Tạo voice profile từ %s (Whisper tự nhận diện ref_text)",
            profile["ref_audio_path"],
        )
    else:
        ref_text = read_ref_text(profile)
        logging.info("Tạo voice profile từ %s", profile["ref_audio_path"])

    prompt = model.create_voice_clone_prompt(
        ref_audio=profile["ref_audio_path"],
        ref_text=ref_text,
        preprocess_prompt=preprocess,
    )

    if auto_transcribe:
        ref_text_path = Path(profile["ref_text_path"])
        ref_text_path.write_text(prompt.ref_text, encoding="utf-8")
        logging.info("Đã cập nhật ref_text từ Whisper: %s", ref_text_path)

    return prompt


def save_voice_prompt(prompt: VoiceClonePrompt, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "ref_audio_tokens": prompt.ref_audio_tokens.cpu(),
            "ref_text": prompt.ref_text,
            "ref_rms": prompt.ref_rms,
        },
        path,
    )
    logging.info("Đã lưu voice profile: %s", path)


def load_voice_prompt(path: Path) -> VoiceClonePrompt:
    data = torch.load(path, map_location="cpu", weights_only=True)
    return VoiceClonePrompt(
        ref_audio_tokens=data["ref_audio_tokens"],
        ref_text=data["ref_text"],
        ref_rms=data["ref_rms"],
    )


def ensure_voice_prompt(model: OmniVoice, profile: dict) -> VoiceClonePrompt:
    prompt_path = Path(profile["voice_prompt_path"])
    if prompt_path.exists():
        logging.info("Dùng voice profile có sẵn: %s", prompt_path)
        return load_voice_prompt(prompt_path)
    prompt = build_voice_prompt(model, profile)
    save_voice_prompt(prompt, prompt_path)
    return prompt


def time_stretch_speech(audio: np.ndarray, rate: float) -> np.ndarray:
    """Tăng/giảm tốc audio giữ cao độ, ưu tiên WSOLA cho giọng nói.

    WSOLA (audiotsm) giữ chất giọng tự nhiên hơn nhiều so với phase vocoder
    của librosa khi tăng tốc. Nếu WSOLA lỗi, fallback về librosa.
    """
    rate = float(rate)
    audio = np.ascontiguousarray(audio.astype(np.float32))
    if abs(rate - 1.0) < 1e-3 or audio.size == 0:
        return audio
    try:
        from audiotsm import wsola
        from audiotsm.io.array import ArrayReader, ArrayWriter

        reader = ArrayReader(audio.reshape(1, -1))
        writer = ArrayWriter(channels=1)
        wsola(channels=1, speed=rate).run(reader, writer)
        out = np.asarray(writer.data, dtype=np.float32).flatten()
        if out.size > 0:
            return out
        raise ValueError("WSOLA trả về rỗng")
    except Exception as exc:  # noqa: BLE001
        logging.warning("WSOLA lỗi (%s), dùng librosa phase vocoder", exc)
        return librosa.effects.time_stretch(audio, rate=rate)


def apply_speed_policy(
    audio: np.ndarray,
    sample_rate: int,
    slot_sec: float,
    *,
    speed_mode: str,
    gentle_threshold: float,
) -> tuple[np.ndarray, dict]:
    """Xử lý tốc độ theo chế độ — ưu tiên giữ chất giọng đoạn dài.

    - off: không đổi tốc độ, cascade tràn sang cue sau.
    - gentle: chỉ tăng tốc nhẹ nếu cần <= gentle_threshold (mặc định 1.08).
    - force: ép vừa slot bằng time-stretch (có thể méo giọng).
    """
    generated_sec = len(audio) / sample_rate
    meta = {
        "generated_sec": round(generated_sec, 3),
        "slot_sec": round(slot_sec, 3),
        "required_speed_factor": 1.0,
        "speed_factor": 1.0,
        "speed_mode": speed_mode,
        "gentle_threshold": round(gentle_threshold, 3),
        "speed_fitted": False,
        "speed_skipped": False,
        "speed_skip_reason": None,
    }

    if slot_sec <= 0 or generated_sec <= slot_sec:
        meta["audio_sec"] = round(generated_sec, 3)
        return audio, meta

    required_rate = generated_sec / slot_sec
    meta["required_speed_factor"] = round(required_rate, 3)

    if speed_mode == "off":
        meta["audio_sec"] = round(generated_sec, 3)
        meta["speed_skipped"] = True
        meta["speed_skip_reason"] = "cascade_overflow"
        logging.info(
            "Cue %.2fs > slot %.2fs: giữ nguyên giọng, tràn cascade (cần x%.2f)",
            generated_sec,
            slot_sec,
            required_rate,
        )
        return audio, meta

    if speed_mode == "gentle" and required_rate > gentle_threshold:
        meta["audio_sec"] = round(generated_sec, 3)
        meta["speed_skipped"] = True
        meta["speed_skip_reason"] = "exceeds_gentle_threshold"
        logging.info(
            "Cue dài %.2fs / slot %.2fs (x%.2f > %.2f): giữ nguyên giọng, tràn cascade",
            generated_sec,
            slot_sec,
            required_rate,
            gentle_threshold,
        )
        return audio, meta

    rate = required_rate if speed_mode == "force" else min(required_rate, gentle_threshold)
    stretched = time_stretch_speech(audio, rate)

    if speed_mode == "gentle" or speed_mode == "force":
        target_samples = int(round(slot_sec * sample_rate))
        if len(stretched) > target_samples:
            stretched = stretched[:target_samples]
        elif len(stretched) < target_samples:
            stretched = np.pad(stretched, (0, target_samples - len(stretched)))

    meta["speed_factor"] = round(rate, 3)
    meta["speed_fitted"] = True
    meta["audio_sec"] = round(len(stretched) / sample_rate, 3)
    logging.info(
        "Tăng tốc nhẹ cue: %.2fs -> %.2fs (x%.2f, mode=%s)",
        generated_sec,
        meta["audio_sec"],
        rate,
        speed_mode,
    )
    return stretched, meta


def synthesize(
    model: OmniVoice,
    prompt: VoiceClonePrompt,
    text: str,
    language: str,
    **kwargs,
) -> np.ndarray:
    text = text.strip()
    if not text:
        raise ValueError("Văn bản trống.")
    audios = model.generate(
        text=text,
        language=language,
        voice_clone_prompt=prompt,
        **kwargs,
    )
    return audios[0]


def estimate_natural_duration_sec(
    model: OmniVoice, prompt: VoiceClonePrompt, text: str
) -> float:
    """Ước lượng thời lượng đọc tự nhiên (giây) của text với giọng mẫu.

    Dùng chính bộ ước lượng của model (không cần sinh audio), nhờ đó biết
    trước câu nào sẽ dài hơn khung SRT để quyết định tốc độ native.
    """
    text = text.strip()
    if not text:
        return 0.0
    est_tokens = model.duration_estimator.estimate_duration(
        text,
        prompt.ref_text,
        prompt.ref_audio_tokens.size(-1),
    )
    frame_rate = model.audio_tokenizer.config.frame_rate
    return float(est_tokens) / frame_rate if frame_rate else 0.0


def parse_srt_time(value: str) -> float:
    hh, mm, rest = value.strip().split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def parse_srt(content: str) -> List[SrtCue]:
    content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n\s*\n", content)
    cues: List[SrtCue] = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue
        if not lines[0].isdigit():
            continue
        index = int(lines[0])
        if "-->" not in lines[1]:
            continue
        start_raw, end_raw = [part.strip() for part in lines[1].split("-->")]
        text = " ".join(lines[2:])
        text = re.sub(r"<[^>]+>", "", text).strip()
        if not text:
            continue
        cues.append(
            SrtCue(
                index=index,
                start_sec=parse_srt_time(start_raw),
                end_sec=parse_srt_time(end_raw),
                text=text,
            )
        )
    return cues


def format_srt_time(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    total_ms = int(round(sec * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def plan_cascade_placements(
    cues: List[SrtCue],
    segments: List[np.ndarray],
    sample_rate: int,
) -> List[dict]:
    """Tính vị trí thực tế: cue dài hơn slot sẽ đẩy các cue sau."""
    placements: List[dict] = []
    cursor = 0.0

    for cue, audio in zip(cues, segments):
        audio_sec = len(audio) / sample_rate
        slot_sec = max(0.0, cue.end_sec - cue.start_sec)
        actual_start = max(cue.start_sec, cursor)
        actual_end = actual_start + audio_sec
        pushed = actual_start > cue.start_sec + 0.01
        if pushed:
            overflow_sec = 0.0
        else:
            overflow_sec = max(0.0, actual_end - cue.end_sec)

        placements.append(
            {
                "actual_start_sec": round(actual_start, 3),
                "actual_end_sec": round(actual_end, 3),
                "overflow_sec": round(overflow_sec, 3),
                "pushed_by_previous": pushed,
            }
        )
        if overflow_sec > 0:
            logging.info(
                "Cue %s dài %.2fs / slot %.2fs -> tràn %.2fs, kết thúc %.2fs",
                cue.index,
                audio_sec,
                slot_sec,
                overflow_sec,
                actual_end,
            )
        cursor = actual_end

    return placements


def plan_native_placements(
    cues: List[SrtCue],
    segments: List[np.ndarray],
    sample_rate: int,
) -> List[dict]:
    """Neo cứng mỗi cue đúng mốc SRT gốc — lỗi lệch KHÔNG bao giờ cộng dồn.

    Kiểu lồng tiếng chuyên nghiệp: câu dài hơn khung đã được nói nhanh native
    vừa đủ chứa hết chữ (xử lý lúc sinh audio), nên ở đây chỉ cần đặt từng câu
    đúng vị trí thời gian của nó. Mỗi câu độc lập theo mốc SRT, câu này không
    đẩy câu kia → đồng bộ tiếng/hình ổn định suốt video.
    """
    placements: List[dict] = []
    n = len(cues)

    for i, (cue, audio) in enumerate(zip(cues, segments)):
        audio_sec = len(audio) / sample_rate
        actual_start = cue.start_sec
        actual_end = actual_start + audio_sec
        next_start = cues[i + 1].start_sec if i + 1 < n else actual_end
        overflow = max(0.0, actual_end - next_start)

        placements.append(
            {
                "actual_start_sec": round(actual_start, 3),
                "actual_end_sec": round(actual_end, 3),
                "overflow_sec": round(overflow, 3),
                "pushed_by_previous": False,
            }
        )
        if overflow > 0.05:
            logging.info(
                "Cue %s: vẫn vượt khung %.2fs sau khi tăng tốc (cân nhắc tăng "
                "--native-speed-cap để chứa hết chữ)",
                cue.index,
                overflow,
            )

    return placements


def write_shifted_srt(
    path: Path,
    cues: List[SrtCue],
    placements: List[dict],
) -> None:
    blocks = []
    for cue, placement in zip(cues, placements):
        start = format_srt_time(placement["actual_start_sec"])
        end = format_srt_time(placement["actual_end_sec"])
        blocks.append(f"{cue.index}\n{start} --> {end}\n{cue.text}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def write_manifest(
    path: Path,
    cues: List[SrtCue],
    wav_paths: List[Path],
    fit_metas: List[dict],
    sample_rate: int,
    profile: dict,
    srt_input: Path,
    merge_mode: str,
) -> None:
    rows = []
    for cue, wav, fit_meta in zip(cues, wav_paths, fit_metas):
        slot_sec = max(0.0, cue.end_sec - cue.start_sec)
        rows.append(
            {
                "index": cue.index,
                "start_sec": cue.start_sec,
                "end_sec": cue.end_sec,
                "slot_sec": round(slot_sec, 3),
                "actual_start_sec": fit_meta.get("actual_start_sec"),
                "actual_end_sec": fit_meta.get("actual_end_sec"),
                "overflow_sec": fit_meta.get("overflow_sec", 0.0),
                "pushed_by_previous": fit_meta.get("pushed_by_previous", False),
                "fit_applied": fit_meta.get("fit_applied", False),
                "fit_speed_factor": fit_meta.get("fit_speed_factor", 1.0),
                "generated_sec": fit_meta.get("generated_sec"),
                "audio_sec": fit_meta.get("audio_sec"),
                "required_speed_factor": fit_meta.get("required_speed_factor", 1.0),
                "speed_factor": fit_meta.get("speed_factor", 1.0),
                "speed_mode": fit_meta.get("speed_mode"),
                "gentle_threshold": fit_meta.get("gentle_threshold"),
                "speed_fitted": fit_meta.get("speed_fitted", False),
                "speed_skipped": fit_meta.get("speed_skipped", False),
                "speed_skip_reason": fit_meta.get("speed_skip_reason"),
                "text": cue.text,
                "wav": str(wav),
                "wav_relative": wav.name,
            }
        )
    payload = {
        "voice": profile.get("name", profile["slug"]),
        "voice_slug": profile["slug"],
        "language": profile.get("language"),
        "srt_input": str(srt_input),
        "sample_rate": sample_rate,
        "merge_mode": merge_mode,
        "cues": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_timeline_strict(
    cues: List[SrtCue],
    audio_segments: List[np.ndarray],
    sample_rate: int,
    tail_sec: float = 0.5,
) -> np.ndarray:
    if not cues:
        raise ValueError("Không có cue SRT để gộp.")
    total_sec = max(cue.end_sec for cue in cues) + tail_sec
    merged = np.zeros(int(total_sec * sample_rate), dtype=np.float32)
    for cue, audio in zip(cues, audio_segments):
        start = int(cue.start_sec * sample_rate)
        end = min(start + len(audio), len(merged))
        merged[start:end] = audio[: end - start]
    return _normalize_audio(merged)


def merge_timeline_cascade(
    placements: List[dict],
    audio_segments: List[np.ndarray],
    sample_rate: int,
    tail_sec: float = 0.5,
) -> np.ndarray:
    if not placements:
        raise ValueError("Không có cue SRT để gộp.")
    total_sec = placements[-1]["actual_end_sec"] + tail_sec
    merged = np.zeros(int(total_sec * sample_rate), dtype=np.float32)
    for placement, audio in zip(placements, audio_segments):
        start = int(placement["actual_start_sec"] * sample_rate)
        end = start + len(audio)
        if end > len(merged):
            merged = np.pad(merged, (0, end - len(merged)))
        merged[start:end] = audio
    return _normalize_audio(merged)


def plan_fit_placements(
    cues: List[SrtCue],
    segments: List[np.ndarray],
    sample_rate: int,
    max_speed_factor: float = 1.6,
    min_gap_sec: float = 0.05,
) -> tuple[List[dict], List[np.ndarray]]:
    """Neo mỗi cue đúng mốc SRT gốc, tăng tốc cả câu (giữ pitch) cho vừa khung.

    - Cue vừa khung: giữ nguyên, không đổi tốc độ.
    - Cue tràn, cần tăng tốc <= max_speed_factor: time-stretch vừa đủ -> khớp SRT
      tuyệt đối, giọng tự nhiên (phase vocoder giữ cao độ).
    - Cue tràn nặng, cần > max_speed_factor: chỉ tăng tới trần (giữ giọng),
      phần dư cho tràn nhẹ và tự khớp lại ở các cue ngắn kế tiếp (cascade mềm).
    """
    placements: List[dict] = []
    fitted_segments: List[np.ndarray] = []
    n = len(cues)
    cursor = 0.0

    for i, (cue, audio) in enumerate(zip(cues, segments)):
        audio_sec = len(audio) / sample_rate
        start = max(cue.start_sec, cursor)

        if i + 1 < n:
            room_sec = max(min_gap_sec, cues[i + 1].start_sec - start)
        else:
            room_sec = audio_sec  # cue cuối: không giới hạn

        capped = False
        if audio_sec > room_sec + 1e-3:
            required = audio_sec / room_sec
            rate = min(required, max_speed_factor)
            stretched = time_stretch_speech(audio, rate)
            if rate >= required - 1e-3:
                target = int(round(room_sec * sample_rate))
                if len(stretched) > target:
                    stretched = stretched[:target]
                elif len(stretched) < target:
                    stretched = np.pad(stretched, (0, target - len(stretched)))
            else:
                capped = True
            fitted = True
            speed_factor = rate
        else:
            stretched = audio
            fitted = False
            speed_factor = 1.0

        seg_sec = len(stretched) / sample_rate
        actual_end = start + seg_sec
        next_start = cues[i + 1].start_sec if i + 1 < n else actual_end
        overflow = max(0.0, actual_end - next_start)
        placements.append(
            {
                "actual_start_sec": round(start, 3),
                "actual_end_sec": round(actual_end, 3),
                "overflow_sec": round(overflow, 3),
                "pushed_by_previous": start > cue.start_sec + 0.01,
                "fit_applied": fitted,
                "fit_speed_factor": round(speed_factor, 3),
                "fit_capped": capped,
            }
        )
        fitted_segments.append(stretched)
        cursor = actual_end
        if fitted:
            logging.info(
                "Cue %s: %.2fs -> %.2fs (x%.2f%s)",
                cue.index,
                audio_sec,
                seg_sec,
                speed_factor,
                ", chạm trần - tràn nhẹ" if capped else "",
            )

    return placements, fitted_segments


def merge_timeline_fit(
    placements: List[dict],
    fitted_segments: List[np.ndarray],
    sample_rate: int,
    tail_sec: float = 0.5,
) -> np.ndarray:
    if not placements:
        raise ValueError("Không có cue SRT để gộp.")
    total_sec = placements[-1]["actual_end_sec"] + tail_sec
    merged = np.zeros(int(total_sec * sample_rate), dtype=np.float32)
    for placement, audio in zip(placements, fitted_segments):
        start = int(placement["actual_start_sec"] * sample_rate)
        end = start + len(audio)
        if end > len(merged):
            merged = np.pad(merged, (0, end - len(merged)))
        merged[start:end] = audio
    return _normalize_audio(merged)


def _normalize_audio(audio: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak > 1.0:
        return audio / peak * 0.98
    return audio


def cmd_build(args: argparse.Namespace) -> None:
    profile = load_profile(Path(args.profile))
    model = load_model(profile)
    prompt = build_voice_prompt(model, profile)
    save_voice_prompt(prompt, Path(profile["voice_prompt_path"]))


def cmd_text(args: argparse.Namespace) -> None:
    profile = load_profile(Path(args.profile))
    model = load_model(profile)
    prompt = ensure_voice_prompt(model, profile)
    audio = synthesize(
        model,
        prompt,
        args.text,
        profile["language"],
        num_step=args.num_step,
        class_temperature=args.class_temperature,
        guidance_scale=args.guidance_scale,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(out, audio, model.sampling_rate)
    logging.info("Đã lưu: %s", out)


def cmd_file(args: argparse.Namespace) -> None:
    text = Path(args.input).read_text(encoding="utf-8").strip()
    ns = argparse.Namespace(**vars(args))
    ns.text = text
    cmd_text(ns)


def cmd_voices(_: argparse.Namespace) -> None:
    profiles = discover_profiles()
    if not profiles:
        print("Chưa có giọng nào trong voices/*/profile.json")
        return
    for path in profiles:
        profile = load_profile(path)
        ready = Path(profile["voice_prompt_path"]).exists()
        status = "ready" if ready else "missing voice.pt"
        print(f"- {profile['slug']}: {profile.get('name', profile['slug'])} [{status}]")
        print(f"  profile: {path}")


def list_voice_choices() -> List[tuple[str, str, str]]:
    rows = []
    for path in discover_profiles():
        profile = load_profile(path)
        ready = Path(profile["voice_prompt_path"]).exists()
        label = f"{profile.get('name', profile['slug'])} ({'ready' if ready else 'no .pt'})"
        rows.append((profile["slug"], label, str(path)))
    return rows


def _pipe_log(log_lines: List[str], line: str, on_log: Optional[Callable[[str], None]] = None) -> None:
    log_lines.append(line)
    if on_log is not None:
        on_log(line)


def run_srt_pipeline(
    profile_path: Path,
    srt_path: Path,
    *,
    output_dir: Optional[Path] = None,
    merge: bool = False,
    merge_output: Optional[Path] = None,
    merge_mode: str = "cascade",
    speed_mode: str = "off",
    gentle_threshold: float = 1.08,
    max_speed_factor: float = 1.6,
    native_speed_cap: float = 2.0,
    num_step: int = 32,
    class_temperature: float = DEFAULT_CLASS_TEMPERATURE,
    guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
    skip_existing: bool = False,
    from_cue: Optional[int] = None,
    to_cue: Optional[int] = None,
    model: Optional[OmniVoice] = None,
    prompt: Optional[VoiceClonePrompt] = None,
    progress=None,
    on_log: Optional[Callable[[str], None]] = None,
) -> dict:
    if speed_mode == "gentle" and gentle_threshold <= 1.0:
        raise ValueError("--gentle-threshold phải lớn hơn 1.0")

    profile = load_profile(profile_path)
    if model is None:
        model = load_model(profile)
    if prompt is None:
        prompt = ensure_voice_prompt(model, profile)

    srt_path = Path(srt_path)
    content = srt_path.read_text(encoding="utf-8")
    cues = parse_srt(content)
    if not cues:
        raise ValueError("Không đọc được cue nào từ file SRT.")

    if from_cue is not None:
        cues = [c for c in cues if c.index >= from_cue]
    if to_cue is not None:
        cues = [c for c in cues if c.index <= to_cue]
    if not cues:
        raise ValueError("Không còn cue nào sau khi lọc from/to.")

    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = default_output_dir(profile, srt_path.stem)
    output_dir.mkdir(parents=True, exist_ok=True)

    wav_paths: List[Path] = []
    segments: List[np.ndarray] = []
    fit_metas: List[dict] = []
    log_lines: List[str] = []
    generated = 0
    skipped = 0
    speed_fitted_count = 0
    speed_skipped_count = 0
    merged_path: Optional[Path] = None
    total = len(cues)
    _pipe_log(log_lines, f"Bắt đầu: {total} cue | chế độ ghép: {merge_mode}", on_log)

    for idx, cue in enumerate(cues):
        if progress is not None:
            progress(idx / max(total, 1), desc=f"Cue {cue.index}/{total}")

        wav_path = output_dir / f"{cue.index:04d}.wav"
        slot_sec = max(0.0, cue.end_sec - cue.start_sec)

        if skip_existing and wav_path.exists():
            audio, sr = sf.read(wav_path, dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            audio_sec = len(audio) / sr
            segments.append(audio)
            wav_paths.append(wav_path)
            fit_metas.append(
                {
                    "generated_sec": round(audio_sec, 3),
                    "audio_sec": round(audio_sec, 3),
                    "slot_sec": round(slot_sec, 3),
                    "required_speed_factor": 1.0,
                    "speed_factor": 1.0,
                    "speed_mode": speed_mode,
                    "gentle_threshold": round(gentle_threshold, 3),
                    "speed_fitted": False,
                    "speed_skipped": False,
                    "speed_skip_reason": None,
                }
            )
            skipped += 1
            _pipe_log(log_lines, f"[skip] Cue {cue.index}: {wav_path.name}", on_log)
            if progress is not None:
                progress((idx + 1) / max(total, 1), desc=f"Xong cue {cue.index}/{total}")
            continue

        _pipe_log(log_lines, f"[gen] Cue {cue.index} ({slot_sec:.1f}s): {cue.text[:50]}...", on_log)

        native_meta: Optional[dict] = None
        gen_duration: Optional[float] = None
        if merge_mode == "native":
            # Ngân sách = thời gian tới khi cue kế bắt đầu (slot + khoảng lặng sau).
            if idx + 1 < total:
                budget = max(0.05, cues[idx + 1].start_sec - cue.start_sec)
            else:
                budget = None
            if budget is not None and budget > 0:
                # Chừa biên an toàn nhỏ để phần đệm fade/pad ở đuôi không đè
                # sang cue sau (tránh cảm giác mất chữ/đè đuôi).
                fit_target = max(0.1, budget - 0.12)
                natural_sec = estimate_natural_duration_sec(model, prompt, cue.text)
                if natural_sec > fit_target + 1e-3:
                    # Ép native vừa khít, không vượt trần tốc độ.
                    gen_duration = round(
                        max(fit_target, natural_sec / native_speed_cap), 3
                    )
                    native_meta = {
                        "natural_sec": round(natural_sec, 3),
                        "budget_sec": round(budget, 3),
                        "native_duration_sec": gen_duration,
                        "native_speed_factor": round(
                            natural_sec / gen_duration, 3
                        )
                        if gen_duration
                        else 1.0,
                        "native_capped": natural_sec / native_speed_cap
                        > fit_target + 1e-3,
                    }

        synth_kwargs = dict(
            num_step=num_step,
            class_temperature=class_temperature,
            guidance_scale=guidance_scale,
        )
        if gen_duration is not None:
            synth_kwargs["duration"] = gen_duration

        audio = synthesize(
            model,
            prompt,
            cue.text,
            profile["language"],
            **synth_kwargs,
        )

        if merge_mode == "native":
            audio_sec = len(audio) / model.sampling_rate
            fit_meta = {
                "generated_sec": round(audio_sec, 3),
                "audio_sec": round(audio_sec, 3),
                "slot_sec": round(slot_sec, 3),
                "required_speed_factor": 1.0,
                "speed_factor": 1.0,
                "speed_mode": "native",
                "gentle_threshold": round(gentle_threshold, 3),
                "speed_fitted": gen_duration is not None,
                "speed_skipped": False,
                "speed_skip_reason": None,
            }
            if native_meta is not None:
                fit_meta.update(native_meta)
                speed_fitted_count += 1
                if native_meta.get("native_capped"):
                    _pipe_log(
                        log_lines,
                        f"  Cue {cue.index}: native {native_meta['natural_sec']}s "
                        f"-> {native_meta['native_duration_sec']}s "
                        f"(x{native_meta['native_speed_factor']}, chạm trần - tràn nhẹ)",
                        on_log,
                    )
        elif slot_sec > 0 and merge_mode != "fit":
            audio, fit_meta = apply_speed_policy(
                audio,
                model.sampling_rate,
                slot_sec,
                speed_mode=speed_mode,
                gentle_threshold=gentle_threshold,
            )
            if fit_meta["speed_fitted"]:
                speed_fitted_count += 1
            if fit_meta.get("speed_skipped"):
                speed_skipped_count += 1
        else:
            audio_sec = len(audio) / model.sampling_rate
            fit_meta = {
                "generated_sec": round(audio_sec, 3),
                "audio_sec": round(audio_sec, 3),
                "slot_sec": round(slot_sec, 3),
                "required_speed_factor": 1.0,
                "speed_factor": 1.0,
                "speed_mode": speed_mode,
                "gentle_threshold": round(gentle_threshold, 3),
                "speed_fitted": False,
                "speed_skipped": False,
                "speed_skip_reason": None,
            }

        sf.write(wav_path, audio, model.sampling_rate)
        wav_paths.append(wav_path)
        segments.append(audio)
        fit_metas.append(fit_meta)
        generated += 1
        if progress is not None:
            progress((idx + 1) / max(total, 1), desc=f"Xong cue {cue.index}/{total}")

    if progress is not None:
        progress(0.9, desc="Đang canh giờ & ghi manifest")
    fitted_segments: Optional[List[np.ndarray]] = None
    if merge_mode == "native":
        placements = plan_native_placements(cues, segments, model.sampling_rate)
    elif merge_mode == "cascade":
        placements = plan_cascade_placements(cues, segments, model.sampling_rate)
    elif merge_mode == "fit":
        placements, fitted_segments = plan_fit_placements(
            cues, segments, model.sampling_rate, max_speed_factor=max_speed_factor
        )
    else:
        placements = [
            {
                "actual_start_sec": round(cue.start_sec, 3),
                "actual_end_sec": round(
                    cue.start_sec + len(audio) / model.sampling_rate, 3
                ),
                "overflow_sec": 0.0,
                "pushed_by_previous": False,
            }
            for cue, audio in zip(cues, segments)
        ]

    overflow_count = sum(1 for p in placements if p["overflow_sec"] > 0)
    pushed_count = sum(1 for p in placements if p["pushed_by_previous"])
    fit_count = sum(1 for p in placements if p.get("fit_applied"))
    capped_count = sum(1 for p in placements if p.get("fit_capped"))

    for fit_meta, placement in zip(fit_metas, placements):
        fit_meta.update(placement)

    manifest = output_dir / "manifest.json"
    write_manifest(
        manifest,
        cues,
        wav_paths,
        fit_metas,
        model.sampling_rate,
        profile,
        srt_path,
        merge_mode,
    )

    shifted_srt = output_dir / f"{srt_path.stem}_shifted.srt"
    write_shifted_srt(shifted_srt, cues, placements)

    if merge_mode == "fit":
        summary = (
            f"Hoàn tất [{profile['slug']}] (fit): {generated} cue mới, "
            f"{fit_count} cue tăng tốc khớp giờ ({capped_count} chạm trần, tràn nhẹ), "
            f"{skipped} bỏ qua"
        )
    elif merge_mode == "native":
        native_capped = sum(1 for m in fit_metas if m.get("native_capped"))
        summary = (
            f"Hoàn tất [{profile['slug']}] (native): {generated} cue mới, "
            f"{speed_fitted_count} cue nói nhanh native cho vừa khung "
            f"({native_capped} câu chạm trần x{native_speed_cap}, còn vượt khung; "
            f"neo cứng SRT - không cộng dồn lệch), {skipped} bỏ qua"
        )
    else:
        summary = (
            f"Hoàn tất [{profile['slug']}] ({merge_mode}): {generated} cue mới, "
            f"{overflow_count} tràn, {pushed_count} đẩy, {speed_fitted_count} tăng tốc nhẹ, "
            f"{speed_skipped_count} giữ giọng, {skipped} bỏ qua"
        )
    for line in (
        summary,
        f"Output: {output_dir}",
        f"Manifest: {manifest}",
        f"Shifted SRT: {shifted_srt}",
    ):
        _pipe_log(log_lines, line, on_log)

    if merge:
        if progress is not None:
            progress(0.95, desc="Đang ghép file WAV")
        _pipe_log(log_lines, "Đang ghép file WAV...", on_log)
        if merge_mode in ("cascade", "native"):
            merged = merge_timeline_cascade(
                placements, segments, model.sampling_rate
            )
        elif merge_mode == "fit":
            merged = merge_timeline_fit(
                placements, fitted_segments or segments, model.sampling_rate
            )
        else:
            merged = merge_timeline_strict(cues, segments, model.sampling_rate)
        merge_out = (
            Path(merge_output)
            if merge_output
            else output_dir / f"{srt_path.stem}_merged.wav"
        )
        merge_out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(merge_out, merged, model.sampling_rate)
        merged_path = merge_out
        _pipe_log(log_lines, f"Merged WAV: {merge_out}", on_log)

    if progress is not None:
        progress(1.0, desc="Hoàn tất")

    return {
        "output_dir": str(output_dir),
        "manifest": str(manifest),
        "shifted_srt": str(shifted_srt),
        "merged_wav": str(merged_path) if merged_path else None,
        "sample_rate": model.sampling_rate,
        "stats": {
            "generated": generated,
            "overflow": overflow_count,
            "pushed": pushed_count,
            "speed_fitted": speed_fitted_count,
            "speed_skipped": speed_skipped_count,
            "skipped": skipped,
        },
        "log": "\n".join(log_lines),
    }


def cmd_srt(args: argparse.Namespace) -> None:
    result = run_srt_pipeline(
        Path(args.profile),
        Path(args.input),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        merge=args.merge,
        merge_output=Path(args.output) if args.output else None,
        merge_mode=args.merge_mode,
        speed_mode=args.speed_mode,
        gentle_threshold=args.gentle_threshold,
        max_speed_factor=args.max_speed_factor,
        native_speed_cap=args.native_speed_cap,
        num_step=args.num_step,
        class_temperature=args.class_temperature,
        guidance_scale=args.guidance_scale,
        skip_existing=args.skip_existing,
        from_cue=args.from_cue,
        to_cue=args.to_cue,
    )
    print(result["log"])


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Đọc văn bản/SRT bằng voice profile trong voices/",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=str(DEFAULT_PROFILE),
        help="Đường dẫn profile.json",
    )
    parser.add_argument(
        "--num-step",
        type=int,
        default=32,
        help="Số bước diffusion (16 = nhanh hơn, 32 = chất lượng cao hơn)",
    )
    parser.add_argument(
        "--class-temperature",
        type=float,
        default=DEFAULT_CLASS_TEMPERATURE,
        help="Độ biểu cảm: nhiệt độ lấy mẫu token. 0 = đều/máy móc (greedy), "
        "0.7-0.9 = nhấn nhá tự nhiên, >1.0 = ngẫu hứng mạnh hơn",
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=DEFAULT_GUIDANCE_SCALE,
        help="Mức bám giọng mẫu (CFG). Cao hơn = rõ/chắc giọng, thấp hơn = mềm hơn",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_voices = sub.add_parser("voices", help="Liệt kê các giọng có sẵn")
    p_voices.set_defaults(func=cmd_voices)

    p_build = sub.add_parser("build", help="Tạo file voice.pt từ audio mẫu")
    p_build.set_defaults(func=cmd_build)

    p_text = sub.add_parser("text", help="Đọc một đoạn văn bản")
    p_text.add_argument("--text", required=True)
    p_text.add_argument("-o", "--output", required=True)
    p_text.set_defaults(func=cmd_text)

    p_file = sub.add_parser("file", help="Đọc cả file .txt")
    p_file.add_argument("--input", required=True)
    p_file.add_argument("-o", "--output", required=True)
    p_file.set_defaults(func=cmd_file)

    p_srt = sub.add_parser("srt", help="Đọc file phụ đề .srt")
    p_srt.add_argument("--input", required=True)
    p_srt.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Thư mục lưu từng cue. Mặc định: output/<voice>/<ten_srt>/",
    )
    p_srt.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="File WAV gộp khi dùng --merge",
    )
    p_srt.add_argument(
        "--merge",
        action="store_true",
        help="Gộp các cue thành 1 file WAV",
    )
    p_srt.add_argument(
        "--merge-mode",
        choices=["native", "fit", "cascade", "strict"],
        default="native",
        help="native: model nói nhanh native (giữ nhấn nhá) có trần tốc độ, "
        "phần dư tràn nhẹ/cascade - khuyến nghị cho lồng tiếng; "
        "fit: sinh dài rồi kéo nén tín hiệu vừa khung SRT (khít giờ, dễ mất nhấn nhá); "
        "cascade: cue dài tràn/đẩy cue sau (giữ chất giọng, lệch SRT); "
        "strict: ghép theo timestamp gốc (có thể cắt audio)",
    )
    p_srt.add_argument(
        "--speed-mode",
        choices=["off", "gentle", "force"],
        default="off",
        help="off: giữ giọng, tràn cascade (mặc định); "
        "gentle: chỉ tăng tốc nhẹ khi hơn slot <= gentle-threshold; "
        "force: ép vừa slot (có thể méo giọng)",
    )
    p_srt.add_argument(
        "--gentle-threshold",
        type=float,
        default=1.08,
        help="Với gentle: chỉ tăng tốc nếu cần <= hệ số này (vd. 1.08 = 8%%)",
    )
    p_srt.add_argument(
        "--max-speed-factor",
        type=float,
        default=1.6,
        help="Với fit: trần tăng tốc 1 câu để giữ giọng tự nhiên (vd. 1.6 = 60%%). "
        "Câu cần hơn trần sẽ tràn nhẹ và tự khớp lại sau",
    )
    p_srt.add_argument(
        "--native-speed-cap",
        type=float,
        default=2.0,
        help="Với native: trần tốc độ nói native để chứa hết chữ trong khung "
        "(vd. 2.0 = nói nhanh tối đa gấp đôi). Cao hơn = chắc chắn đủ chữ nhưng "
        "câu dài nói nhanh hơn; thấp hơn = giữ nhấn nhá nhưng câu rất dài có thể "
        "vẫn vượt khung",
    )
    p_srt.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua cue đã có file WAV (tiếp tục job dở)",
    )
    p_srt.add_argument("--from-cue", type=int, default=None, help="Cue bắt đầu")
    p_srt.add_argument("--to-cue", type=int, default=None, help="Cue kết thúc")
    p_srt.set_defaults(func=cmd_srt)

    return parser


def _force_utf8_stdio() -> None:
    """Tránh UnicodeEncodeError khi in tiếng Việt trên console Windows (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError, AttributeError):
                pass


class _SafeLogHandler(logging.StreamHandler):
    """Handler log không crash khi console Windows không hỗ trợ Unicode."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            record.msg = str(record.getMessage()).encode("ascii", errors="replace").decode("ascii")
            record.args = ()
            super().emit(record)


def _setup_logging() -> None:
    _force_utf8_stdio()
    root = logging.getLogger()
    if root.handlers:
        return
    handler = _SafeLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def main() -> None:
    _setup_logging()
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
else:
    _setup_logging()
