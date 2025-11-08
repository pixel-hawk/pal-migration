from __future__ import annotations
import json
import os
from typing import Dict, Any

_LANG: str = "zh_CN"
_RES: Dict[str, Dict[str, str]] = {"en_US": {}, "zh_CN": {}}
_BASE: str = os.path.dirname(__file__)
_CFG: str = os.path.join(_BASE, "config.json")


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_resources(lang: str | None = None) -> None:
    global _RES, _LANG
    _RES["en_US"] = _load_json(os.path.join(_BASE, "en_US.json"))
    _RES["zh_CN"] = _load_json(os.path.join(_BASE, "zh_CN.json"))
    if lang:
        _LANG = lang


def get_language() -> str:
    return _LANG


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang
    try:
        with open(_CFG, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_language(default_lang: str = "zh_CN") -> None:
    lang = default_lang
    if os.path.exists(_CFG):
        cfg = _load_json(_CFG)
        lang = cfg.get("lang", default_lang)
    load_resources(lang)
    set_language(lang)


_DEF = object()


def t(key: str, default: str | object = _DEF, **fmt) -> str:
    # Try current -> en -> fallback
    src = _RES.get(_LANG, {})
    en = _RES.get("en_US", {})
    text = src.get(key)
    if text is None:
        text = en.get(key)
    if text is None:
        text = key if default is _DEF else default
    try:
        return text.format(**fmt) if fmt else text
    except Exception:
        return text




