from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeepSeekGatewayBoundaryTests(unittest.TestCase):
    def test_production_deepseek_network_access_exists_only_in_gateway(self):
        violations = []
        for path in ROOT.rglob("*.py"):
            relative = path.relative_to(ROOT)
            if relative.parts[0] in {"tests", "venv"} or path.name == "llm_gateway.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "api.deepseek.com" in text:
                violations.append(f"{relative}: provider URL")
            if "DEEPSEEK_API_KEY" in text:
                violations.append(f"{relative}: reads provider key")
            if "deepseek_url" in text:
                violations.append(f"{relative}: legacy provider URL field")
        self.assertEqual(violations, [])

if __name__ == "__main__":
    unittest.main()
