"""ThienVoice CLI — test nhanh từ command line.

Cách dùng:

  TTS:
    python app_mvp/cli.py tts --text "Xin chào..." --speed normal

  Clone Voice:
    python app_mvp/cli.py clone --text "Xin chào..." --ref voices/sample.wav --speed normal
    python app_mvp/cli.py clone --text "Xin chào..." --ref voices/sample.wav --ref-text "Nội dung audio mẫu." --speed normal

  Voice Design:
    python app_mvp/cli.py design --text "Xin chào..." --voice "giọng nam, trưởng thành" --speed normal

  Chỉ định đường dẫn output:
    python app_mvp/cli.py tts --text "..." --output outputs/my_tts.wav
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Đảm bảo chạy được từ thư mục gốc repo
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _setup_logging(log_dir: str = "logs"):
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"omnivoice_{ts}.log")

    fmt = "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )
    logging.info("Log file: %s", os.path.abspath(log_file))
    return log_file


def _ts_output(prefix: str, ext: str = "wav") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"outputs/{prefix}_{ts}.{ext}"


def cmd_voices(args):
    from app_mvp.vi_voice_profiles import validate_vi_voice_assets, get_default_vi_voice

    print()
    print("6 voice preset tiếng Việt (STBack23/omnivoice-vi)")
    print("=" * 58)
    default = get_default_vi_voice()
    results = validate_vi_voice_assets()
    for slug, info in results.items():
        tag = " [default]" if slug == default else ""
        ready = "READY" if info["ready"] else "MISSING"
        pt_ok = "voice.pt OK" if info["voice_pt_loadable"] else (
            "voice.pt MISSING" if not info["voice_pt"] else "voice.pt ERROR"
        )
        fallback = " (fallback ref.wav)" if (
            not info["voice_pt_loadable"] and info["ref_audio"]
        ) else ""
        err = f"  [!] {info['error']}" if info["error"] else ""
        print(f"  {slug:<14} {info['display_name']:<14} [{ready}]  {pt_ok}{fallback}{tag}{err}")
    print()
    print("Dung: .venv\\Scripts\\python.exe app_mvp\\cli.py tts --text '...' --voice-preset <slug>")


def cmd_tts(args):
    from app_mvp.core_engine import generate_tts
    output = args.output or _ts_output("tts")
    path = generate_tts(
        text=args.text,
        speed=args.speed,
        output_path=output,
        voice_preset=args.voice_preset,
        model_name=args.model,
    )
    print(f"\n✓ TTS hoàn thành ({args.voice_preset}): {path}")


def cmd_clone(args):
    from app_mvp.core_engine import generate_clone
    output = args.output or _ts_output("clone")
    ref_text = args.ref_text if args.ref_text else ""
    path = generate_clone(
        text=args.text,
        reference_audio_path=args.ref,
        reference_transcript=ref_text,
        speed=args.speed,
        output_path=output,
        model_name=args.model,
    )
    print(f"\n✓ Clone Voice hoàn thành: {path}")


def cmd_design(args):
    from app_mvp.core_engine import generate_voice_design
    output = args.output or _ts_output("design")
    path = generate_voice_design(
        text=args.text,
        voice_description=args.voice,
        speed=args.speed,
        output_path=output,
        model_name=args.model,
    )
    print(f"\n✓ Voice Design hoàn thành: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python app_mvp/cli.py",
        description="ThienVoice — TTS / Clone / Design tiếng Việt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default="k2-fsa/OmniVoice",
        help="Model checkpoint (HuggingFace repo id hoặc đường dẫn local). "
             "Mặc định: k2-fsa/OmniVoice",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Thư mục lưu log. Mặc định: logs/",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --- VOICES ---
    p_voices = sub.add_parser("voices", help="Liệt kê 6 voice preset tiếng Việt")
    p_voices.set_defaults(func=cmd_voices)

    # --- TTS ---
    p_tts = sub.add_parser("tts", help="Text to Speech tiếng Việt (dùng voice preset)")
    p_tts.add_argument("--text", required=True, help="Văn bản tiếng Việt cần đọc")
    p_tts.add_argument(
        "--voice-preset",
        default="tuong_vy",
        dest="voice_preset",
        metavar="SLUG",
        help=(
            "Voice preset slug. Mặc định: tuong_vy\n"
            "Các giá trị: ban_mai, lan_trinh, ngan_ha, "
            "ngoc_huyen, thao_trinh, tuong_vy"
        ),
    )
    p_tts.add_argument(
        "--speed",
        default="normal",
        choices=["slow", "normal", "fast"],
        help="Tốc độ đọc: slow=0.85x | normal=1.0x | fast=1.15x (mặc định: normal)",
    )
    p_tts.add_argument(
        "--output",
        default=None,
        help="Đường dẫn file WAV output. Mặc định: outputs/vi_presets/<voice>.wav",
    )
    p_tts.set_defaults(func=cmd_tts)

    # --- Clone ---
    p_clone = sub.add_parser("clone", help="Clone giọng từ audio mẫu")
    p_clone.add_argument("--text", required=True, help="Văn bản tiếng Việt cần đọc")
    p_clone.add_argument(
        "--ref",
        required=True,
        metavar="AUDIO_PATH",
        help="Đường dẫn file WAV/MP3 mẫu giọng (khuyến nghị 3–10 giây)",
    )
    p_clone.add_argument(
        "--ref-text",
        default="",
        metavar="TRANSCRIPT",
        help="Transcript của audio mẫu (tùy chọn). Để trống để tự động nhận dạng "
             "bằng Whisper (cần tải ~1.5GB lần đầu).",
    )
    p_clone.add_argument(
        "--speed",
        default="normal",
        choices=["slow", "normal", "fast"],
        help="Tốc độ đọc (mặc định: normal)",
    )
    p_clone.add_argument(
        "--output",
        default=None,
        help="Đường dẫn file WAV output. Mặc định: outputs/clone_<timestamp>.wav",
    )
    p_clone.set_defaults(func=cmd_clone)

    # --- Design ---
    p_design = sub.add_parser(
        "design",
        help="[EXPERIMENTAL] Voice Design từ mô tả tiếng Việt — chất lượng VI không ổn định",
    )
    p_design.add_argument("--text", required=True, help="Văn bản tiếng Việt cần đọc")
    p_design.add_argument(
        "--voice",
        required=True,
        metavar="DESCRIPTION",
        help=(
            "Mô tả giọng bằng tiếng Việt. Ví dụ:\n"
            '  "giọng nam, trưởng thành"\n'
            '  "giọng nữ, thì thầm, âm cao"\n'
            "Keyword được map tự động sang OmniVoice instruct. "
            "Các từ không nhận dạng được (rõ ràng, chuyên nghiệp...) sẽ bị bỏ qua."
        ),
    )
    p_design.add_argument(
        "--speed",
        default="normal",
        choices=["slow", "normal", "fast"],
        help="Tốc độ đọc (mặc định: normal)",
    )
    p_design.add_argument(
        "--output",
        default=None,
        help="Đường dẫn file WAV output. Mặc định: outputs/design_<timestamp>.wav",
    )
    p_design.set_defaults(func=cmd_design)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(args.log_dir)
    try:
        args.func(args)
    except FileNotFoundError as e:
        logging.error("File không tồn tại: %s", e)
        sys.exit(1)
    except ValueError as e:
        logging.error("Lỗi tham số: %s", e)
        sys.exit(1)
    except Exception as e:
        logging.exception("Lỗi không mong đợi: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

