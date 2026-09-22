"""Generate the repository marketplace without machine-specific executable paths."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
path = root / ".agents" / "plugins" / "marketplace.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({
    "name": "laya-source",
    "interface": {"displayName": "Laya for Codex (source development)"},
    "plugins": [{"name": "laya-for-codex",
                 "source": {"source": "local", "path": "./integrations/codex/plugins/laya-for-codex"},
                 "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                 "category": "Productivity"}]
}, indent=2) + "\n", encoding="utf-8")
