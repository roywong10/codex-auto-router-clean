"""User execution settings shared by the service and catalog publisher."""
import json
from pathlib import Path
from routing_policy import SOL, TIERS, LUNA, TERRA, ASTRA

DEFAULT_MODELS = {
    "main": SOL, "explore": SOL, "execute": SOL, "mechanical": LUNA,
    "visual": TERRA, "plan": ASTRA, "review": ASTRA,
}


def role_models(path=None):
    path = Path(path) if path is not None else Path.home() / ".config/codex-auto-router/config.json"
    if not path.exists():
        return dict(DEFAULT_MODELS)
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read execution configuration: {path}") from error
    if not isinstance(config, dict) or set(config) - {"execution"}:
        raise ValueError("Configuration must contain only an execution object")
    execution = config.get("execution", {})
    fields = {role + "_model" for role in DEFAULT_MODELS}
    if not isinstance(execution, dict) or set(execution) - fields:
        raise ValueError("Unknown execution setting; supported fields: " + ", ".join(sorted(fields)))
    models = dict(DEFAULT_MODELS)
    for role in models:
        model = execution.get(role + "_model", models[role])
        if not isinstance(model, str) or model not in TIERS:
            raise ValueError(f"Unsupported execution.{role}_model; choose " + ", ".join(TIERS))
        models[role] = model
    return models


def main_model(path=None):
    return role_models(path)["main"]


if __name__ == "__main__":
    print(json.dumps(role_models()))
