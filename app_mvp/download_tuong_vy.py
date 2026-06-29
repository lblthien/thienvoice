"""Tải voice preset tuong_vy từ dataset STBack23/omnivoice-vi.

Tải toàn bộ dataset về assets/omnivoice-vi/ (nhỏ, ~vài MB).
Sau khi tải xong, các file tuong_vy nằm tại:
    assets/omnivoice-vi/voices/tuong_vy/profile.json
    assets/omnivoice-vi/voices/tuong_vy/voice.pt
    assets/omnivoice-vi/voices/tuong_vy/ref.wav
    assets/omnivoice-vi/voices/tuong_vy/ref_text.txt

Chạy:
    .venv\\Scripts\\python.exe app_mvp\\download_tuong_vy.py
"""

import json
import os
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DATASET_REPO = "STBack23/omnivoice-vi"
LOCAL_DIR    = _REPO_ROOT / "assets" / "omnivoice-vi"
VOICE_NAME   = "tuong_vy"
VOICE_DIR    = LOCAL_DIR / "voices" / VOICE_NAME


def download_dataset():
    from huggingface_hub import snapshot_download

    print(f"Downloading dataset {DATASET_REPO} ...")
    print(f"  → {LOCAL_DIR}")

    # snapshot_download copies files to local_dir (không dùng symlink)
    snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        local_dir=str(LOCAL_DIR),
        ignore_patterns=["*.gitattributes", ".git/*"],
    )
    print("Download complete.")


def verify_tuong_vy():
    expected = [
        VOICE_DIR / "profile.json",
        VOICE_DIR / "voice.pt",
        VOICE_DIR / "ref_text.txt",
    ]
    # ref audio có thể là ref.wav hoặc ref.mp3
    ref_audio = next(
        (VOICE_DIR / f for f in ("ref.wav", "ref.mp3") if (VOICE_DIR / f).exists()),
        None,
    )

    print(f"\nKiểm tra {VOICE_NAME}:")
    all_ok = True
    for p in expected:
        exists = p.exists()
        size = f"{p.stat().st_size / 1024:.1f} KB" if exists else "—"
        status = "OK" if exists else "MISSING"
        print(f"  [{status}] {p.name}  {size}")
        if not exists:
            all_ok = False

    if ref_audio:
        size = f"{ref_audio.stat().st_size / 1024:.1f} KB"
        print(f"  [OK] {ref_audio.name}  {size}")
    else:
        print("  [MISSING] ref.wav / ref.mp3")
        all_ok = False

    # In nội dung profile.json
    profile_path = VOICE_DIR / "profile.json"
    if profile_path.exists():
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)
        print(f"\nprofile.json:")
        for k, v in profile.items():
            print(f"  {k}: {v}")

    # In ref_text
    ref_text_path = VOICE_DIR / "ref_text.txt"
    if ref_text_path.exists():
        with open(ref_text_path, encoding="utf-8") as f:
            ref_text = f.read().strip()
        print(f"\nref_text: {ref_text[:120]}{'...' if len(ref_text)>120 else ''}")

    return all_ok


def main():
    print("=" * 60)
    print(f"ThienVoice VI — Download voice preset: {VOICE_NAME}")
    print("=" * 60)

    # Neu da co day du file thi khong tai lai
    if VOICE_DIR.exists() and (VOICE_DIR / "voice.pt").exists():
        print(f"\nVoice preset {VOICE_NAME} da co tai:")
        print(f"  {VOICE_DIR}")
        verify_tuong_vy()
        print("\n[SKIP] Khong tai lai. Xoa thu muc assets/omnivoice-vi/ neu muon tai lai.")
        return

    os.makedirs(LOCAL_DIR, exist_ok=True)
    download_dataset()
    ok = verify_tuong_vy()

    print()
    if ok:
        print(f"[THANH CONG] Voice preset {VOICE_NAME} san sang.")
        print(f"  Chay tiep: .venv\\Scripts\\python.exe app_mvp\\test_tuong_vy_preset.py")
    else:
        print(f"[LOI] Mot so file cua {VOICE_NAME} bi thieu. Kiem tra lai.")
        sys.exit(1)


if __name__ == "__main__":
    main()

