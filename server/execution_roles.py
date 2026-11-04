"""Fixed Codex execution roles; the shared OMP classifier remains adaptive."""
import os
from execution_config import role_models

from routing_policy import (
    ASTRA, LUNA, SOL, TERRA, POLICY_VERSION, QUESTIONS, EFFORTS, LEASES,
    _validated_choice,
)

EXECUTION_POLICY_VERSION = POLICY_VERSION + "-sol-main-roles-v2"
ROLE_MODELS = role_models()
EFFORT_QUESTIONS = {name: QUESTIONS[name] for name in ("effort", "lease")}


def effort_floor(payload, role):
    if role != "main":
        return "low"
    reasoning = payload.get("reasoning")
    requested = reasoning.get("effort") if isinstance(reasoning, dict) else None
    return {"high": "medium", "xhigh": "high", "max": "xhigh"}.get(requested, "low")


def constrain_effort(effort, floor):
    return max(effort, floor, key=EFFORTS.index) if effort in EFFORTS else floor


ROLE_INSTRUCTIONS = """
Fixed-role delegation policy:
You own the task, requirements, priorities, integration and final acceptance.
For worthwhile bounded delegation, use an offered role agent:
router_role_explore: code discovery and evidence gathering, on {explore}.
router_role_execute: bounded implementation or complex tests, on {execute}.
router_role_mechanical: established mechanical edits, formatting, factual
documentation and simple checks, on {mechanical}. Return ambiguity to the parent.
router_role_visual: image inspection and continuous browser/desktop workflows,
on {visual}. A browser session must have only one active operator.
router_role_plan: difficult architecture, material trade-offs or challenging a
high-risk proposal, on {plan}. Routine planning stays with the parent.
router_role_review: independent final review or security, permission,
concurrency, migration and compatibility review, on {review}.
Use only agent types offered by the current tool schema. If unavailable, report
that limitation; never invent an agent, swap the main model, or launch a
side-channel agent. Respect user/repository limits on delegation.
Delegate only when its benefit exceeds handoff cost. Include objective,
constraints, owned files/resources and acceptance criteria. Avoid concurrent
writes to the same file or browser. Give independent reviewers the requirements,
actual diff and validation evidence, not only your conclusions. Require workers
to return findings/work, evidence, checks and remaining risks. The parent
adjudicates findings, retains key decisions and unfinished work, and validates
the integrated result. Close finished children with the offered interrupt tool.
"""


def execution_role(payload):
    model = payload.get("model", "auto")
    if model in ("auto", "jev/auto", "jev-auto"):
        return None if os.environ.get("JEV_EXECUTION_POLICY", "roles") == "adaptive" else "main"
    role = model.removeprefix("role/") if isinstance(model, str) else ""
    if not isinstance(model, str) or not model.startswith("role/") or role not in ROLE_MODELS:
        raise ValueError("unsupported fixed execution role")
    return role


def questions_for_state(state):
    return EFFORT_QUESTIONS if state.get("execution_model") in (LUNA, TERRA, SOL, ASTRA) else QUESTIONS


def execution_decision(answers, model):
    effort, effort_probs, effort_conf = _validated_choice(answers, "effort", EFFORTS)
    lease, lease_probs, lease_conf = _validated_choice(answers, "lease", LEASES)
    confidences = [v for v in (effort_conf, lease_conf) if v is not None]
    probabilities = [p[c] for p, c in ((effort_probs, effort), (lease_probs, lease)) if p]
    return {
        "model": model, "base_model": model, "astra_policy": "normal",
        "effort": effort, "lease": lease, "speed": "default", "gate": "apply",
        "confidence": min(confidences) if confidences else None,
        "probabilities": {"model": None, "astra_policy": None,
                          "effort": effort_probs, "lease": lease_probs},
        "chosen_probability": min(probabilities) if probabilities else None,
        "policy_version": EXECUTION_POLICY_VERSION,
    }


def prepare_role(payload, role):
    if role == "main":
        instructions = payload.get("instructions") or ""
        guidance = ROLE_INSTRUCTIONS.format(**ROLE_MODELS)
        if guidance not in instructions:
            payload["instructions"] = instructions + "\n" + guidance
