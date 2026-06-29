"""Test nhanh 2 giọng Việt: tuong_vy và ban_mai.

Output:
    outputs/vi_presets/tuong_vy.wav
    outputs/vi_presets/ban_mai.wav

Chạy:
    .venv\\Scripts\\python.exe app_mvp\\test_vi_voice_quick.py
"""

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

from app_mvp.core_engine import generate_preset_tts

TEST_VOICES = ["tuong_vy", "ban_mai"]

TEST_TEXT = (
    "Xin chào, đây là bản kiểm tra giọng đọc tiếng Việt bằng OmniVoice. "
    "Hôm nay tôi sẽ giới thiệu một dự án bất động sản nổi bật tại khu Nam Sài Gòn."
)

OUTPUT_DIR = _REPO_ROOT / "outputs" / "vi_presets"


def main():
    print("=" * 60)
    print("Quick test: tuong_vy + ban_mai")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = {}

    for voice in TEST_VOICES:
        out = str(OUTPUT_DIR / f"{voice}.wav")
        print(f"\n[{voice}] Đang generate...")
        t0 = time.time()
        try:
            path = generate_preset_tts(
                text=TEST_TEXT,
                voice_preset=voice,
                speed="normal",
                output_path=out,
            )
            elapsed = time.time() - t0
            results[voice] = {"ok": True, "path": path, "time": elapsed}
            print(f"[{voice}] OK — {elapsed:.1f}s → {path}")
        except Exception as e:
            elapsed = time.time() - t0
            results[voice] = {"ok": False, "error": str(e), "time": elapsed}
            logging.error("[%s] FAILED: %s", voice, e)

    print()
    print("=" * 60)
    print("KẾT QUẢ")
    print("=" * 60)
    for voice, r in results.items():
        if r["ok"]:
            print(f"  [OK]   {voice:<14} {r['time']:.1f}s  {r['path']}")
        else:
            print(f"  [FAIL] {voice:<14} {r['time']:.1f}s  {r['error'][:80]}")

    all_ok = all(r["ok"] for r in results.values())
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
