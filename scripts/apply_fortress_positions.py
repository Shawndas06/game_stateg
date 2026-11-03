"""Применяет ручные координаты из fortress_positions.json к fortresses.py.

Не трогает lon/lat — добавляет/обновляет словарь MANUAL_FORTRESS_POSITIONS,
из которого Fortress.__post_init__ возьмёт абсолютные x,y вместо проекции.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "scripts" / "fortress_positions.json"
DATA_PATH = ROOT / "src" / "data" / "fortresses.py"

SCALE = 8400 / 1440  # PNG-px → логические

START = "# === MANUAL_FORTRESS_POSITIONS START ==="
END = "# === MANUAL_FORTRESS_POSITIONS END ==="


def main() -> None:
    if not JSON_PATH.exists():
        print(f"Нет файла {JSON_PATH} — сначала запусти scripts/calibrate_fortresses.py")
        return
    raw = json.loads(JSON_PATH.read_text())
    if not raw:
        print("Файл позиций пуст")
        return

    lines = [START, "MANUAL_FORTRESS_POSITIONS: dict[str, tuple[int, int]] = {"]
    for fid, (px, py) in sorted(raw.items()):
        lx = int(round(px * SCALE))
        ly = int(round(py * SCALE))
        lines.append(f"    {fid!r:24s}: ({lx:5d}, {ly:5d}),")
    lines.append("}")
    lines.append(END)
    block = "\n".join(lines)

    src = DATA_PATH.read_text()
    if START in src and END in src:
        src = re.sub(
            re.escape(START) + r"[\s\S]*?" + re.escape(END),
            block,
            src,
        )
    else:
        # вставить перед FORTRESS_MAP_OFFSETS
        src = src.replace(
            "FORTRESS_MAP_OFFSETS",
            block + "\n\n\nFORTRESS_MAP_OFFSETS",
            1,
        )
    DATA_PATH.write_text(src)
    print(f"Записано {len(raw)} ручных позиций в {DATA_PATH}")


if __name__ == "__main__":
    main()
