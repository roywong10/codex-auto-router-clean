"""Bounded classification-only access to the shared routing judge."""
import hashlib
import time

from routing_policy import POLICY_VERSION, decision_from_answers

MAX_BYTES = 96 * 1024
FIELDS = {"prompt", "previous_user", "previous_assistant", "has_image", "session_id"}


def validate(body):
    if not isinstance(body, dict) or set(body) - FIELDS:
        raise ValueError("unsupported route request fields")
    for name, limit, required in (
        ("prompt", 12000, True), ("session_id", 128, True),
        ("previous_user", 6000, False), ("previous_assistant", 4000, False),
    ):
        value = body.get(name, "")
        if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
            raise ValueError(f"invalid {name}")
    if "has_image" in body and not isinstance(body["has_image"], bool):
        raise ValueError("invalid has_image")
    return body


def classify(body, *, load_key, call_judge, source, make_dossier):
    """Return a decision only: never relay execution, acquire leases or fall back."""
    body = validate(body)
    items = []
    if body.get("previous_user"):
        items.append({"role": "user", "content": body["previous_user"]})
    if body.get("previous_assistant"):
        items.append({"role": "assistant", "content": body["previous_assistant"]})
    items.append({"role": "user", "content": body["prompt"]})
    state = make_dossier({"input": items})
    if body.get("has_image"):
        state["image"] = True
    # Namespace routing-only consumers separately from native Codex execution.
    scope = "omp-" + hashlib.sha256(body["session_id"].encode()).hexdigest()[:32]
    key = load_key()
    if not key:
        raise RuntimeError("routing judge credentials unavailable")
    started = time.monotonic()
    result = call_judge(key, state, session_id=scope)
    decision = decision_from_answers(result.get("answers"))
    return {
        "decision": decision,
        "classifier": result.get("model"),
        "source": source(),
        "ms": int((time.monotonic() - started) * 1000),
        "policy_version": POLICY_VERSION,
        "usage": result.get("usage") or {},
    }
