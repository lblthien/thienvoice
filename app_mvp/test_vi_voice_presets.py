"""Test đầy đủ 6 voice preset tiếng Việt từ STBack23/omnivoice-vi.

Cách dùng:
    # Test 1 giọng
    .venv\\Scripts\\python.exe app_mvp\\test_vi_voice_presets.py --voice tuong_vy

    # Test tất cả 6 giọng
    .venv\\Scripts\\python.exe app_mvp\\test_vi_voice_presets.py --all

Output:
    outputs/vi_presets/ban_mai.wav
    outputs/vi_presets/lan_trinh.wav
    outputs/vi_presets/ngan_ha.wav
    outputs/vi_presets/ngoc_huyen.wav
    outputs/vi_presets/thao_trinh.wav
    outputs/vi_presets/tuong_vy.wav
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.makedirs(_REPO_ROOT / "logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

from app_mvp.vi_voice_profiles import VI_VOICE_SLUGS, slug_to_display_name
from app_mvp.core_engine import generate_preset_tts

TEST_TEXT = (
    "Xin chào, đây là bản kiểm tra giọng đọc tiếng Việt bằng OmniVoice. "
    "Hôm nay tôi sẽ giới thiệu một dự án bất động sản nổi bật tại khu Nam Sài Gòn."
)

OUTPUT_DIR = _REPO_ROOT / "outputs" / "vi_presets"

# Settings chất lượng
GEN_KWARGS = dict(
    num_step=32,
    guidance_scale=2.0,
    class_temperature=0.4,
)


def run_voice(voice: str) -> dict:
    out = str(OUTPUT_DIR / f"{voice}.wav")
    display = slug_to_display_name(voice)
    print(f"\n[{display} / {voice}] Đang generate...")
    t0 = time.time()
    try:
        path = generate_preset_tts(
            text=TEST_TEXT,
            voice_preset=voice,
            speed="normal",
            output_path=out,
            **GEN_KWARGS,
        )
        elapsed = time.time() - t0

        import soundfile as sf
        info = sf.info(path)
        return {
            "ok": True, "voice": voice, "display": display,
            "path": path, "time": elapsed,
            "duration": round(info.duration, 2),
            "size_kb": round(os.path.getsize(path) / 1024, 1),
        }
    except Exception as e:
        elapsed = time.time() - t0
        logging.error("[%s] FAILED in %.1fs: %s", voice, elapsed, e)
        return {
            "ok": False, "voice": voice, "display": display,
            "error": str(e), "time": elapsed,
        }


def print_summary(results: list):
    print()
    print("=" * 70)
    print("TỔNG KẾT")
    print("=" * 70)
    total_time = sum(r["time"] for r in results)
    for r in results:
        if r["ok"]:
            print(
                f"  [OK]   {r['voice']:<14} {r['display']:<14} "
                f"{r['time']:>6.1f}s  {r['duration']}s audio  {r['path']}"
            )
        else:
            print(
                f"  [FAIL] {r['voice']:<14} {r['display']:<14} "
                f"{r['time']:>6.1f}s  {r['error'][:60]}"
            )
    ok_count = sum(1 for r in results if r["ok"])
    print(f"\n  {ok_count}/{len(results)} voices OK | Tổng thời gian: {total_time:.1f}s")
    print(f"  Output dir: {OUTPUT_DIR}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Test voice preset tiếng Việt (STBack23/omnivoice-vi)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--voice",
        metavar="SLUG",
        help=(
            "Test 1 giọng cụ thể.\n"
            f"Các giá trị: {', '.join(VI_VOICE_SLUGS)}"
        ),
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Test tất cả 6 giọng (CPU: ~25-30 phút)",
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.voice:
        if args.voice not in VI_VOICE_SLUGS:
            print(f"[LOI] Voice '{args.voice}' khong hop le.")
            print(f"      Cac voice hop le: {', '.join(VI_VOICE_SLUGS)}")
            sys.exit(1)
        voices = [args.voice]
    else:
        voices = list(VI_VOICE_SLUGS)

    print("=" * 60)
    print(f"Test {len(voices)} voice preset(s): {', '.join(voices)}")
    print(f"Settings: num_step={GEN_KWARGS['num_step']} "
          f"guidance_scale={GEN_KWARGS['guidance_scale']} "
          f"class_temperature={GEN_KWARGS['class_temperature']}")
    if len(voices) > 1:
        print(f"[INFO] CPU mode: uoc tinh ~{len(voices)*4-5}-{len(voices)*5} phut")
    print("=" * 60)

    results = [run_voice(v) for v in voices]
    print_summary(results)

    all_ok = all(r["ok"] for r in results)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
