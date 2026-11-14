"""Offline regression tests; never load or use a real credential."""
import ast
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, mock_open, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {
    "download_all_regions": "compute_ors_isochrones",
    "download_real_osm": "compute_isochrones_ors",
    "extract_hundreds_pois": "compute_ors_isochrones_batch",
    "fast_osmnx_direct": "compute_ors_isochrones_batch",
    "fast_overpass_extract": "compute_ors_isochrones",
    "fetch_all_pois": "compute_all_ors_isochrones",
    "generate_data": "fetch_ors_isochrones",
    "restore_concepcion": "main",
}
FAKE_KEY = "unit-test-only"
POIS = [{"id": 1, "name": "Test", "shop": "bakery", "lon": -73, "lat": -36}]


@contextlib.contextmanager
def load_script(name):
    dependencies = {key: MagicMock() for key in (
        "requests", "geopandas", "pandas", "osmnx", "shapely",
        "shapely.geometry", "shapely.ops",
    )}
    with patch.dict("sys.modules", dependencies):
        spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


class ORSSecurityTests(unittest.TestCase):
    def test_no_literal_credentials(self):
        for name in SCRIPTS:
            tree = ast.parse((ROOT / (name + ".py")).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "ORS_API_KEY" for t in node.targets
                ):
                    self.assertFalse(isinstance(node.value, ast.Constant), name)

    def test_import_does_not_request_credentials_or_network(self):
        with patch.dict(os.environ, {}, clear=True):
            for name in SCRIPTS:
                with self.subTest(script=name), load_script(name) as module:
                    module.requests.post.assert_not_called()

    def test_main_rejects_missing_key_before_side_effects(self):
        for value in (None, "", "   "):
            env = {} if value is None else {"ORS_API_KEY": value}
            with patch.dict(os.environ, env, clear=True):
                for name in SCRIPTS:
                    with self.subTest(script=name, value=value), load_script(name) as module:
                        with patch("builtins.open", side_effect=AssertionError("file write")), \
                             patch("os.makedirs", side_effect=AssertionError("directory write")), \
                             contextlib.redirect_stdout(io.StringIO()):
                            module.requests.post.side_effect = AssertionError("network")
                            with self.assertRaisesRegex(RuntimeError, "ORS_API_KEY"):
                                module.main()
                            module.requests.post.assert_not_called()

    def test_helpers_reject_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            for name, function in SCRIPTS.items():
                if function == "main":
                    continue
                with self.subTest(script=name), load_script(name) as module, \
                     contextlib.redirect_stdout(io.StringIO()):
                    module.requests.post.side_effect = AssertionError("network")
                    with self.assertRaisesRegex(RuntimeError, "ORS_API_KEY"):
                        getattr(module, function)(POIS)
                    module.requests.post.assert_not_called()

    def test_requests_use_environment_and_do_not_log_secret(self):
        with patch.dict(os.environ, {"ORS_API_KEY": FAKE_KEY}, clear=True):
            for name, function in SCRIPTS.items():
                with self.subTest(script=name), load_script(name) as module:
                    module.requests.post.return_value.status_code = 403
                    module.requests.post.return_value.text = FAKE_KEY
                    module.shape.return_value.__geo_interface__ = {}
                    output = io.StringIO()
                    with patch("time.sleep"), patch("builtins.open", mock_open()), \
                         patch("json.dump"), contextlib.redirect_stdout(output):
                        if function == "main":
                            module.get_concepcion_pois = lambda: POIS
                            module.main()
                        else:
                            getattr(module, function)(POIS)
                    self.assertTrue(module.requests.post.called, name)
                    headers = module.requests.post.call_args.kwargs["headers"]
                    self.assertTrue(headers["Authorization"] == FAKE_KEY, name)
                    self.assertNotIn(FAKE_KEY, output.getvalue())

    def test_exception_text_cannot_leak_key(self):
        with patch.dict(os.environ, {"ORS_API_KEY": FAKE_KEY}, clear=True):
            for name, function in SCRIPTS.items():
                if function == "main":
                    continue
                with self.subTest(script=name), load_script(name) as module:
                    module.requests.post.side_effect = RuntimeError(FAKE_KEY)
                    output = io.StringIO()
                    with patch("time.sleep"), contextlib.redirect_stdout(output):
                        getattr(module, function)(POIS)
                    self.assertNotIn(FAKE_KEY, output.getvalue())


if __name__ == "__main__":
    unittest.main()
