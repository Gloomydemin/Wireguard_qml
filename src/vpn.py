import subprocess
import time
import os
import shutil
import base64
import json
import textwrap
import socket
import configparser
import zipfile
import tempfile
import re
import ctypes
import urllib.parse

import interface
import daemon

from ipaddress import ip_network
from pathlib import Path

from vendor_paths import resolve_vendor_binary

WG_PATH = resolve_vendor_binary("wg")

APP_ID = 'wireguard.sysadmin'
CONFIG_DIR = Path(f'/home/phablet/.local/share/{APP_ID}')
PROFILES_DIR = CONFIG_DIR / 'profiles'

LOG_DIR = Path(f'/home/phablet/.cache/{APP_ID}')

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

_ZBAR_LIB = None
_GDK_LIB = None
_GOBJECT_LIB = None
_QR_LIBS_READY = None
_ZBAR_FOURCC_Y800 = (ord('Y') | (ord('8') << 8) | (ord('0') << 16) | (ord('0') << 24))


def _load_qr_libs():
    global _ZBAR_LIB, _GDK_LIB, _GOBJECT_LIB, _QR_LIBS_READY
    if _QR_LIBS_READY is not None:
        return _QR_LIBS_READY
    try:
        _ZBAR_LIB = ctypes.CDLL("libzbar.so.0")
        _GDK_LIB = ctypes.CDLL("libgdk_pixbuf-2.0.so.0")
        _GOBJECT_LIB = ctypes.CDLL("libgobject-2.0.so.0")
    except OSError:
        _QR_LIBS_READY = False
        return False

    _GDK_LIB.gdk_pixbuf_new_from_file.restype = ctypes.c_void_p
    _GDK_LIB.gdk_pixbuf_new_from_file.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    _GDK_LIB.gdk_pixbuf_get_width.restype = ctypes.c_int
    _GDK_LIB.gdk_pixbuf_get_width.argtypes = [ctypes.c_void_p]
    _GDK_LIB.gdk_pixbuf_get_height.restype = ctypes.c_int
    _GDK_LIB.gdk_pixbuf_get_height.argtypes = [ctypes.c_void_p]
    _GDK_LIB.gdk_pixbuf_get_n_channels.restype = ctypes.c_int
    _GDK_LIB.gdk_pixbuf_get_n_channels.argtypes = [ctypes.c_void_p]
    _GDK_LIB.gdk_pixbuf_get_rowstride.restype = ctypes.c_int
    _GDK_LIB.gdk_pixbuf_get_rowstride.argtypes = [ctypes.c_void_p]
    _GDK_LIB.gdk_pixbuf_get_pixels.restype = ctypes.POINTER(ctypes.c_ubyte)
    _GDK_LIB.gdk_pixbuf_get_pixels.argtypes = [ctypes.c_void_p]
    _GDK_LIB.gdk_pixbuf_scale_simple.restype = ctypes.c_void_p
    _GDK_LIB.gdk_pixbuf_scale_simple.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]

    _GOBJECT_LIB.g_object_unref.restype = None
    _GOBJECT_LIB.g_object_unref.argtypes = [ctypes.c_void_p]

    _ZBAR_LIB.zbar_image_scanner_create.restype = ctypes.c_void_p
    _ZBAR_LIB.zbar_image_scanner_destroy.argtypes = [ctypes.c_void_p]
    _ZBAR_LIB.zbar_image_create.restype = ctypes.c_void_p
    _ZBAR_LIB.zbar_image_destroy.argtypes = [ctypes.c_void_p]
    _ZBAR_LIB.zbar_image_set_format.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    _ZBAR_LIB.zbar_image_set_size.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    _ZBAR_LIB.zbar_image_set_data.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
    _ZBAR_LIB.zbar_scan_image.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    _ZBAR_LIB.zbar_image_first_symbol.restype = ctypes.c_void_p
    _ZBAR_LIB.zbar_image_first_symbol.argtypes = [ctypes.c_void_p]
    _ZBAR_LIB.zbar_symbol_next.restype = ctypes.c_void_p
    _ZBAR_LIB.zbar_symbol_next.argtypes = [ctypes.c_void_p]
    _ZBAR_LIB.zbar_symbol_get_data.restype = ctypes.c_char_p
    _ZBAR_LIB.zbar_symbol_get_data.argtypes = [ctypes.c_void_p]

    _QR_LIBS_READY = True
    return True


