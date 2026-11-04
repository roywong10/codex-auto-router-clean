"""Go classification, credential isolation and native routing failure behavior."""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error

import jev_server as jev
import opencode_decision as go
import test_per_call_routing as routing_fixture
from routing_policy import ASTRA, LUNA, TERRA, decision_from_answers

CHOICE = {"astra_policy": "normal", "model": "luna", "effort": "low", "lease": "one_call"}


def response(choices=None):
    return {
        "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(CHOICE if choices is None else choices),
        }}],
        "usage": {"prompt_tokens": 37, "completion_tokens": 12},
    }


class Classifier(unittest.TestCase):
    def test_request_and_result_use_only_the_classification_contract(self):
        opener = mock.Mock()
        opener.open.return_value = io.BytesIO(json.dumps(response()).encode())
        with mock.patch.object(go.urllib.request, "build_opener", return_value=opener):
            result = go.call("fixture-key", {"task": "format this file"}, "session-1")
        req = opener.open.call_args.args[0]
        body = json.loads(req.data)
        self.assertEqual(req.full_url, "https://opencode.ai/inference/go/openai/v1/chat/completions")
        self.assertEqual(req.get_header("X-opencode-session"), "session-1")
        self.assertIn("jev-codex-router", req.get_header("User-agent"))
        self.assertEqual(body["model"], "deepseek-v4.1-flash")
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertNotIn("fixture-key", req.data.decode())
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 12.0)
        decision = decision_from_answers(result["answers"])
        self.assertEqual((decision["model"], decision["effort"]), (LUNA, "low"))
        self.assertIsNone(decision["confidence"])
        self.assertEqual(result["usage"], {"input_tokens": 37, "output_tokens": 12})

    def test_mandatory_frontier_policy_still_overrides_the_selected_tier(self):
        result = go.parse_response(response({**CHOICE, "model": "terra", "astra_policy": "astra"}))
        self.assertEqual(decision_from_answers(result["answers"])["model"], ASTRA)

    def test_invalid_and_incomplete_answers_are_rejected(self):
        cases = [response({**CHOICE, "model": "deepseek"}), response({"model": "luna"}),
                 response({**CHOICE, "confidence": 1}), response({**CHOICE, "effort": True}),
                 [], {}, {"choices": []}, {"choices": [None]}]
        incomplete = response()
        incomplete["choices"][0]["finish_reason"] = "length"
        cases.append(incomplete)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                go.parse_response(case)

    def test_oversized_and_non_json_responses_are_rejected(self):
        for raw in (b"x" * (go.MAX_RESPONSE_BYTES + 1), b"not json"):
            opener = mock.Mock()
            opener.open.return_value = io.BytesIO(raw)
            with mock.patch.object(go.urllib.request, "build_opener", return_value=opener), \
                 self.assertRaises(ValueError):
                go.call("fixture-key", {}, "session")

    def test_redirects_cannot_forward_the_authorization_header(self):
        request = go.urllib.request.Request(go.API, headers={"Authorization": "Bearer fixture"})
        with self.assertRaises(urllib.error.HTTPError):
            go.NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://other.invalid")

    def test_keychain_reference_is_used_without_typesafe_fallback(self):
        env = {"JEV_DECISION_PROVIDER": "opencode-go", "JEV_API_KEY": "wrong-provider",
               "OPENCODE_GO_KEYCHAIN_SERVICE": "fixture/go", "OPENCODE_GO_KEYCHAIN_ACCOUNT": "fixture"}
        completed = subprocess.CompletedProcess([], 0, "fixture-go-key\n", "")
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(go.subprocess, "run", return_value=completed) as run:
            self.assertEqual(jev.load_key(), "fixture-go-key")
            self.assertEqual(run.call_args.args[0], ["/usr/bin/security", "find-generic-password",
                             "-s", "fixture/go", "-a", "fixture", "-w"])
        with mock.patch.dict(os.environ, {"JEV_DECISION_PROVIDER": "opencode-go",
                                          "TYPESAFE_API_KEY": "wrong-provider"}, clear=True):
            self.assertEqual(jev.load_key(), "")

    def test_denied_keychain_is_an_error_without_printing_diagnostics(self):
        env = {"OPENCODE_GO_KEYCHAIN_SERVICE": "fixture/go", "OPENCODE_GO_KEYCHAIN_ACCOUNT": "fixture"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            go.subprocess, "run", return_value=subprocess.CompletedProcess([], 36, "", "private")
        ), self.assertRaisesRegex(RuntimeError, "unavailable"):
            go.load_key()

    def test_typesafe_default_retains_original_protocol(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(jev, "call_jev", return_value={}) as call:
            jev.call_jev_routed("fixture", {}, session_id="unused")
            call.assert_called_once_with("fixture", {}, None, timeout=4.0)

    def test_invalid_provider_fails_before_selecting_any_credentials(self):
        with mock.patch.dict(os.environ, {"JEV_DECISION_PROVIDER": "typo"}), \
             self.assertRaises(ValueError):
            jev.load_key()

    def test_picker_name_and_idempotence_follow_the_provider(self):
        script = Path(__file__).parent / "configure-model.mjs"
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "CODEX_ROUTER_STATE_DIR": temp, "CODEX_HOME": str(Path(temp) / "home"),
                   "JEV_DECISION_PROVIDER": "opencode-go"}
            for _ in range(2):
                subprocess.run(["node", str(script)], env=env, capture_output=True, check=True)
            models = json.loads((Path(temp) / "user-models.json").read_text())["models"]
            self.assertEqual(len(models), 7)
            self.assertEqual(models[0]["slug"], "jev/auto")
            self.assertEqual(models[0]["displayName"], "Auto (DeepSeek router)")


