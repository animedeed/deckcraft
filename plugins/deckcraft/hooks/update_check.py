"""Проверка обновления deckcraft при старте сессии (хук SessionStart).

Раз в сутки сверяет установленную версию с plugin.json в GitHub. Если вышла новая — показывает пользователю
строку «доступна deckcraft X» и просит Claude один раз спросить: обновить сейчас / напомнить позже / пропустить.
Сеть недоступна, проверка отключена или плагин запущен из рабочей папки (разработка) — молчит.

    python3 update_check.py               # сам хук
    python3 update_check.py --snooze 7    # «позже»: не напоминать 7 дней
    python3 update_check.py --skip        # «пропустить»: не напоминать про эту версию
Отключить: переменная окружения DECKCRAFT_NO_UPDATE_CHECK=1.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO_RAW = os.environ.get("DECKCRAFT_UPDATE_URL", "https://raw.githubusercontent.com/animedeed/deckcraft/main")
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("CLAUDE_PLUGIN_DATA") or Path.home() / ".cache" / "deckcraft")
STATE = DATA / "update_state.json"
DAY = 86400


def _ver(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3])


def _get(url: str, timeout: float = 3.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 — фиксированный адрес репозитория
        return r.read().decode("utf-8")


def _load() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def _save(st: dict) -> None:
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(st))
    except OSError:
        pass


def _changes(changelog: str, installed: tuple, limit: int = 8) -> list[str]:
    """Пункты CHANGELOG для версий новее установленной."""
    out, take = [], False
    for line in changelog.splitlines():
        m = re.match(r"##\s+(\d+\.\d+\.\d+)", line)
        if m:
            take = _ver(m.group(1)) > installed
            continue
        if take and line.startswith("- "):
            out.append(line[2:].strip())
    return out[:limit]


def main() -> None:
    if os.environ.get("DECKCRAFT_NO_UPDATE_CHECK") == "1":
        return
    if "--snooze" in sys.argv or "--skip" in sys.argv:
        st = _load()
        if "--skip" in sys.argv:
            st["skip_version"] = st.get("latest", "")
        else:
            days = float(sys.argv[sys.argv.index("--snooze") + 1]) if len(sys.argv) > sys.argv.index("--snooze") + 1 else 7
            st["snooze_until"] = time.time() + days * DAY
        _save(st)
        print("deckcraft: напоминание отложено" if "--snooze" in sys.argv else "deckcraft: эта версия пропущена")
        return
    # установка из рабочей папки (маркетплейс-каталог на диске) — режим разработки, обновления не предлагаем
    if ".claude/plugins/cache" not in ROOT.as_posix() and not os.environ.get("DECKCRAFT_UPDATE_FORCE"):
        return
    try:
        installed = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return
    st = _load()
    now = time.time()
    if now - st.get("checked", 0) > DAY or os.environ.get("DECKCRAFT_UPDATE_FORCE"):
        try:
            st["latest"] = json.loads(_get(f"{REPO_RAW}/plugins/deckcraft/.claude-plugin/plugin.json"))["version"]
            st["changes"] = _changes(_get(f"{REPO_RAW}/CHANGELOG.md"), _ver(installed))
        except Exception:  # noqa: BLE001 — нет сети или GitHub недоступен: молчим, проверим в следующий раз
            st["checked"] = now - DAY + 3600  # повтор через час
            _save(st)
            return
        st["checked"] = now
        _save(st)
    latest = st.get("latest", "")
    if not latest or _ver(latest) <= _ver(installed):
        return
    if st.get("skip_version") == latest or now < st.get("snooze_until", 0):
        return
    news = st.get("changes") or []
    me = Path(__file__).resolve()
    msg = f"deckcraft {latest} доступна (у вас {installed})."
    ctx = (f"Вышло обновление плагина deckcraft: {latest} (установлена {installed}). Что нового: "
           + ("; ".join(news) if news else "см. CHANGELOG в github.com/animedeed/deckcraft") + ". "
           "Один раз в этой сессии, до основной работы, спроси пользователя через AskUserQuestion: "
           "«Обновить сейчас» / «Напомнить позже» / «Пропустить эту версию», коротко перечислив новое. "
           "Сейчас → выполни `claude plugin update deckcraft@deckcraft` и попроси пользователя ввести /reload-plugins. "
           f"Позже → `python3 \"{me}\" --snooze 7`. Пропустить → `python3 \"{me}\" --skip`. "
           "Если пользователь занят другим — не перебивай, спроси в конце ответа.")
    print(json.dumps({"systemMessage": msg,
                      "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
