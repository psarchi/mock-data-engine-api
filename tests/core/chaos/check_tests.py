"""Quick check to verify all chaos ops have tests."""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.core.chaos.utils import get_all_registered_chaos_ops  # noqa: E402


def main():
    ops = get_all_registered_chaos_ops()
    print(f"Found {len(ops)} registered chaos ops")
    print()

    missing = []
    for op in ops:
        mod_name = f"tests.core.chaos.test_{op}"
        try:
            mod = importlib.import_module(mod_name)
            streaming_func = getattr(mod, f"test_{op}_streaming", None)
            rest_func = getattr(mod, f"test_{op}_rest", None)

            status = []
            if streaming_func:
                status.append("streaming")
            if rest_func:
                status.append("rest")

            if status:
                print(f"  {op}: {' '.join(status)}")
            else:
                print(f"  {op}: MISSING FUNCTIONS")
                missing.append(op)
        except ImportError:
            print(f"  {op}: MISSING MODULE")
            missing.append(op)

    print()
    if missing:
        print(f"WARNING: Missing tests for chaos ops: {', '.join(missing)}")
        return 1
    else:
        print("All chaos ops have tests!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