class NativeRouting(unittest.TestCase):
    # Reuse the existing loopback Codex edge fixture, without inheriting its tests.
    setUp = routing_fixture.PerCallEndToEnd.setUp
    tearDown = routing_fixture.PerCallEndToEnd.tearDown
    call = routing_fixture.PerCallEndToEnd.call

    def test_go_judges_but_only_codex_receives_the_execution_request(self):
        opening = [routing_fixture.message("user", "format this file")]
        with mock.patch.dict(os.environ, {"JEV_DECISION_PROVIDER": "opencode-go"}), \
             mock.patch.object(go, "call", return_value=go.parse_response(response())) as judge:
            self.call(routing_fixture.payload_for(opening))
        self.assertEqual(routing_fixture.Edge.payloads[0]["model"], LUNA)
        self.assertEqual(self.records[0]["decision_source"], "opencode-go")
        self.assertEqual(judge.call_args.args[2], self.records[0]["cache_scope"])
        self.assertEqual(self.records[0]["decision_provider"], "opencode-go")

    def test_terra_uses_native_effort_updates_and_preserves_full_context(self):
        opening = [routing_fixture.message("user", "inspect the diagram"),
                   routing_fixture.message("assistant", "I found the two buttons."),
                   routing_fixture.message("user", "Explain the next UI steps.")]
        payload = routing_fixture.payload_for(opening)
        payload["reasoning"] = {"effort": "low"}
        answer = go.parse_response(response({**CHOICE, "model": "terra", "effort": "high"}))
        with mock.patch.dict(os.environ, {"JEV_DECISION_PROVIDER": "opencode-go"}), \
             mock.patch.object(go, "call", return_value=answer):
            status, body = self.call(payload)
        forwarded = routing_fixture.Edge.payloads[-1]
        self.assertEqual((status, forwarded["model"]), (200, TERRA))
        self.assertEqual([item for item in forwarded["input"]
                          if item.get("type") != "configuration_update"], opening)
        self.assertIn({"type": "configuration_update", "reasoning": {"effort": "high"}},
                      forwarded["input"])
        self.assertEqual(self.records[-1]["effort_transport"], "configuration_update")
        self.assertEqual(self.records[-1]["decision_source"], "opencode-go")
        self.assertIn("gpt-6.1-terra", body.decode())

    def test_timeout_and_invalid_output_fall_back_to_astra_medium(self):
        opening = [routing_fixture.message("user", "format this file")]
        for error in (TimeoutError("fixture"), ValueError("bad JSON")):
            with mock.patch.dict(os.environ, {"JEV_DECISION_PROVIDER": "opencode-go"}), \
                 mock.patch.object(go, "call", side_effect=error):
                self.call(routing_fixture.payload_for(opening))
            last = self.records[-1]
            self.assertEqual((last["model"], last["effort"]), (ASTRA, "medium"))
            self.assertEqual(last["decision_source"], "technical_fallback")

    def test_locked_keychain_falls_back_without_leaking_its_error(self):
        with mock.patch.dict(os.environ, {"JEV_DECISION_PROVIDER": "opencode-go"}), \
             mock.patch.object(jev, "load_key", side_effect=RuntimeError("private detail")):
            self.call(routing_fixture.payload_for([routing_fixture.message("user", "format file")]))
        self.assertEqual(self.records[-1]["model"], ASTRA)
        self.assertEqual(self.records[-1]["gate"], "key_unavailable:RuntimeError")
        self.assertNotIn("private detail", json.dumps(self.records))


if __name__ == "__main__":
    unittest.main()
