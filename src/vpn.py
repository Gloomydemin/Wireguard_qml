#!/usr/bin/env python3
import subprocess
import time
import os
import shutil
import base64
import json
import textwrap
import socket
import zipfile
import tempfile
import configparser
from ipaddress import IPv4Network, IPv4Address
from pathlib import Path

CONFIG_DIR = Path('/home/phablet/.local/share/wireguard.davidv.dev')
PROFILES_DIR = CONFIG_DIR / 'profiles'
LOG_DIR = Path('/home/phablet/.cache/wireguard.davidv.dev')

LOG_DIR.mkdir(parents=True, exist_ok=True)

class Vpn:
    def __init__(self):
        self._sudo_pwd = ''
        self.interface = None

    def set_pwd(self, sudo_pwd):
        self._sudo_pwd = sudo_pwd or ''
        if self._sudo_pwd and self.interface is None:
            try:
                import interface
                self.interface = interface.Interface(self._sudo_pwd)
            except:
                self.interface = None  # Graceful fallback

    def safe_status(self):
        """✅ БЕЗОПАСНЫЙ статус"""
        if not self.interface:
            return {}
        try:
            return self.interface.current_status_by_interface()
        except:
            return {}
        
    def serve_sudo_pwd(self):
        pwd = self._sudo_pwd or ''  # ✅ None → ''
        return subprocess.Popen(['echo', pwd], stdout=subprocess.PIPE)


    def can_use_kernel_module(self):
        if not Path('/usr/bin/sudo').exists():
            return False
        try:
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'add', 'test_wg0', 'type', 'wireguard'], 
                          stdin=serve_pwd.stdout, check=True)
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'del', 'test_wg0'], stdin=serve_pwd.stdout, check=True)
        except subprocess.CalledProcessError:
            return False
        return True

    def _connect(self, profile_name, use_kmod):
        if self.interface is None:
            return "Interface not initialized. Call set_pwd() first."
        try:
            profile_data = self.get_profile(profile_name)
            config_path = PROFILES_DIR / profile_name / 'config.ini'
            return self.interface._connect(profile_data, config_path, use_kmod)
        except Exception as e:
            return str(e)

    def genkey(self):
        return subprocess.check_output(['vendored/wg', 'genkey']).strip().decode()

    def genpubkey(self, privkey):
        p = subprocess.Popen(['vendored/wg', 'pubkey'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(privkey.encode())
        if p.returncode == 0:
            return stdout.strip().decode()
        return stderr.strip().decode()

    def save_profile(self, profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, peers):
        if '/' in profile_name:
            return '"/" is not allowed in profile names'

        # Proper base64 validation: decode to 32 bytes
        try:
            decoded = base64.b64decode(private_key)
            if len(decoded) != 32:
                return 'Private key must decode to exactly 32 bytes'
        except Exception:
            return 'Invalid base64 private key'

        pubkey = self.genpubkey(private_key)
        try:
            IPv4Network(ip_address, strict=False)
        except Exception as e:
            return f'Bad IP address: {e}'

        # Validate peers (simplified, expand as needed)
        for peer in peers:
            if len(peer['key']) != 44 or not peer['name']:
                return f'Invalid peer {peer["name"]}'
            try:
                base64.b64decode(peer['key'])
                if peer['presharedKey'] and (len(peer['presharedKey']) != 44 or not base64.b64decode(peer['presharedKey'])):
                    return f'Invalid PSK for {peer["name"]}'
                for prefix in peer['allowed_prefixes'].split(','):
                    IPv4Network(prefix.strip(), strict=False)
            except Exception as e:
                return f'Peer validation failed for {peer["name"]}: {e}'

        PROFILE_DIR = PROFILES_DIR / profile_name
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        # Secure privkey storage
        privkey_path = PROFILE_DIR / 'privkey'
        privkey_path.write_text(private_key)
        privkey_path.chmod(0o600)   # Secure permissions

        # Profile without privkey (security)
        profile = {
            'peers': peers, 
            'ip_address': ip_address, 
            'dns_servers': dns_servers,
            'extra_routes': extra_routes, 
            'profile_name': profile_name,
            'interface_name': interface_name,
            'private_key': private_key  # ← ВРЕМЕННО для QML!
        }
        (PROFILE_DIR / 'profile.json').write_text(json.dumps(profile, indent=4))

        # Config file INI format WITH spaces (as in original project)
        config_path = PROFILE_DIR / 'config.ini'  # ← ИМЯ ФАЙЛА КАК В ОРИГИНАЛЕ!
        
        # БЕЗ отступов в многострочной строке!
        config_lines = [
            "[Interface]",
            # f"# Profile = {profile_name}",
            f"PrivateKey = {private_key}",
            # f"Address = {ip_address}",
        ]

        
        if dns_servers:
            config_lines.append(f"DNS = {dns_servers}")
        
        for peer in peers:
            config_lines.extend([
                "",
                "[Peer]",
                f"# Name = {peer['name']}",
                f"PublicKey = {peer['key']}",
                f"AllowedIPs = {peer['allowed_prefixes']}",
                f"Endpoint = {peer['endpoint']}",
                "PersistentKeepalive = 25"
            ])
            if peer.get('presharedKey'):
                config_lines.append(f"PresharedKey = {peer['presharedKey']}")
        
        config_path.write_text('\n'.join(config_lines))

        final_config = '\n'.join(config_lines) + '\n'
        config_path.write_text(final_config)

        print("DEBUG: Config content:")
        print(final_config)
        print("DEBUG: Config lines (raw):")
        for i, line in enumerate(config_lines):
            print(f"{i}: {repr(line)}")
        
        config_path.write_text(final_config)
        
        # Также прочитайте и покажите, что записалось
        print("DEBUG: Written content:")
        print(config_path.read_text())

        return "Profile saved successfully"
    
    def import_config(self, file_path):  # Fixed: instance method
        """Import .conf or .zip WireGuard config"""
        try:
            if file_path.endswith('.zip'):
                return self._import_from_zip(file_path)
            elif file_path.endswith('.conf'):
                return self._import_from_conf(file_path)
            return {"error": "Unsupported format. Use .conf or .zip"}
        except Exception as e:
            return {"error": str(e)}

    def _import_from_zip(self, zip_path):
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(tmpdir)
            conf_files = [f for f in os.listdir(tmpdir) if f.endswith('.conf')]
            if not conf_files:
                return {"error": "No .conf files in ZIP"}
            return self._import_from_conf(os.path.join(tmpdir, conf_files[0]))

    def _import_from_conf(self, conf_path):
        """Парсим .conf → save_profile"""
        
        # Читаем файл
        with open(conf_path, 'r') as f:
            content = f.read()
        
        # Парсим WireGuard .conf (поддерживаем оба формата)
        lines = content.strip().split('\n')
        section = None
        data = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                section = line[1:-1]
                data[section] = {}
            elif '=' in line and section:
                # Разделяем по первому знаку равенства
                parts = line.split('=', 1)
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ''
                data[section][key] = value
        
        # Извлекаем Interface
        interface_data = data.get('Interface', {})
        private_key = interface_data.get('PrivateKey', '')
        ip_address = interface_data.get('Address', '10.0.0.2/32')
        dns_servers = interface_data.get('DNS', '')
        
        # Извлекаем пиры
        peers = []
        peer_index = 1
        for sec_name, peer_data in data.items():
            if sec_name == 'Peer' or sec_name.startswith('Peer'):
                peers.append({
                    'name': f'Peer{peer_index}',
                    'key': peer_data.get('PublicKey', ''),
                    'endpoint': peer_data.get('Endpoint', ''),
                    'allowed_prefixes': peer_data.get('AllowedIPs', '0.0.0.0/0'),
                    'presharedKey': peer_data.get('PresharedKey', '')
                })
                peer_index += 1
        
        # Имя профиля из имени файла
        profile_name = Path(conf_path).stem
        
        # ✅ ВЫЗЫВАЕМ save_profile со спарсенными данными!
        result = self.save_profile(
            profile_name=profile_name,
            ip_address=ip_address,
            private_key=private_key,
            interface_name=f'wg{len(os.listdir(PROFILES_DIR)) if PROFILES_DIR.exists() else 0}',
            extra_routes='',  # Пока не парсим
            dns_servers=dns_servers,
            peers=peers
        )
        
        if result.startswith('Error') or result.startswith('Bad'):
            return {"error": result}
        
        return {
            "success": True,
            "profile_name": profile_name,
            "data": {
                "profile_name": profile_name,
                "private_key": private_key,
                "ip_address": ip_address,
                "peers": peers
            }
        }



    def delete_profile(self, profile):
        profile_dir = PROFILES_DIR / profile
        if not profile_dir.exists():
            return f"Profile {profile} not found"
        try:
            shutil.rmtree(profile_dir)
            return ""
        except OSError as e:
            return f"Error: {e}"


    def get_profile(self, profile):
        with (PROFILES_DIR / profile / 'profile.json').open() as f:
            data = json.load(f)
            return data

    def list_profiles(self):
        profiles = []
        for path in PROFILES_DIR.glob('*/profile.json'):
            with path.open() as f:
                data = json.load(f)
                data.setdefault('interface_name', 'wg0')
                data['c_status'] = {}
                profiles.append(data)
        return profiles
    def get_status(self):
        """Метод для QML вместо vpn.instance.interface.current_status_by_interface"""
        return self.safe_status()

instance = Vpn()  # Global for PyOtherSide QML
instance.safe_status = instance.safe_status

if __name__ == "__main__":
    vpn = instance
    print("1. interface:", vpn.interface)
    vpn.set_pwd("test123")
    print("2. interface после set_pwd:", vpn.interface)
    print("3. safe_status:", vpn.safe_status())
    print("4. get_status:", vpn.get_status())
