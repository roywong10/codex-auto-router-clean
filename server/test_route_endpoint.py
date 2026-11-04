"""Consumer-visible boundaries of classification-only routing."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

import jev_server
from routing_policy import route_choice, LUNA, ASTRA


class RouteEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = jev_server.ThreadingHTTPServer(("127.0.0.1", 0), jev_server.Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.enterContext(mock.patch.object(jev_server, "local_secret", return_value="test-local"))
        self.enterContext(mock.patch.object(jev_server, "load_key", return_value="test-upstream"))
        self.relay = self.enterContext(mock.patch.object(
            jev_server.Handler, "_forward", side_effect=AssertionError("execution forbidden")))

    def post(self, body, secret="test-local", origin=None):
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + secret}
        if origin:
            headers["Origin"] = origin
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.server.server_port}/v1/route",
            data=json.dumps(body).encode(), headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            with error:
                return error.code, json.loads(error.read())

    def test_mandatory_review_overrides_cheaper_choice_without_execution(self):
        answers = {key: {"choice": value} for key, value in
                   route_choice(LUNA, "high", astra_required=True).items()}
        with mock.patch.object(jev_server, "call_jev_routed", return_value={"answers": answers}) as judge:
            status, result = self.post({"prompt": "Review authentication risks", "session_id": "private-thread"})
        self.assertEqual(status, 200)
        self.assertEqual(result["decision"]["model"], ASTRA)
        self.assertEqual(result["decision"]["effort"], "high")
        self.assertIsNone(result["decision"]["confidence"])
        self.assertNotEqual(judge.call_args.kwargs["session_id"], "private-thread")
        self.relay.assert_not_called()

    def test_classifier_failure_does_not_become_successful_fallback(self):
        with mock.patch.object(jev_server, "call_jev_routed", side_effect=TimeoutError):
            status, result = self.post({"prompt": "Fix it", "session_id": "s"})
        self.assertEqual(status, 502)
        self.assertNotIn("decision", result)

    def test_rejects_credentials_browser_origins_and_invalid_inputs_before_judging(self):
        with mock.patch.object(jev_server, "call_jev_routed") as judge:
            valid = {"prompt": "Fix it", "session_id": "s"}
            self.assertEqual(self.post(valid, secret="wrong")[0], 401)
            self.assertEqual(self.post(valid, origin="https://example.com")[0], 403)
            for body in (dict(valid, prompt=""), dict(valid, prompt="x" * 12001),
                         dict(valid, has_image="yes"), dict(valid, tools=[]),
                         dict(valid, previous_user="x" * 6001)):
                with self.subTest(body_keys=list(body)):
                    self.assertEqual(self.post(body)[0], 400)
            judge.assert_not_called()

    def test_image_and_followup_context_survive_bounded_projection(self):
        answers = {key: {"choice": value} for key, value in route_choice(LUNA, "low").items()}
        with mock.patch.object(jev_server, "call_jev_routed", return_value={"answers": answers}) as judge:
            status, _ = self.post({"prompt": "可以，继续", "session_id": "s", "has_image": True,
                                   "previous_user": "Investigate export failure",
                                   "previous_assistant": "I propose tracing the renderer"})
        self.assertEqual(status, 200)
        state = judge.call_args.args[1]
        self.assertTrue(state["image"])
        self.assertIn("Investigate export failure", str(state))
        self.assertIn("tracing the renderer", str(state))


if __name__ == "__main__":
    unittest.main()
