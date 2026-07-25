"""Provider-to-vault lookup aliases (Signal-compatible)."""

PROVIDER_VAULT_NAMES: dict[str, list[str]] = {
    "anthropic": ["anthropic", "claude"],
    "openai_gpts": ["openai", "openai gpts", "gpt", "openai api key"],
    "gemini_gems": ["gemini", "google ai", "gemini gems"],
    "deepseek": ["deepseek"],
    "groq": ["groq", "groq_api_key", "groq api key"],
    "openrouter": ["openrouter", "open_router", "open router", "openrouter_api_key", "openrouter api key"],
    "generic_api": ["api key", "generic api"],
    "nvidia_nim": ["nvidia_nim", "nvidia nim", "nvidia-nim", "nvidia nim api"],
    "cursor_cli": ["cursor", "cursor api", "cursor_api_key", "cursor api key", "cursor cli"],
    "codex_cli": ["codex", "codex api", "codex_api_key", "codex api key", "codex cli"],
}

PROVIDER_VAULT_URLS: dict[str, list[str]] = {
    "anthropic": ["anthropic.com"],
    "openai_gpts": ["openai.com", "api.openai.com"],
    "gemini_gems": ["generativelanguage.googleapis.com", "aistudio.google.com"],
    "deepseek": ["deepseek.com"],
    "groq": ["groq.com", "api.groq.com", "console.groq.com"],
    "openrouter": ["openrouter.ai"],
    "nvidia_nim": ["build.nvidia.com", "integrate.api.nvidia.com"],
    "cursor_cli": ["cursor.com", "cursor.sh"],
    "codex_cli": ["openai.com", "api.openai.com"],
}

RUNTIME_PROVIDER_IDS: dict[str, str] = {
    "cursor_local": "cursor_cli",
    "cursor_cloud": "cursor_cli",
    "codex_local": "codex_cli",
    "codex_cloud": "codex_cli",
}
