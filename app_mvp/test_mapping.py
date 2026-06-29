"""Test logic mapping tiếng Việt → OmniVoice instruct (không cần load model/torch).

Chạy: python app_mvp/test_mapping.py
"""

import sys
from pathlib import Path

# Thêm repo root vào path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _resolve_speed(speed):
    SPEED_MAP = {"slow": 0.85, "normal": 1.0, "fast": 1.15}
    if isinstance(speed, str):
        key = speed.lower().strip()
        if key in SPEED_MAP:
            return SPEED_MAP[key]
        return float(key)
    return float(speed)


_VI_TO_INSTRUCT = {
    "giọng nam": "male",
    "giọng nữ": "female",
    "trẻ em": "child",
    "thiếu niên": "teenager",
    "thanh niên": "young adult",
    "trung niên": "middle-aged",
    "trưởng thành": "middle-aged",
    "người già": "elderly",
    "lớn tuổi": "elderly",
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
    "thì thầm": "whisper",
    "nói thầm": "whisper",
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
}


_GENDER_KEYS = {"giọng nam": "male", "giọng nữ": "female"}

_VI_GENDER_FALLBACK = {
    " nam ": "male", " nữ ": "female",
    "nam,": "male", "nữ,": "female",
    "(nam)": "male", "(nữ)": "female",
}


def vi_to_instruct(description):
    desc = description.lower()
    gender = None
    rest = []

    for vi_key, en_val in _GENDER_KEYS.items():
        if vi_key in desc:
            gender = en_val
            desc = desc.replace(vi_key, " ", 1)
            break

    for vi_key, en_val in sorted(_VI_TO_INSTRUCT.items(), key=lambda x: -len(x[0])):
        if vi_key in _GENDER_KEYS:
            continue
        if vi_key in desc:
            if en_val not in rest and en_val != gender:
                rest.append(en_val)
            desc = desc.replace(vi_key, " ", 1)

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
    return ", ".join(matched) if matched else None


def run_tests():
    print("=" * 60)
    print("TEST SPEED MAPPING")
    print("=" * 60)
    for s, expected in [("slow", 0.85), ("normal", 1.0), ("fast", 1.15)]:
        got = _resolve_speed(s)
        status = "OK" if got == expected else f"FAIL (expected {expected})"
        print(f"  '{s}' -> {got}  [{status}]")

    print()
    print("=" * 60)
    print("TEST VOICE DESCRIPTION MAPPING")
    print("=" * 60)
    test_cases = [
        ("giọng nam, trưởng thành",                      "male, middle-aged"),
        ("giọng nữ, thanh niên",                         "female, young adult"),
        ("giọng nam Việt Nam, rõ ràng, chuyên nghiệp",   "male"),
        ("giọng nữ Việt Nam, nhẹ nhàng, tự nhiên",       "female"),
        ("giọng nữ, thì thầm, âm cao",                   "female, whisper, high pitch"),
        ("giọng nam, âm thấp",                           "male, low pitch"),
        ("giọng nữ, người già",                          "female, elderly"),
        ("giọng nam, trung niên",                        "male, middle-aged"),
        ("giọng nữ, trẻ em",                             "female, child"),
        ("giọng mỹ",                                     "american accent"),
    ]

    passed = 0
    for desc, expected in test_cases:
        got = vi_to_instruct(desc)
        ok = got == expected
        status = "OK" if ok else f"FAIL (expected '{expected}')"
        print(f"  Input : '{desc}'")
        print(f"  Output: '{got}'  [{status}]")
        print()
        if ok:
            passed += 1

    print(f"Kết quả: {passed}/{len(test_cases)} test passed")
    return passed == len(test_cases)


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
