import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/session-handoff/scripts/test_handoff.py'


def load_tests(loader, tests, pattern):
    spec = importlib.util.spec_from_file_location('handoff_behavior_tests', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)