def _decode_qr_from_image_path(path):
    if not _load_qr_libs():
        return None, "QR decoder libraries are not available"

    if not path or not os.path.exists(path):
        return None, "Image path not found"

    pixbuf = _GDK_LIB.gdk_pixbuf_new_from_file(path.encode("utf-8"), None)
    if not pixbuf:
        return None, "Failed to load image"

    try:
        width = _GDK_LIB.gdk_pixbuf_get_width(pixbuf)
        height = _GDK_LIB.gdk_pixbuf_get_height(pixbuf)

        max_dim = 640
        if width > max_dim or height > max_dim:
            scale = max_dim / float(max(width, height))
            new_w = max(1, int(width * scale))
            new_h = max(1, int(height * scale))
            scaled = _GDK_LIB.gdk_pixbuf_scale_simple(pixbuf, new_w, new_h, 2)
            _GOBJECT_LIB.g_object_unref(pixbuf)
            if not scaled:
                return None, "Failed to scale image"
            pixbuf = scaled
            width = new_w
            height = new_h

        n_channels = _GDK_LIB.gdk_pixbuf_get_n_channels(pixbuf)
        rowstride = _GDK_LIB.gdk_pixbuf_get_rowstride(pixbuf)
        pixels = _GDK_LIB.gdk_pixbuf_get_pixels(pixbuf)
        size = rowstride * height
        raw = ctypes.string_at(pixels, size)
    finally:
        if pixbuf:
            _GOBJECT_LIB.g_object_unref(pixbuf)

    gray = bytearray(width * height)
    if n_channels >= 3:
        for y in range(height):
            row_start = y * rowstride
            out_row = y * width
            for x in range(width):
                idx = row_start + x * n_channels
                r = raw[idx]
                g = raw[idx + 1]
                b = raw[idx + 2]
                gray[out_row + x] = (r * 30 + g * 59 + b * 11) // 100
    else:
        for y in range(height):
            row_start = y * rowstride
            out_row = y * width
            for x in range(width):
                idx = row_start + x * n_channels
                gray[out_row + x] = raw[idx]

    scanner = _ZBAR_LIB.zbar_image_scanner_create()
    image = _ZBAR_LIB.zbar_image_create()
    buf = ctypes.create_string_buffer(bytes(gray))
    try:
        _ZBAR_LIB.zbar_image_set_format(image, _ZBAR_FOURCC_Y800)
        _ZBAR_LIB.zbar_image_set_size(image, width, height)
        _ZBAR_LIB.zbar_image_set_data(image, buf, len(gray), None)
        _ZBAR_LIB.zbar_scan_image(scanner, image)
        symbol = _ZBAR_LIB.zbar_image_first_symbol(image)
        if not symbol:
            return None, None
        data = _ZBAR_LIB.zbar_symbol_get_data(symbol)
        if not data:
            return None, None
        return data.decode("utf-8", "replace"), None
    finally:
        _ZBAR_LIB.zbar_image_destroy(image)
        _ZBAR_LIB.zbar_image_scanner_destroy(scanner)

