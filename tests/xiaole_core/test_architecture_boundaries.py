import ast
import unittest
from pathlib import Path


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_core_has_no_forbidden_legacy_imports(self):
        forbidden = {"agent", "memory", "modules.task_executor", "modules.tool_manager"}
        found = set()
        for path in Path("xiaole_core").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import): found.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module: found.add(node.module)
        self.assertFalse({name for name in found if name in forbidden or any(name.startswith(item + ".") for item in forbidden)})

    def test_persona_is_a_single_file_without_user_facts(self):
        persona = Path("xiaole_core/persona.md").read_text(encoding="utf-8")
        self.assertIn("长期事实来自乐知", persona)
        self.assertNotIn("API_KEY", persona)


if __name__ == "__main__": unittest.main()
