import importlib.util
import os
import sys

for path in sys.path:
    file_path = os.path.join(path, 'dataclasses.py')
    if os.path.exists(file_path):
        # Load the builtin module instead.
        break
else:
    file_path = os.path.join(os.path.dirname(__file__), 'dataclasses.py')

module_name = 'dataclasses'
spec = importlib.util.spec_from_file_location(module_name, file_path)
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module
spec.loader.exec_module(module)
