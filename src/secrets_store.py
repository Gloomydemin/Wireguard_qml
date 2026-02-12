import base64
import hashlib
import hmac
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import pyaes

APP_ID = "wireguard.sysadmin"
APP_HOME = Path(os.environ.get("WIREGUARD_APP_HOME", "/home/phablet"))
CONFIG_DIR = APP_HOME / ".local" / "share" / APP_ID
PROFILES_DIR = CONFIG_DIR / "profiles"
KEY_DIR = Path(os.environ.get("WIREGUARD_KEY_DIR", str(CONFIG_DIR / "keys")))


def available():
    return True


def _sanitize_profile_name(name):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name or ""))
    return safe or "profile"


def key_path(profile_name):
    return KEY_DIR / f"{_sanitize_profile_name(profile_name)}.key"


def _sudo_run(args, sudo_pwd, input_data=None):
    def run(cmd, data):
        return subprocess.run(
            cmd,
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def normalize_error(res):
        err = res.stderr.decode(errors="ignore").strip()
        if "a password is required" in err.lower():
            return "NO_PASSWORD"
        if "incorrect password" in err.lower() or "sorry" in err.lower():
            return "BAD_PASSWORD"
        return err or "SUDO_FAILED"

    if input_data is not None:
        # Avoid injecting password into stdin when sudo creds are cached.
        res = run(["/usr/bin/sudo", "-n"] + args, input_data)
        if res.returncode == 0:
            return res, None
        err = normalize_error(res)
        if err != "NO_PASSWORD":
            return res, err
        if not sudo_pwd:
            return res, "NO_PASSWORD"
        res = run(["/usr/bin/sudo", "-S", "-p", ""] + args, (sudo_pwd + "\n").encode() + input_data)
        if res.returncode != 0:
            return res, normalize_error(res)
        return res, None

    # No stdin needed: try non-interactive first, then fall back to password.
    res = run(["/usr/bin/sudo", "-n"] + args, None)
    if res.returncode == 0:
        return res, None
    err = normalize_error(res)
    if err != "NO_PASSWORD":
        return res, err
    if not sudo_pwd:
        return res, "NO_PASSWORD"
    res = run(["/usr/bin/sudo", "-S", "-p", ""] + args, (sudo_pwd + "\n").encode())
    if res.returncode != 0:
        return res, normalize_error(res)
    return res, None


def secret_exists(profile_name, sudo_pwd=None):
    path = key_path(profile_name)
    if os.geteuid() == 0:
        return path.exists()
    res, err = _sudo_run(["/usr/bin/test", "-f", str(path)], sudo_pwd)
    return bool(res and err is None and res.returncode == 0)


def list_private_keys(sudo_pwd=None):
    if os.geteuid() == 0:
        try:
            if not KEY_DIR.exists():
                return set()
            return {p.stem for p in KEY_DIR.glob("*.key")}
        except Exception:
            return set()

    if not sudo_pwd:
        # Avoid sudo spam when password isn't available.
        return set()

    res, err = _sudo_run(["/bin/ls", "-1", str(KEY_DIR)], sudo_pwd)
    if err:
        return set()
    names = set()
    for line in res.stdout.decode(errors="ignore").splitlines():
        if line.endswith(".key"):
            names.add(Path(line).stem)
    return names


def set_private_key(profile_name, private_key, sudo_pwd):
    key_bytes = private_key
    if isinstance(key_bytes, str):
        key_bytes = key_bytes.strip().encode()
    if not key_bytes:
        return False, "Private key is required"

    path = key_path(profile_name)
    script = (
        "umask 077; "
        f"mkdir -p {shlex.quote(str(KEY_DIR))}; "
        f"chmod 700 {shlex.quote(str(KEY_DIR))}; "
        f"chown root:root {shlex.quote(str(KEY_DIR))}; "
        f"cat > {shlex.quote(str(path))}; "
        f"chmod 600 {shlex.quote(str(path))}; "
        f"chown root:root {shlex.quote(str(path))}"
    )
    res, err = _sudo_run(["/bin/sh", "-c", script], sudo_pwd, input_data=key_bytes + b"\n")
    if err:
        return False, err
    return True, None


def get_private_key(profile_name, sudo_pwd, return_error=False):
    if not sudo_pwd:
        return (None, "NO_PASSWORD") if return_error else None
    path = key_path(profile_name)
    res, err = _sudo_run(["/bin/cat", str(path)], sudo_pwd)
    if err:
        if "No such file" in err or "not found" in err:
            return (None, "MISSING") if return_error else None
        return (None, err) if return_error else None
    key = res.stdout.decode(errors="ignore").strip()
    return (key, None) if return_error else key


def delete_private_key(profile_name, sudo_pwd):
    path = key_path(profile_name)
    if os.geteuid() == 0:
        try:
            if path.exists():
                path.unlink()
        except Exception as e:
            return False, str(e)
        return True, None
    if not sudo_pwd:
        return False, "NO_PASSWORD"
    res, err = _sudo_run(["/bin/rm", "-f", str(path)], sudo_pwd)
    if err:
        return False, err
    return True, None


# ---- Legacy encrypted store (read-only, for migration) ----

def _legacy_secret_path(profile_name):
    return PROFILES_DIR / profile_name / "secret.json"


def legacy_secret_exists(profile_name):
    return _legacy_secret_path(profile_name).exists()


def _legacy_derive_keys(password, salt, meta):
    pwd = (password or "").encode()
    kdf = (meta or {}).get("kdf") or "scrypt"
    if kdf == "scrypt":
        n = int((meta or {}).get("n") or 2 ** 14)
        r = int((meta or {}).get("r") or 8)
        p = int((meta or {}).get("p") or 1)
        try:
            key = hashlib.scrypt(pwd, salt=salt, n=n, r=r, p=p, dklen=64)
            return key[:32], key[32:], {"kdf": "scrypt", "n": n, "r": r, "p": p}
        except Exception:
            pass
    iters = int((meta or {}).get("iters") or 200000)
    key = hashlib.pbkdf2_hmac("sha256", pwd, salt, iters, dklen=64)
    return key[:32], key[32:], {"kdf": "pbkdf2", "iters": iters}


def _legacy_hmac_data(meta, salt, nonce, ct):
    parts = [meta.get("kdf", "")]
    if meta.get("kdf") == "scrypt":
        parts += [str(meta.get("n", "")), str(meta.get("r", "")), str(meta.get("p", ""))]
    if meta.get("kdf") == "pbkdf2":
        parts += [str(meta.get("iters", ""))]
    meta_bytes = "|".join(parts).encode()
    return meta_bytes + b"|" + salt + nonce + ct


def legacy_get_private_key(profile_name, password, return_error=False):
    if not password:
        return (None, "NO_PASSWORD") if return_error else None
    secret_file = _legacy_secret_path(profile_name)
    if not secret_file.exists():
        return (None, "MISSING") if return_error else None
    try:
        blob = json.loads(secret_file.read_text())
        salt = base64.b64decode(blob.get("salt", ""))
        nonce = base64.b64decode(blob.get("nonce", ""))
        ct = base64.b64decode(blob.get("ct", ""))
        mac = base64.b64decode(blob.get("hmac", ""))
    except Exception:
        return (None, "CORRUPT") if return_error else None
    meta = {
        "kdf": blob.get("kdf") or "scrypt",
        "n": blob.get("n"),
        "r": blob.get("r"),
        "p": blob.get("p"),
        "iters": blob.get("iters"),
    }
    enc_key, mac_key, _ = _legacy_derive_keys(password, salt, meta)
    expected = hmac.new(mac_key, _legacy_hmac_data(meta, salt, nonce, ct), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, mac):
        return (None, "BAD_PASSWORD") if return_error else None
    try:
        counter = pyaes.Counter(int.from_bytes(nonce, "big"))
        aes = pyaes.AESModeOfOperationCTR(enc_key, counter=counter)
        pt = aes.decrypt(ct)
        return (pt.decode(errors="ignore").strip(), None) if return_error else pt.decode(errors="ignore").strip()
    except Exception:
        return (None, "DECRYPT_FAILED") if return_error else None


def legacy_delete_secret(profile_name):
    secret_file = _legacy_secret_path(profile_name)
    try:
        if secret_file.exists():
            secret_file.unlink()
    except Exception as e:
        return False, str(e)
    return True, None
