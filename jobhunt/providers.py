"""AI providers. Local ones (Ollama, LM Studio, llama.cpp) are auto-detected; online ones need a key."""
import json
import urllib.request

TIMEOUT = 300


def _request(url, payload=None, headers=None, timeout=TIMEOUT):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


class Provider:
    name = ""
    label = ""
    local = False
    default_model = ""

    def __init__(self, model="", api_key="", base_url=None):
        self.model = model or self.default_model
        self.api_key = api_key
        if base_url:
            self.base_url = base_url

    def complete(self, system, prompt):
        raise NotImplementedError


class Ollama(Provider):
    name, label, local = "ollama", "Ollama (local)", True
    base_url = "http://localhost:11434"

    def models(self):
        return [m["name"] for m in _request(self.base_url + "/api/tags", timeout=2).get("models", [])]

    def complete(self, system, prompt):
        r = _request(self.base_url + "/api/chat", {
            "model": self.model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        return r["message"]["content"]


class OpenAICompatible(Provider):
    """Any server speaking the OpenAI chat-completions protocol."""
    base_url = ""

    def _headers(self):
        return {"Authorization": "Bearer " + self.api_key} if self.api_key else {}

    def models(self):
        r = _request(self.base_url + "/models", headers=self._headers(), timeout=2)
        return [m["id"] for m in r.get("data", [])]

    def complete(self, system, prompt):
        r = _request(self.base_url + "/chat/completions", {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
            self._headers())
        return r["choices"][0]["message"]["content"]


class LMStudio(OpenAICompatible):
    name, label, local = "lmstudio", "LM Studio (local)", True
    base_url = "http://localhost:1234/v1"


class LlamaCpp(OpenAICompatible):
    name, label, local = "llamacpp", "llama.cpp server (local)", True
    base_url = "http://localhost:8080/v1"


class OpenAI(OpenAICompatible):
    name, label = "openai", "OpenAI"
    base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"


class Grok(OpenAICompatible):
    name, label = "grok", "Grok (xAI)"
    base_url = "https://api.x.ai/v1"
    default_model = "grok-3-mini"


class Gemini(OpenAICompatible):
    name, label = "gemini", "Gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
    default_model = "gemini-2.0-flash"


class Copilot(OpenAICompatible):
    """GitHub Models (uses a GitHub token), the API route to Copilot-family models."""
    name, label = "copilot", "GitHub Copilot / GitHub Models"
    base_url = "https://models.github.ai/inference"
    default_model = "openai/gpt-4o-mini"


class Claude(Provider):
    name, label = "claude", "Claude (Anthropic)"
    base_url = "https://api.anthropic.com/v1"
    default_model = "claude-3-5-haiku-latest"

    def complete(self, system, prompt):
        r = _request(self.base_url + "/messages", {
            "model": self.model, "max_tokens": 4096, "system": system,
            "messages": [{"role": "user", "content": prompt}]},
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in r["content"])


LOCAL = [Ollama, LMStudio, LlamaCpp]
ONLINE = [OpenAI, Claude, Gemini, Grok, Copilot]
REGISTRY = {c.name: c for c in LOCAL + ONLINE}


def detect_local():
    """Return [{name,label,models}] for local servers that are currently running."""
    found = []
    for cls in LOCAL:
        try:
            found.append({"name": cls.name, "label": cls.label, "models": cls().models()})
        except Exception:
            continue
    return found


def get_provider(settings):
    """Build the provider chosen in settings; 'auto' picks the first running local one."""
    name, model = settings.get("provider", "auto"), settings.get("model", "")
    if name == "auto":
        local = detect_local()
        if not local:
            raise RuntimeError("No local AI detected. Start Ollama/LM Studio or choose an online provider in Settings.")
        name = local[0]["name"]
        model = model or (local[0]["models"][0] if local[0]["models"] else "")
    cls = REGISTRY.get(name)
    if not cls:
        raise RuntimeError("Unknown provider: %s" % name)
    key = settings.get("api_keys", {}).get(name, "")
    if not cls.local and not key:
        raise RuntimeError("No API key set for %s. Add it in Settings." % cls.label)
    return cls(model=model, api_key=key)
