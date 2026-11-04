"""Portable execution configuration validation."""
import json
from pathlib import Path
import tempfile
import unittest
import os
import subprocess
import sys
from execution_config import main_model, role_models, DEFAULT_MODELS
from routing_policy import SOL, TIERS


class Configuration(unittest.TestCase):
    def test_each_role_can_be_overridden_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for role in DEFAULT_MODELS:
                for model in TIERS:
                    path.write_text(json.dumps({"execution": {role + "_model": model}}))
                    self.assertEqual(role_models(path), {**DEFAULT_MODELS, role: model})
            for model in (None, [], {}, "unknown"):
                path.write_text(json.dumps({"execution": {"review_model": model}}))
                with self.assertRaises(ValueError):
                    role_models(path)

    def test_catalog_agents_and_service_share_worker_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".config/codex-auto-router/config.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"execution":{"mechanical_model":"gpt-6.1-sol"}}')
            env = {**os.environ, "HOME": directory, "CODEX_HOME": directory + "/codex",
                   "CODEX_ROUTER_STATE_DIR": directory + "/state",
                   "JEV_PYTHON": sys.executable}
            root = Path(__file__).parent
            subprocess.run(["node", str(root / "configure-model.mjs")],
                           env=env, check=True, capture_output=True)
            agent = Path(env["CODEX_HOME"]) / "agents/router-role-mechanical.toml"
            self.assertIn("Fixed gpt-6.1-sol", agent.read_text())
            models = json.loads((Path(directory) / "state/user-models.json").read_text())
            worker = next(m for m in models["models"] if m["slug"] == "jev/role-mechanical")
            self.assertIn("gpt-6.1-sol", worker["displayName"])
            script = (
                "from execution_roles import ROLE_MODELS, prepare_role; "
                "assert ROLE_MODELS['mechanical'] == 'gpt-6.1-sol'; "
                "p={}; prepare_role(p, 'main'); s=p['instructions']; "
                "assert 'on gpt-6.1-sol. Return ambiguity' in s; "
                "prepare_role(p, 'main'); assert p['instructions'] == s"
            )
            subprocess.run([sys.executable, "-B", "-c", script],
                           cwd=root, env=env, check=True)

    def test_service_roles_load_nondefault_main_without_changing_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".config/codex-auto-router/config.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"execution":{"main_model":"gpt-6-astra"}}')
            script = (
                "from execution_roles import ROLE_MODELS; "
                "assert ROLE_MODELS['main'] == 'gpt-6-astra'; "
                "assert ROLE_MODELS['mechanical'] == 'gpt-6-luna'; "
                "assert ROLE_MODELS['execute'] == 'gpt-6.1-sol'"
            )
            subprocess.run([sys.executable, "-B", "-c", script],
                           cwd=Path(__file__).parent,
                           env={**os.environ, "HOME": directory}, check=True)

    def test_defaults_and_supported_models(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            self.assertEqual(main_model(path), SOL)
            for config, expected in [
                ({}, SOL), ({"execution": {}}, SOL),
                *[({"execution": {"main_model": model}}, model) for model in TIERS],
            ]:
                path.write_text(json.dumps(config))
                self.assertEqual(main_model(path), expected)

    def test_invalid_settings_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for config in [[], None, {"unknown": 1}, {"execution": []},
                           {"execution": {"main_model": "unknown"}},
                           {"execution": {"main_model": None}},
                           {"execution": {"typo": "sol"}}]:
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    main_model(path)
            path.write_text("{")
            with self.assertRaises(ValueError):
                main_model(path)
