"""Small end-to-end check through the parent router; never print credentials."""
import http.client
import hashlib
import json
import secrets
from pathlib import Path

from healthcheck import healthy
from opencode_decision import decision_provider, decision_source
from local_runtime import STATE
from routing_policy import EFFORTS, POLICY_VERSION, TIERS
from execution_roles import EXECUTION_POLICY_VERSION, ROLE_MODELS, execution_role


def main():
    if not healthy():
        raise RuntimeError("local health check failed")
    health = http.client.HTTPConnection("127.0.0.1", 4319, timeout=5)
    try:
        health.request("GET", "/health")
        running = json.loads(health.getresponse().read())
        if running.get("policy_version") != POLICY_VERSION:
            raise RuntimeError("running policy differs from checkout; reload required")
        if running.get("decision_provider", "typesafe") != decision_provider():
            raise RuntimeError("running classifier differs from configuration; reload required")
        if execution_role({"model": "auto"}) and running.get("execution_policy") != EXECUTION_POLICY_VERSION:
            raise RuntimeError("running execution policy differs from checkout; reload required")
    finally:
        health.close()
    secret = (Path(STATE) / "caller-secret").read_text().strip()
    connection = http.client.HTTPConnection("127.0.0.1", 4202, timeout=120)
    result = {"policy": POLICY_VERSION, "model": None, "status": None}
    output_text = []
    response_model = None
    smoke_key = "jev-smoke-" + secrets.token_hex(16)
    smoke_scope = hashlib.sha256(("prompt:" + smoke_key).encode()).hexdigest()[:16]
    if execution_role({"model": "auto"}):
        smoke_scope = hashlib.sha256((smoke_scope + ":main").encode()).hexdigest()[:16]
    try:
        body = {"model": "jev/auto", "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "Reply only OK."}]}
        ], "prompt_cache_key": smoke_key, "stream": True}
        connection.request("POST", f"/_codex-router/{secret}/v1/responses",
                           json.dumps(body), {"Content-Type": "application/json"})
        response = connection.getresponse()
        result["http"] = response.status
        if response.status != 200:
            raise RuntimeError(f"parent router returned HTTP {response.status}")
        for line in response:
            if not line.startswith(b"data: "):
                continue
            try:
                event = json.loads(line[6:])
            except ValueError:
                continue
            if event.get("type") == "response.created":
                response_model = (event.get("response") or {}).get("model")
            if event.get("type") == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str):
                    output_text.append(delta)
            if event.get("type") == "response.completed":
                result["status"] = (event.get("response") or {}).get("status")
        if result["status"] != "completed":
            raise RuntimeError("no successful terminal response")
        route = None
        with (Path(STATE) / "jev-router-live.jsonl").open(encoding="utf-8") as log:
            for line in log:
                entry = json.loads(line)
                if isinstance(entry, dict) and entry.get("cache_scope") == smoke_scope:
                    route = entry
        if (
            not isinstance(route, dict)
            or route.get("decision_source") != decision_source()
            or route.get("gate") not in ("apply", "astra_policy")
            or route.get("status") != 200
            or route.get("completion_status") != "response.completed"
        ):
            raise RuntimeError("the request completed without a verified classifier decision; check the key and route")
        if route.get("model") not in TIERS or route.get("effort") not in EFFORTS:
            raise RuntimeError("the classifier decision did not report a supported model and effort")
        if execution_role({"model": "auto"}) and route.get("model") != ROLE_MODELS["main"]:
            raise RuntimeError("main execution did not remain on Sol")
        if response_model != route["model"]:
            raise RuntimeError("the upstream response model did not match the selected route")
        expected_label = f"{route['model']} · reasoning: {route['effort']}"
        if expected_label not in "".join(output_text)[:240]:
            raise RuntimeError("the streamed assistant text did not show its routed model and effort")
        result.update({key: route.get(key) for key in (
            "model", "effort", "effort_transport", "gate", "decision_source", "decision_provider"
        )})
        result["response_model"] = response_model
        result["visible_model_effort"] = "confirmed"
        print(json.dumps(result))
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Transport exceptions can carry request URLs: expose only their class.
        print(json.dumps({"ok": False, "error_type": type(error).__name__}))
        raise SystemExit(1)
