import signal as _real_signal
import threading
import time

class Signal:
    """Wrapper around :mod:`signal` with a minimal Windows implementation.

    The original code uses only ``SIGALRM`` and ``setitimer(ITIMER_REAL, …)``.
    On Linux these are provided by the OS; on Windows they are not.  This
    wrapper emulates the same behaviour using :class:`threading.Timer`.

    The public API matches the subset used in *budget.py*:

    ``signal.signal(signum, handler)`` – stores a handler for ``signum`` and
    returns the previous one.
    ``signal.setitimer(which, seconds, interval=0)`` – starts or stops a real‑time
    timer.  Only ``ITIMER_REAL`` is supported; other values raise
    :class:`NotImplementedError`.
    ``signal.getitimer(which)`` – returns the remaining time and the repeat
    interval for an active timer.
    ``signal.getsignal(signum)`` – retrieves the stored handler.

    The implementation keeps a small in‑memory state; it is *not* thread safe
    but that matches the behaviour of the real module on Windows where only
    the main thread can set signal handlers.
    """

    # ``signal`` constants – use real ones if available, otherwise fall back
    try:
        SIGALRM = _real_signal.SIGALRM
    except AttributeError:  # pragma: no cover - Windows path
        SIGALRM = 15  # common value for SIGALRM on POSIX; arbitrary here
    ITIMER_REAL = getattr(_real_signal, "ITIMER_REAL", 0)

    _handlers = {}
    _timers: dict[int, dict] = {}

    @staticmethod
    def signal(signum, handler):
        # Store the handler and return the previous one.
        prev = Signal._handlers.get(signum)
        Signal._handlers[signum] = handler
        return prev
    @staticmethod
    def getsignal(signum):
        return Signal._handlers.get(signum)

    @staticmethod
    def setitimer(which, seconds, interval=0.0):
        if which != Signal.ITIMER_REAL:
            raise NotImplementedError("Only ITIMER_REAL is supported on Windows")
        # Cancel existing timer if any.
        info = Signal._timers.get(which)
        if info and info["timer"]:
            info["timer"].cancel()
            info["timer"] = None
        if seconds <= 0 and interval == 0:
            return (0.0, 0.0)

        interval = seconds if interval == 0 else interval

        def _callback():
            # Call the stored handler for SIGALRM.
            handler = Signal._handlers.get(Signal.SIGALRM)
            if handler is not None:
                try:
                    handler(Signal.SIGALRM, None)
                except Exception:  # pragma: no cover - defensive
                    pass
            # Reschedule if interval > 0.
            if interval > 0:
                t = threading.Timer(interval, _callback)
                t.daemon = True
                t.start()
                Signal._timers[which]["timer"] = t
                Signal._timers[which]["start"] = time.monotonic()

        # Start the timer.
        t = threading.Timer(seconds, _callback)
        t.daemon = True
        t.start()
        Signal._timers[which] = {
            "timer": t,
            "start": time.monotonic(),
            "seconds": seconds,
            "interval": interval,
        }
        return (seconds, interval)

    @staticmethod
    def getitimer(which):
        info = Signal._timers.get(which)
        if not info or not info["timer"]:
            return (0.0, 0.0)
        elapsed = time.monotonic() - info["start"]
        remaining = max(0.0, info["seconds"] - elapsed)
        return (remaining, info["interval"])

