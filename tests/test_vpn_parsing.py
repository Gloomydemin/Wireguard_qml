import base64
import importlib
import os
import shutil
import subprocess
import tempfile

import pytest

SUDO_PWD = os.environ.get("WIREGUARD_SUDO_PWD") or os.environ.get("SUDO_PWD")
SUDO_OK = False
if SUDO_PWD and shutil.which("sudo"):
    probe = subprocess.run(
        ["sudo", "-S", "-v"],
        input=(SUDO_PWD + "\n").encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    SUDO_OK = probe.returncode == 0

os.environ.setdefault("WIREGUARD_KEY_DIR", tempfile.mkdtemp(prefix="wg_keys_"))

import secrets_store


def _vpn_module():
    import vpn
    return importlib.reload(vpn)


def test_parse_conf_lines_basic():
    vpn = _vpn_module()
    v = vpn.Vpn()
    lines = [
        "[Interface]",
        "#Profile = My VPN!",
        "PrivateKey = privkey",
        "Address = 10.0.0.2/32",
        "DNS = 1.1.1.1",
        "",
        "[Peer]",
        "PublicKey = pubkey",
        "AllowedIPs = 0.0.0.0/0, ::/0",
        "Endpoint = vpn.example.com:51820",
    ]

    (
        profile_name,
        ip_address,
        private_key,
        iface,
        extra_routes,
        dns,
        peers,
        pre_up,
        post_up,
        pre_down,
        post_down,
    ) = v._parse_wireguard_conf_lines(lines, "default")

    assert profile_name == "My_VPN"
    assert iface == "wg_My_VPN"
    assert ip_address == "10.0.0.2/32"
    assert dns == "1.1.1.1"
    assert len(peers) == 1
    assert pre_up == ""
    assert post_up == ""
    assert pre_down == ""
    assert post_down == ""
    assert peers[0]["endpoint"] == "vpn.example.com:51820"


def test_normalize_qr_text_wireguard_scheme():
    vpn = _vpn_module()
    v = vpn.Vpn()
    conf = "[Interface]\nPrivateKey = abc\nAddress = 10.0.0.1/32\n"
    payload = base64.b64encode(conf.encode("utf-8")).decode("ascii")
    text = "wireguard://" + payload
    assert v._normalize_qr_text(text) == conf


def test_sanitize_interface_name():
    vpn = _vpn_module()
    v = vpn.Vpn()
    assert v._sanitize_interface_name("test") == "wg_test"
    assert v._sanitize_interface_name("wg0") == "wg0"


def test_save_profile_keeps_existing_private_key():
    if not SUDO_OK:
        pytest.skip("sudo required for root key store")
    vpn = _vpn_module()
    v = vpn.Vpn()
    v._sudo_pwd = SUDO_PWD
    profile_name = "existing"
    v._write_profile(
        profile_name,
        {
            "profile_name": profile_name,
            "ip_address": "10.0.0.2/32",
            "dns_servers": "",
            "extra_routes": "",
            "pre_up": "",
            "interface_name": "wg_existing",
            "peers": [],
        },
    )
    ok, err = secrets_store.set_private_key(profile_name, "privkeydata", SUDO_PWD)
    assert ok, err
    peer_key = base64.b64encode(b"\x00" * 32).decode("ascii")
    peers = [
        {
            "name": "peer1",
            "key": peer_key,
            "allowed_prefixes": "0.0.0.0/0",
            "endpoint": "vpn.example.com:51820",
            "presharedKey": "",
        }
    ]
    err = v.save_profile(
        profile_name,
        "10.0.0.2/32",
        "",
        "wg_existing",
        "",
        "",
        "",
        "",
        "",
        "",
        peers,
    )
    assert err is None


def test_parse_conf_lines_with_comments_and_repeats():
    vpn = _vpn_module()
    v = vpn.Vpn()
    lines = [
        "; Profile = Demo VPN",
        "[interface]",
        "PrivateKey = privkey # inline comment",
        "Address = 10.0.0.2/32",
        "Address = 10.0.0.3/32 ; another comment",
        "DNS = 1.1.1.1",
        "DNS = 8.8.8.8",
        "PreUp = echo one",
        "PreUp = echo two # trailing",
        "PostUp = echo post",
        "PreDown = echo predown",
        "PostDown = echo postdown",
        "",
        "[Peer]",
        "PublicKey = pubkey",
        "AllowedIPs = 0.0.0.0/0",
        "AllowedIPs = ::/0",
        "Endpoint = vpn.example.com:51820 # comment",
    ]

    (
        profile_name,
        ip_address,
        private_key,
        iface,
        extra_routes,
        dns,
        peers,
        pre_up,
        post_up,
        pre_down,
        post_down,
    ) = v._parse_wireguard_conf_lines(lines, "default")

    assert profile_name == "Demo_VPN"
    assert iface == "wg_Demo_VPN"
    assert private_key == "privkey"
    assert ip_address == "10.0.0.2/32, 10.0.0.3/32"
    assert dns == "1.1.1.1, 8.8.8.8"
    assert pre_up == "echo one\necho two"
    assert post_up == "echo post"
    assert pre_down == "echo predown"
    assert post_down == "echo postdown"
    assert len(peers) == 1
    assert peers[0]["allowed_prefixes"] == "0.0.0.0/0, ::/0"
    assert peers[0]["endpoint"] == "vpn.example.com:51820"
