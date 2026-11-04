"""User execution settings shared by the service and catalog publisher."""
import json
from pathlib import Path
from routing_policy import SOL, TIERS


def main_model(path=None):
    path = Path(path) if path is not None else Path.home() / ".config/codex-auto-router/config.json"
    if not path.exists():
        return SOL
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read execution configuration: {path}") from error
    if not isinstance(config, dict) or set(config) - {"execution"}:
        raise ValueError("Configuration must contain only an execution object")
    execution = config.get("execution", {})
    if not isinstance(execution, dict) or set(execution) - {"main_model"}:
        raise ValueError("execution supports only main_model")
    model = execution.get("main_model", SOL)
    if model not in TIERS:
        raise ValueError("Unsupported execution.main_model; choose " + ", ".join(TIERS))
    return model


if __name__ == "__main__":
    print(main_model())
