"""🔒 ONE KEEPER PER MACHINE. Two backend processes ticking the same Fuse wallet trade every order twice (2026-10-05: a restart left
the old process alive without its port — both bought $WAIF and $HIGGS, and the books saw one buy each). The keeper holds an exclusive
OS lock on a file for as long as the process lives; a process that can't get it never ticks cards or sends orders. The OS drops the
lock when the process dies, however it dies."""
import fcntl
import os

_held = {}


def acquire(path):
    """True when THIS process holds the keeper lock (taken now or earlier). Never blocks."""
    key = str(path)
    if key in _held:
        return True
    try:
        os.makedirs(os.path.dirname(key) or '.', exist_ok=True)
        fd = os.open(key, os.O_CREAT | os.O_RDWR, 0o644)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return False
    try:
        os.ftruncate(fd, 0); os.write(fd, str(os.getpid()).encode())
    except OSError:
        pass
    _held[key] = fd
    return True


def release(path):
    fd = _held.pop(str(path), None)
    if fd is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
        except OSError:
            pass
