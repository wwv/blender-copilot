from pathlib import Path
import importlib.util

# Resolve repository root and load modules by path, like test_context.py
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load the _signal module from the package
_signal_path = ROOT / "blender_copilot" / "_signal.py"
Signal = load("_signal", _signal_path).Signal

def check(label: str, condition: bool, extra: str = "") -> None:
    global CHECKS
    CHECKS += 1
    assert condition, f"FAILED: {label} {extra}"
    print(f"ok   {label}")

import time
CHECKS = 0

def test_setitimer_sets_timer(monkeypatch):
    # Ensure no timer running before the test
    Signal.setitimer(Signal.ITIMER_REAL, 0)

    called = []
    def handler(signum, frame):
        called.append(True)

    # Register a dummy handler for SIGALRM
    Signal.signal(Signal.SIGALRM, handler)

    # Call setitimer with seconds=10 and interval=3
    ret = Signal.setitimer(Signal.ITIMER_REAL, 10, 3)
    check("setitimer returns the tuple", ret == (10, 3))
    # Immediately check that getitimer reports the correct remaining time and interval
    rem, inter = Signal.getitimer(Signal.ITIMER_REAL)
    # Allow a small drift due to execution time
    check("getitimer reports remaining time", abs(rem - 10) < 0.5)
    check("getitimer reports interval", inter == 3)
    # Sleep briefly – less than the timer period – so the handler should not fire yet
    time.sleep(0.1)
    check("handler should wait for delay", called == [])
    # Подождём достаточное время, чтобы таймер сработал дважды (10s и 13s)
    time.sleep(15)
    # Ожидаем ровно два вызова обработчика
    check("handler should fire twice after delay", len(called) == 2)
    # Останавливаем таймер, чтобы не оставить живого потока
    Signal.setitimer(Signal.ITIMER_REAL, 0)



if __name__ == "__main__":
    try:
        test_setitimer_sets_timer(None)
        print(f"{CHECKS} checks passed")
    except AssertionError as e:
        print("test failed:", e)


