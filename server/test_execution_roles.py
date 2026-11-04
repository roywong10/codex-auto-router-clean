"""Fixed execution identity, adaptive effort and bounded role publication."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import execution_roles as roles
import jev_server as jev
import opencode_decision as go
import test_per_call_routing as fixture


def effort_answer(effort="high"):
    return {"answers": {"effort": {"choice": effort}, "lease": {"choice": "one_call"}}}


class Contract(unittest.TestCase):
    def test_effort_floor_matrix_and_role_isolation(self):
        for requested, floor in [
            (None, "low"), ("low", "low"), ("medium", "low"),
            ("high", "medium"), ("xhigh", "high"), ("max", "xhigh"),
            ("unknown", "low"),
        ]:
            payload = {"reasoning": {"effort": requested}}
            self.assertEqual(roles.effort_floor(payload, "main"), floor)
            for effort in jev.EFFORTS:
                self.assertEqual(
                    roles.constrain_effort(effort, floor),
                    jev.EFFORTS[max(jev.EFFORTS.index(effort), jev.EFFORTS.index(floor))],
                )
            for role in roles.ROLE_MODELS.keys() - {"main"}:
                self.assertEqual(roles.effort_floor(payload, role), "low")

    def test_main_classifier_only_selects_effort_and_lease_for_fixed_sol(self):
        state = {"execution_model": jev.SOL, "execution_role": "main", "task": "final review"}
        body = go.request_body(state)
        self.assertIn("exactly effort, lease", body["messages"][0]["content"])
        self.assertNotIn('"astra_policy"', body["messages"][0]["content"])
        response = {"choices": [{"finish_reason": "stop", "message": {
            "content": '{"effort":"high","lease":"one_call"}'}}]}
        result = go.parse_response(response, state)
        self.assertEqual(roles.execution_decision(result["answers"], jev.SOL)["model"], jev.SOL)
        response["choices"][0]["message"]["content"] = '{"effort":"high","lease":"one_call","model":"astra"}'
        with self.assertRaises(ValueError):
            go.parse_response(response, state)

    def test_omp_without_execution_role_keeps_existing_four_questions(self):
        self.assertIs(roles.questions_for_state({"task": "review"}), jev.QUESTIONS)

    def test_publication_is_idempotent_private_and_preserves_other_models_and_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, home = root / "state", root / "home"
            state.mkdir()
            (home / "agents").mkdir(parents=True)
            own_agent = home / "agents" / "user.toml"
            own_agent.write_text('name = "user"\n')
            overlay = state / "user-models.json"
            overlay.write_text(json.dumps({"version": 1, "models": [{"slug": "other/model"}]}))
            env = {**os.environ, "CODEX_ROUTER_STATE_DIR": str(state), "CODEX_HOME": str(home)}
            script = Path(__file__).parent / "configure-model.mjs"
            for _ in range(2):
                subprocess.run(["node", str(script)], env=env, check=True, capture_output=True)
            entries = json.loads(overlay.read_text())["models"]
            self.assertEqual(len(entries), 8)
            self.assertEqual(entries[0], {"slug": "other/model"})
            self.assertEqual(own_agent.read_text(), 'name = "user"\n')
            for role in roles.ROLE_MODELS.keys() - {"main"}:
                entry = next(m for m in entries if m["slug"] == f"jev/role-{role}")
                self.assertEqual(entry["upstreamModel"], f"role/{role}")
                agent = home / "agents" / f"router-role-{role}.toml"
                self.assertIn(f'model = "jev/role-{role}"', agent.read_text())
                self.assertEqual(agent.stat().st_mode & 0o777, 0o600)


class Execution(unittest.TestCase):
    setUp = fixture.PerCallEndToEnd.setUp
    tearDown = fixture.PerCallEndToEnd.tearDown
    call = fixture.PerCallEndToEnd.call

    def call_fixed(self, role="main", **overrides):
        model = "auto" if role == "main" else f"role/{role}"
        with mock.patch.dict(os.environ, {"JEV_EXECUTION_POLICY": "roles"}):
            return self.call(fixture.payload_for(
                [fixture.message("user", "Inspect the task and review the risks.")],
                model=model, **overrides,
            ))

    def test_main_keeps_sol_even_if_a_legacy_answer_names_astra(self):
        with mock.patch.object(jev, "call_jev_routed",
                               return_value=fixture.answer(jev.ASTRA, "xhigh", astra_required=True)) as judge:
            status, _ = self.call_fixed()
        self.assertEqual(status, 200)
        self.assertEqual(fixture.Edge.payloads[-1]["model"], jev.SOL)
        self.assertEqual(judge.call_args.args[1]["execution_model"], jev.SOL)
        self.assertIn("router_role_review", fixture.Edge.payloads[-1]["instructions"])
        self.assertEqual(self.records[-1]["execution_role"], "main")
        self.assertEqual(fixture.Edge.headers_seen[-1].get("x-codex-router-exact-route"), "1")

    def test_main_floor_applies_to_forwarded_effort_but_not_workers(self):
        for role in roles.ROLE_MODELS:
            with self.subTest(role=role), mock.patch.object(
                jev, "call_jev_routed", return_value=effort_answer("low")
            ):
                self.call_fixed(role, reasoning={"effort": "max"})
                expected = "xhigh" if role == "main" else "low"
                self.assertEqual(self.records[-1]["effort"], expected)
                forwarded = fixture.Edge.payloads[-1]
                updates = [item["reasoning"]["effort"] for item in forwarded["input"]
                           if item.get("type") == "configuration_update"]
                self.assertEqual(updates[-1] if updates else forwarded["reasoning"]["effort"],
                                 expected)

    def test_main_floor_applies_on_classifier_failure(self):
        with mock.patch.object(jev, "call_jev_routed", side_effect=TimeoutError()):
            self.call_fixed(reasoning={"effort": "max"})
        self.assertEqual(self.records[-1]["effort"], "xhigh")
        self.assertEqual(self.records[-1]["decision_source"], "technical_fallback")

    def test_main_floor_applies_to_low_leased_decision(self):
        leased = roles.execution_decision(effort_answer("low")["answers"], jev.SOL)
        with mock.patch.object(jev, "route_lease", return_value=leased), \
             mock.patch.object(jev, "call_jev_routed") as judge:
            self.call_fixed(reasoning={"effort": "high"})
        judge.assert_not_called()
        self.assertEqual(self.records[-1]["effort"], "medium")
        self.assertTrue(self.records[-1]["lease_hit"])

    def test_empty_completion_recovery_respects_main_floor(self):
        attempts = []

        def forward(handler, payload, path, stream, debug, marker, model,
                    signature, effort, **kwargs):
            attempts.append(effort)
            handler._attempts.append({"model": payload["model"],
                                     "completion": "empty_completion"})
            return 502, "json", "application/json", False, b'{"error":"empty"}', None

        with mock.patch.object(jev, "call_jev_routed", return_value=effort_answer("max")), \
             mock.patch.object(jev.Handler, "_forward", new=forward):
            with self.assertRaisesRegex(Exception, "502"):
                self.call_fixed(reasoning={"effort": "max"})
        self.assertEqual(attempts, ["max", "xhigh"])

    def test_each_role_has_a_fixed_model_with_independent_auto_effort(self):
        for role, model in roles.ROLE_MODELS.items():
            with self.subTest(role=role), mock.patch.object(
                jev, "call_jev_routed", return_value=effort_answer("max")
            ):
                self.call_fixed(role)
                self.assertEqual(fixture.Edge.payloads[-1]["model"], model)
                self.assertEqual(self.records[-1]["effort"], "max")
                self.assertEqual(self.records[-1]["execution_role"], role)
        self.assertEqual(len({r["cache_scope"] for r in self.records}), len(roles.ROLE_MODELS))

    def test_classifier_failure_keeps_the_roles_model(self):
        for role, model in roles.ROLE_MODELS.items():
            with self.subTest(role=role), mock.patch.object(
                jev, "call_jev_routed", side_effect=TimeoutError("private")
            ):
                self.call_fixed(role)
                self.assertEqual((self.records[-1]["model"], self.records[-1]["effort"]),
                                 (model, "medium"))
                self.assertEqual(self.records[-1]["decision_source"], "technical_fallback")

    def test_effort_changes_without_model_changes_on_tool_continuations(self):
        opening = [fixture.message("user", "Implement the change")]
        continuation = opening + [fixture.tool_call("c"), fixture.tool_step("c", "error: failed")]
        with mock.patch.dict(os.environ, {"JEV_EXECUTION_POLICY": "roles"}), mock.patch.object(
            jev, "call_jev_routed", side_effect=[effort_answer("low"), effort_answer("high")]
        ):
            self.call(fixture.payload_for(opening))
            self.call(fixture.payload_for(continuation))
        self.assertEqual([p["model"] for p in fixture.Edge.payloads], [jev.SOL, jev.SOL])
        self.assertEqual([r["effort"] for r in self.records], ["low", "high"])
        self.assertEqual(fixture.Edge.payloads[-1]["input"], continuation)

    def test_empty_completion_recovery_stays_on_same_model(self):
        attempts = []

        def forward(handler, payload, *args, **kwargs):
            attempts.append(payload["model"])
            handler._attempts.append({"model": payload["model"],
                                     "completion": "empty_completion"})
            return 502, "json", "application/json", False, b'{"error":"empty"}', None

        with mock.patch.object(jev, "call_jev_routed", return_value=effort_answer("high")), \
             mock.patch.object(jev.Handler, "_forward", new=forward):
            with self.assertRaisesRegex(Exception, "502"):
                self.call_fixed()
        self.assertEqual(attempts, [jev.SOL, jev.SOL])

    def test_exhausted_quota_does_not_swap_to_external_model(self):
        with mock.patch.object(jev, "native_dry", return_value="manual"), \
             mock.patch.object(jev, "fallback_candidates") as fallback, \
             mock.patch.object(jev, "call_jev_routed", return_value=effort_answer()):
            with self.assertRaisesRegex(Exception, "503"):
                self.call_fixed()
        fallback.assert_not_called()
        self.assertEqual(fixture.Edge.payloads, [])


if __name__ == "__main__":
    unittest.main()
