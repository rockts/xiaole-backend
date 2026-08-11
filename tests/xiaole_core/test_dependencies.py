import os
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("db_setup", types.SimpleNamespace(SessionLocal=object()))

from xiaole_core.dependencies import build_brain_core


class DependencyTests(unittest.TestCase):
    def tearDown(self):
        build_brain_core.cache_clear()

    def test_missing_xiaoke_url_keeps_action_gateway_unconfigured(self):
        build_brain_core.cache_clear()
        with patch.dict(os.environ, {}, clear=True), patch("xiaole_core.dependencies.ActionGateway") as action_gateway:
            build_brain_core()
        self.assertEqual(action_gateway.call_args.args[0], "")


if __name__ == "__main__": unittest.main()
