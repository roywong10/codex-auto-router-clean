"""Portable execution configuration validation."""
import json
from pathlib import Path
import tempfile
import unittest
import os
import subprocess
import sys
from execution_config import main_model
from routing_policy import SOL, TIERS


class Configuration(unittest.TestCase):
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
