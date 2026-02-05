from pathlib import Path
import platform


APP_ROOT = Path(__file__).resolve().parent.parent

_ARCH_MAP = {
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "armv7l": "arm",
    "armv8l": "arm64",
    "arm": "arm",
}


def resolve_vendor_binary(name):
    direct = APP_ROOT / "vendored" / name
    if direct.exists():
        return direct

    machine = platform.machine().lower()
    suffix = _ARCH_MAP.get(machine)
    if suffix:
        candidate = APP_ROOT / "vendored" / f"{name}-{suffix}"
        if candidate.exists():
            return candidate

    for candidate in (APP_ROOT / "vendored").glob(f"{name}-*"):
        return candidate

    return direct