class Vpn:
    def __init__(self):
        self._sudo_pwd = None
        self.interface = None

    def _require_interface(self):
        if not self.interface:
            raise RuntimeError("VPN interface not initialized (sudo password not set)")
        
    def set_pwd(self, sudo_pwd):
        self._sudo_pwd = sudo_pwd
        self.interface = interface.Interface(sudo_pwd)

    def serve_sudo_pwd(self):
        return subprocess.Popen(['echo', self._sudo_pwd], stdout=subprocess.PIPE)

    def can_use_kernel_module(self):
        if not Path('/usr/bin/sudo').exists():
            return False
        if not self._sudo_pwd:
            return False
        try:
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'del', 'test_wg0', 'type', 'wireguard'],
                           stdin=serve_pwd.stdout,
                           check=False,
                           timeout=3)
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'add', 'test_wg0', 'type', 'wireguard'],
                           stdin=serve_pwd.stdout,
                           check=True,
                           timeout=3)
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'del', 'test_wg0', 'type', 'wireguard'],
                           stdin=serve_pwd.stdout,
                           check=False,
                           timeout=3)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return False
        return True

    def _disconnect_other_interfaces(self, keep_interface):
        if not self.interface:
            return
        # First, disconnect any known profile interfaces (cheap and safe).
        try:
            profiles = self._load_profiles()
        except Exception:
            profiles = {}
        for data in profiles.values():
            iface = data.get('interface_name')
            if not iface or iface == keep_interface:
                continue
            try:
                self.interface.disconnect(iface)
            except Exception:
                pass
        # Then, also disconnect any active interfaces we can discover.
        try:
            statuses = self.interface.current_status_by_interface()
        except Exception:
            return
        for iface in list(statuses.keys()):
            if iface == keep_interface:
                continue
            try:
                self.interface.disconnect(iface)
            except Exception:
                pass

    def _load_profiles(self):
        profiles = {}
        if not PROFILES_DIR.exists():
            return profiles
        for path in PROFILES_DIR.glob('*/profile.json'):
            try:
                profiles[path.parent.name] = json.loads(path.read_text())
            except Exception:
                continue
        return profiles

    def _write_profile(self, profile_name, profile):
        profile_dir = PROFILES_DIR / profile_name
        profile_dir.mkdir(exist_ok=True, parents=True)
        profile_file = profile_dir / 'profile.json'
        with profile_file.open('w') as fd:
            json.dump(profile, fd, indent=4, sort_keys=True)

    def _sanitize_interface_name(self, name):
        if not name:
            return ""
        name = name.strip()
        name = re.sub(r'[^A-Za-z0-9_-]', '_', name)
        if not name:
            return ""
        if not name.startswith("wg"):
            name = "wg_" + name
        if len(name) > 15:
            name = name[:15]
        return name

    def _unique_interface_name(self, desired, used):
        base = self._sanitize_interface_name(desired)
        if not base:
            base = "wg0"
        if base not in used:
            return base
        for i in range(1, 1000):
            suffix = f"_{i}"
            max_len = 15 - len(suffix)
            cand = (base[:max_len] if len(base) > max_len else base) + suffix
            if cand not in used:
                return cand
        return base[:15]

    def _ensure_unique_interface_name(self, profile_name, profile):
        profiles = self._load_profiles()

        active_by_privkey = {}
        if self.interface:
            try:
                statuses = self.interface.current_status_by_interface()
                for iface, status in statuses.items():
                    priv = status.get('my_privkey')
                    if priv:
                        active_by_privkey[priv] = iface
            except Exception:
                pass

        used = set()
        for name, data in profiles.items():
            if name == profile_name:
                continue
            iface = data.get('interface_name')
            if iface:
                used.add(iface)
        active_iface = active_by_privkey.get(profile.get('private_key'))
        for iface in active_by_privkey.values():
            if iface == active_iface:
                continue
            used.add(iface)

        desired = active_iface or profile.get('interface_name') or f"wg_{profile_name}"
        unique = self._unique_interface_name(desired, used)
        if unique != profile.get('interface_name'):
            profile['interface_name'] = unique
            self._write_profile(profile_name, profile)

        return profile

    def _connect(self, profile_name,  use_kmod):
        try:
            self._require_interface()
            profile = self._ensure_unique_interface_name(profile_name, self.get_profile(profile_name))
            self._disconnect_other_interfaces(profile.get('interface_name'))
            return self.interface._connect(profile, PROFILES_DIR / profile_name / 'config.ini', use_kmod)
        except Exception as e:
            return str(e)

    def cleanup_userspace(self):
        if not self.interface:
            return "VPN interface not initialized"
        # If sudo password isn't set, bail out quickly to avoid blocking UI on sudo prompts
        if not self._sudo_pwd:
            return None
        try:
            if not self.interface.userspace_running():
                return None
        except Exception:
            pass
        try:
            self.interface.stop_userspace_daemons()
        except Exception:
            pass
        profiles = self._load_profiles()
        for data in profiles.values():
            iface = data.get('interface_name')
            if not iface:
                continue
            try:
                self.interface.disconnect(iface)
            except Exception:
                pass
        return None

    def genkey(self):
        return subprocess.check_output([str(WG_PATH), 'genkey']).decode().strip()

    def genpubkey(self, privkey):
        p = subprocess.Popen([str(WG_PATH), 'pubkey'],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,)

        stdout, stderr = p.communicate(privkey.encode())
        if p.returncode == 0:
            return stdout.decode().strip()
        return stderr.decode().strip()

    def save_profile(self, profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, peers):
        if '/' in profile_name:
            return '"/" is not allowed in profile names'

        if len(private_key) != 44:
            return 'Peer key must be exactly 44 bytes long'

        _pub = self.genpubkey(private_key)
        if len(_pub) != 44:
            return 'Bad private key: ' + _pub

        def _split_csv(val):
            return [x.strip() for x in str(val or "").split(",") if x.strip()]

        try:
            for addr in _split_csv(ip_address):
                ip_network(addr, strict=False)
        except Exception as e:
            return 'Bad ip address {}: {}'.format(addr, e)

        try:
            base64.b64decode(private_key)
        except Exception as e:
            return 'Bad private key'

        for peer in peers:
            if not peer['name']:
                return 'Peer name is incomplete'

            if len(peer['key']) != 44:
                return 'Peer key ({name}) must be exactly 44 bytes long'.format_map(peer)
            try:
                base64.b64decode(peer['key'])
            except Exception as e:
                return 'Bad peer ({name}) key'.format_map(peer)

            if ':' not in peer['endpoint']:
                return 'Bad endpoint ({name}) -- missing ":"'.format_map(peer)

            if len(peer['presharedKey']) > 0 and len(peer['presharedKey']) != 44:
                return 'Preshared key ({name}) must be exactly 44 bytes long'.format_map(peer)
            try:
                base64.b64decode(peer['presharedKey'])
            except Exception as e:
                return 'Bad peer ({name}) preshared key'.format_map(peer)

            allowed_prefixes = peer['allowed_prefixes']
            for allowed_prefix in _split_csv(allowed_prefixes):
                try:
                    ip_network(allowed_prefix, strict=False)
                except Exception as e:
                    return 'Bad peer ({name}) prefix '.format_map(peer) + allowed_prefix + ': ' + str(e)

        if extra_routes:
            for route in _split_csv(extra_routes):
                try:
                    ip_network(route, strict=False)
                except Exception as e:
                    return 'Bad route ' + route + ': ' + str(e)

        if dns_servers:
            for dns in _split_csv(dns_servers):
                try:
                    ip_network(dns, strict=False)
                except Exception as e:
                    return 'Bad dns ' + dns + ': ' + str(e)

        existing_profiles = self._load_profiles()
        used = set()
        for name, data in existing_profiles.items():
            if name == profile_name:
                continue
            iface = data.get('interface_name')
            if iface:
                used.add(iface)

        interface_name = self._unique_interface_name(interface_name or f"wg_{profile_name}", used)

        PROFILE_DIR = PROFILES_DIR / profile_name
        PROFILE_DIR.mkdir(exist_ok=True, parents=True)

        PRIV_KEY_PATH = PROFILE_DIR / 'privkey'
        PROFILE_FILE = PROFILE_DIR / 'profile.json'
        CONFIG_FILE = PROFILE_DIR / 'config.ini'

        with PRIV_KEY_PATH.open('w') as fd:
            fd.write(private_key)

        profile = {'peers': peers,
                   'ip_address': ip_address,
                   'dns_servers': dns_servers,
                   'extra_routes': extra_routes,
                   'profile_name': profile_name,
                   'private_key': private_key,
                   'interface_name': interface_name,
                   }
        self._write_profile(profile_name, profile)

        with CONFIG_FILE.open('w') as fd:
            fd.write(textwrap.dedent('''
            [Interface]
            #Profile = {profile_name}
            PrivateKey = {private_key}
            ''').format_map(profile))
            for peer in peers:
                if len(peer['presharedKey']) > 0:
                    fd.write(textwrap.dedent('''
                    [Peer]
                    #Name = {name}
                    PublicKey = {key}
                    AllowedIPs = {allowed_prefixes}
                    Endpoint = {endpoint}
                    PresharedKey = {presharedKey}
                    PersistentKeepalive = 5
                    '''.format_map(peer)))
                else:
                    fd.write(textwrap.dedent('''
                    [Peer]
                    #Name = {name}
                    PublicKey = {key}
                    AllowedIPs = {allowed_prefixes}
                    Endpoint = {endpoint}
                    PersistentKeepalive = 5
                    '''.format_map(peer)))

    def import_conf(self, path):
        imported_profiles = []

        try:
            if path.endswith(".zip"):
                with zipfile.ZipFile(path) as z:
                    confs = [n for n in z.namelist() if n.endswith(".conf")]
                    if not confs:
                        return {"error": "No .conf in zip"}

                    with tempfile.TemporaryDirectory(prefix="wg_import_") as tmp_dir:
                        for conf_name in confs:
                            tmp_path = os.path.join(tmp_dir, os.path.basename(conf_name))
                            with open(tmp_path, 'wb') as f:
                                f.write(z.read(conf_name))

                            # feed one-by-one into parse_wireguard_conf
                            profile_data = self.parse_wireguard_conf(tmp_path)

                            # profile_data = (profile_name, ip_address, private_key, iface, extra_routes, dns_servers, peers)
                            profile_name = profile_data[0]
                            ip_address = profile_data[1]
                            private_key = profile_data[2]
                            interface_name = profile_data[3]
                            extra_routes = profile_data[4]
                            dns_servers = profile_data[5]
                            peers = profile_data[6]

                            # generate unique profile name on conflict
                            original_name = profile_name
                            suffix = 1
                            while (PROFILES_DIR / profile_name).exists():
                                profile_name = f"{original_name}_{suffix}"
                                suffix += 1

                            error = self.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, peers)
                            if error:
                                return {"error": error}

                            imported_profiles.append(profile_name)

                return {"error": None, "profiles": imported_profiles}

            else:
                # plain single conf
                profile_data = self.parse_wireguard_conf(path)
                profile_name = profile_data[0]
                ip_address = profile_data[1]
                private_key = profile_data[2]
                interface_name = profile_data[3]
                extra_routes = profile_data[4]
                dns_servers = profile_data[5]
                peers = profile_data[6]

                error = self.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, peers)
                if error:
                    return {"error": error}

                return {"error": None, "profiles": [profile_name]}
        except FileNotFoundError:
            return {"error": "File not found"}
        except zipfile.BadZipFile:
            return {"error": "Bad zip file"}
        except Exception as e:
            return {"error": str(e)}



    def _sanitize_profile_name(self, name, fallback):
        cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', name).strip('_')
        return cleaned or fallback

    def _parse_wireguard_conf_lines(self, lines, default_name):
        profile_name = default_name
        interface_name = f"wg_{profile_name}"

        peers = []
        current_peer = None

        iface = {}
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                match = re.match(r"#\s*Profile\s*=\s*(.+)", line, re.IGNORECASE)
                if match:
                    profile_name = self._sanitize_profile_name(match.group(1).strip(), default_name)
                    interface_name = f"wg_{profile_name}"
                continue

            if line == "[Interface]":
                current_peer = None
                continue

            if line == "[Peer]":
                current_peer = {
                    "name": f"Peer{len(peers)+1}",
                    "key": "",
                    "allowed_prefixes": "",
                    "endpoint": "",
                    "presharedKey": ""
                }
                peers.append(current_peer)
                continue

            if "=" not in line:
                continue

            key, val = map(str.strip, line.split("=", 1))

            if current_peer is None:
                iface[key] = val
            else:
                if key == "PublicKey":
                    current_peer["key"] = val
                elif key == "AllowedIPs":
                    current_peer["allowed_prefixes"] = val
                elif key == "Endpoint":
                    current_peer["endpoint"] = val
                elif key == "PresharedKey":
                    current_peer["presharedKey"] = val

        return (
            profile_name,
            iface.get("Address", ""),
            iface.get("PrivateKey", ""),
            interface_name,
            "",
            iface.get("DNS", ""),
            peers
        )

    def parse_wireguard_conf(self, path):
        profile_name = os.path.splitext(os.path.basename(path))[0]
        with open(path) as f:
            lines = f.readlines()
        return self._parse_wireguard_conf_lines(lines, profile_name)

    def _normalize_qr_text(self, text):
        if not text:
            return ""
        data = text.strip()
        if data.startswith("wireguard://") or data.startswith("wg://"):
            payload = data.split("://", 1)[1]
            payload = urllib.parse.unquote(payload)
            candidate = payload.replace("\\n", "\n")
            try:
                decoded = base64.b64decode(payload).decode("utf-8")
                if "[Interface]" in decoded:
                    return decoded
            except (ValueError, UnicodeDecodeError):
                pass
            return candidate
        if "[Interface]" not in data:
            candidate = re.sub(r"\s+", "", data)
            if re.fullmatch(r"[A-Za-z0-9+/=]+", candidate or ""):
                try:
                    decoded = base64.b64decode(candidate).decode("utf-8")
                    if "[Interface]" in decoded:
                        return decoded
                except (ValueError, UnicodeDecodeError):
                    pass
        return data

    def import_conf_text(self, conf_text, profile_name_override=None, interface_name_override=None):
        normalized = self._normalize_qr_text(conf_text)
        if not normalized:
            return {"error": "Empty QR data"}
        if "[Interface]" not in normalized:
            return {"error": "QR does not contain WireGuard config"}

        profile_data = self._parse_wireguard_conf_lines(normalized.splitlines(), "qr_import")
        profile_name = profile_data[0]
        ip_address = profile_data[1]
        private_key = profile_data[2]
        interface_name = profile_data[3]
        extra_routes = profile_data[4]
        dns_servers = profile_data[5]
        peers = profile_data[6]

        if profile_name_override:
            override = self._sanitize_profile_name(str(profile_name_override).strip(), profile_name)
            if override:
                profile_name = override

        if interface_name_override:
            interface_name = str(interface_name_override).strip()
        elif profile_name_override:
            interface_name = f"wg_{profile_name}"

        profiles = self._load_profiles()
        used = set()
        for data in profiles.values():
            iface = data.get('interface_name')
            if iface:
                used.add(iface)
        interface_name = self._unique_interface_name(interface_name or f"wg_{profile_name}", used)

        original_name = profile_name
        suffix = 1
        while (PROFILES_DIR / profile_name).exists():
            profile_name = f"{original_name}_{suffix}"
            suffix += 1

        error = self.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, peers)
        if error:
            return {"error": error}

        return {"error": None, "profiles": [profile_name]}

    def get_wireguard_version(self):
        """
        Returns vendored wireguard-go/wg version info.
        """
        wg_bin = resolve_vendor_binary("wireguard")
        try:
            out = subprocess.check_output([str(wg_bin), "--version"], stderr=subprocess.STDOUT, timeout=3)
            line = out.decode(errors="ignore").strip().splitlines()[0] if out else ""
        except Exception as e:
            line = str(e)
        return {
            "version": line,
            "backend": line,
            "raw": line,
        }

    def export_confs_zip(self):
        """
        Export all config.ini from profiles into wireguard.zip in Downloads.
        """
        downloads = Path("/home/phablet/Downloads")
        downloads.mkdir(parents=True, exist_ok=True)
        base = downloads / "wireguard.zip"

        def next_free_name(path):
            if not path.exists():
                return path
            for i in range(1, 1000):
                cand = path.with_name(f"{path.stem}-{i}{path.suffix}")
                if not cand.exists():
                    return cand
            return path

        target = next_free_name(base)
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
                found = False
                for cfg in PROFILES_DIR.glob("*/config.ini"):
                    found = True
                    name = cfg.parent.name + ".conf"
                    z.write(cfg, arcname=name)
                # if config.ini is missing, fall back to imported .conf
                for conf in PROFILES_DIR.glob("*.conf"):
                    found = True
                    z.write(conf, arcname=conf.name)
                if not found:
                    return {"error": "No profiles to export"}
            return {"error": None, "path": str(target)}
        except Exception as e:
            return {"error": str(e)}

    def decode_qr_image(self, path):
        if path and path.startswith("file://"):
            path = path[7:]
        text, err = _decode_qr_from_image_path(path)
        if err:
            return {"error": err}
        if not text:
            return {"error": "NO_QR"}
        return {"error": None, "text": text}

    def find_barcode_reader_app_id(self):
        search_dirs = [
            Path("/home/phablet/.local/share/applications"),
            Path("/usr/share/applications"),
        ]
        known_desktop = Path("/usr/share/click/preinstalled/.click/users/@all/camera.ubports/lomiri-barcode-reader-app.desktop")
        if known_desktop.exists():
            try:
                text = known_desktop.read_text(errors="ignore")
            except Exception:
                text = ""
            for line in text.splitlines():
                if line.startswith("X-Lomiri-Application-ID="):
                    return line.split("=", 1)[1].strip()
            for line in text.splitlines():
                if line.startswith("Exec="):
                    match = re.search(r"-p\\s+([A-Za-z0-9._-]+)", line)
                    if match:
                        return match.group(1)
        patterns = ("barcode", "qr", "code-reader", "barcode-reader")
        for directory in search_dirs:
            if not directory.exists():
                continue
            for entry in directory.iterdir():
                if not entry.name.endswith(".desktop"):
                    continue
                name_lower = entry.name.lower()
                if not any(pat in name_lower for pat in patterns):
                    continue
                try:
                    text = entry.read_text(errors="ignore")
                except Exception:
                    continue
                app_id = None
                for line in text.splitlines():
                    if line.startswith("X-Lomiri-Application-ID="):
                        app_id = line.split("=", 1)[1].strip()
                        break
                if not app_id:
                    for line in text.splitlines():
                        if line.startswith("Exec="):
                            match = re.search(r"-p\\s+([A-Za-z0-9._-]+)", line)
                            if match:
                                app_id = match.group(1)
                                break
                if app_id:
                    return app_id
        return None

    def launch_app(self, app_id):
        if not app_id:
            return {"error": "Missing app id"}
        launcher_candidates = [
            "/usr/bin/lomiri-app-launch",
            "/usr/bin/ubuntu-app-launch",
        ]
        launcher = None
        for candidate in launcher_candidates:
            if Path(candidate).exists():
                launcher = candidate
                break
        if not launcher:
            return {"error": "No app launcher available"}
        try:
            subprocess.Popen([launcher, app_id],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception as e:
            return {"error": str(e)}
        return {"error": None}


    def delete_profile(self, profile):
        print(profile)
        PROFILE_DIR = PROFILES_DIR / profile
        print(PROFILE_DIR)
        try:
            shutil.rmtree(PROFILE_DIR.as_posix())
        except OSError as e:
            return f'Error: {PROFILE_DIR}: {e.strerror}'


    def get_profile(self, profile):
        with (PROFILES_DIR / profile / 'profile.json').open() as fd:
            data = json.load(fd)
            return data

    def list_profiles(self):
        profiles = []
        raw_profiles = {}
        for path in PROFILES_DIR.glob('*/profile.json'):
            try:
                with path.open() as fd:
                    data = json.load(fd)
            except Exception:
                continue  # skip broken files
            raw_profiles[path.parent.name] = data

        active_by_privkey = {}
        active_ifaces = set()
        if self.interface:
            try:
                statuses = self.interface.current_status_by_interface()
                for iface, status in statuses.items():
                    active_ifaces.add(iface)
                    priv = status.get('my_privkey')
                    if priv:
                        active_by_privkey[priv] = iface
            except Exception:
                pass

        # First, align profiles with active interfaces if possible
        for name, data in raw_profiles.items():
            priv = data.get('private_key')
            if priv and priv in active_by_privkey:
                iface = active_by_privkey[priv]
                if data.get('interface_name') != iface:
                    data['interface_name'] = iface
                    self._write_profile(name, data)

        # Then, ensure uniqueness for all remaining profiles
        used = {}
        for name, data in raw_profiles.items():
            iface = data.get('interface_name')
            if iface and iface not in used:
                used[iface] = name
            else:
                desired = iface or f"wg_{name}"
                unique = self._unique_interface_name(desired, set(used.keys()))
                if unique != iface:
                    data['interface_name'] = unique
                    self._write_profile(name, data)
                iface = unique
                used[iface] = name

            # current status (empty for now, can be updated)
            data['c_status'] = {}
            profiles.append(data)

        return profiles


instance = Vpn()
