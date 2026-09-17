import importlib.util
import pathlib
import sys

MODULE_PATH = pathlib.Path(__file__).resolve().parent.parent / "aprs-is-wx.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("aprs_is_wx", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# The script's filename isn't a valid Python identifier, so it can't be
# imported normally. Load it once and let every test import it as
# `import aprs_is_wx`.
_load_module()
