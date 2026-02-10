import base64
import importlib

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

    profile_name, ip_address, private_key, iface, extra_routes, dns, peers, pre_up = v._parse_wireguard_conf_lines(
        lines, "default"
    )

    assert profile_name == "My_VPN"
    assert iface == "wg_My_VPN"
    assert ip_address == "10.0.0.2/32"
    assert dns == "1.1.1.1"
    assert len(peers) == 1
    assert pre_up == ""
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
    vpn = _vpn_module()
    v = vpn.Vpn()
    v._sudo_pwd = "pw"
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
    ok, err = secrets_store.set_private_key(profile_name, "privkeydata", "pw")
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
        "",
        "[Peer]",
        "PublicKey = pubkey",
        "AllowedIPs = 0.0.0.0/0",
        "AllowedIPs = ::/0",
        "Endpoint = vpn.example.com:51820 # comment",
    ]

    profile_name, ip_address, private_key, iface, extra_routes, dns, peers, pre_up = v._parse_wireguard_conf_lines(
        lines, "default"
    )

    assert profile_name == "Demo_VPN"
    assert iface == "wg_Demo_VPN"
    assert private_key == "privkey"
    assert ip_address == "10.0.0.2/32, 10.0.0.3/32"
    assert dns == "1.1.1.1, 8.8.8.8"
    assert pre_up == "echo one\necho two"
    assert len(peers) == 1
    assert peers[0]["allowed_prefixes"] == "0.0.0.0/0, ::/0"
    assert peers[0]["endpoint"] == "vpn.example.com:51820"
