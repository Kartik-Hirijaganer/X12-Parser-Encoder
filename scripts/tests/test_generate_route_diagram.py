from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_route_diagram import generate_diagram  # noqa: E402


class GenerateRouteDiagramTests(unittest.TestCase):
    def test_openapi_routes_are_grouped_without_router_internals(self) -> None:
        fake_app = types.SimpleNamespace(
            openapi=lambda: {
                "paths": {
                    "/api/v1/health": {
                        "get": {
                            "tags": ["health"],
                            "description": "Run the deep health check.\n\nMore detail.",
                        }
                    },
                    "/healthz": {"get": {"summary": "Healthcheck"}},
                }
            }
        )
        app_package = types.ModuleType("app")
        app_main = types.ModuleType("app.main")
        app_main.app = fake_app

        with patch.dict(sys.modules, {"app": app_package, "app.main": app_main}):
            diagram = generate_diagram(Path.cwd())

        self.assertIn('subgraph group_health["health"]', diagram)
        self.assertIn(
            'route_GET__api_v1_health["GET /api/v1/health<br/>Run the deep health check."]',
            diagram,
        )
        self.assertIn('route_GET__healthz["GET /healthz<br/>Healthcheck"]', diagram)


if __name__ == "__main__":
    unittest.main()
