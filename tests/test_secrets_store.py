import os
import shutil
import tempfile
import subprocess

import pytest

if not shutil.which("sudo"):
    pytest.skip("sudo not available for root key store tests", allow_module_level=True)

SUDO_PWD = os.environ.get("WIREGUARD_SUDO_PWD") or os.environ.get("SUDO_PWD")
if not SUDO_PWD:
    pytest.skip("SUDO password required for root key store tests", allow_module_level=True)

os.environ.setdefault("WIREGUARD_KEY_DIR", tempfile.mkdtemp(prefix="wg_keys_"))

probe = subprocess.run(
    ["sudo", "-S", "-v"],
    input=(SUDO_PWD + "\n").encode(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if probe.returncode != 0:
    pytest.skip("sudo validation failed for root key store tests", allow_module_level=True)

import secrets_store


def test_store_roundtrip():
    ok, err = secrets_store.set_private_key("profile1", "privkeydata", SUDO_PWD)
    assert ok, err
    got = secrets_store.get_private_key("profile1", SUDO_PWD)
    assert got == "privkeydata"
    bad = secrets_store.get_private_key("profile1", "wrong")
    assert bad is None


def test_delete_secret():
    ok, err = secrets_store.set_private_key("profile2", "k", SUDO_PWD)
    assert ok, err
    ok, err = secrets_store.delete_private_key("profile2", SUDO_PWD)
    assert ok, err
    assert secrets_store.get_private_key("profile2", SUDO_PWD) is None
