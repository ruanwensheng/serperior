import sys
import os
import traceback

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import serperior.api as api
    print('imported serperior.api OK')
    print('exported names:', [n for n in dir(api) if not n.startswith('_')])
except Exception:
    traceback.print_exc()
