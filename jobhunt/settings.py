import json
import os
from pathlib import Path

DEFAULTS = {"provider": "auto", "model": "", "api_keys": {}}


def settings_path():
    return Path(os.environ.get("JOBHUNT_HOME", Path.home() / ".jobhuntai")) / "settings.json"


def load():
    data = dict(DEFAULTS, api_keys={})
    try:
        loaded = json.loads(settings_path().read_text())
        data.update({k: loaded[k] for k in ("provider", "model") if k in loaded})
        data["api_keys"] = dict(loaded.get("api_keys", {}))
    except (OSError, ValueError):
        pass
    return data


def save(update):
    data = load()
    for k in ("provider", "model"):
        if k in update:
            data[k] = str(update[k])
    for name, key in (update.get("api_keys") or {}).items():
        if key:
            data["api_keys"][name] = key
        elif key == "":
            data["api_keys"].pop(name, None)
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return data


def public(data):
    """Settings safe to send to the browser (keys are never returned)."""
    return {"provider": data["provider"], "model": data["model"],
            "keys_set": sorted(data["api_keys"])}
