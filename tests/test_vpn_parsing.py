import base64
import importlib


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
