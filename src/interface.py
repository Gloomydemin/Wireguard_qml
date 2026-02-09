import logging
import subprocess
import os
import socket
import json
import re
import tempfile

from pathlib import Path

from vendor_paths import resolve_vendor_binary
from profile import PROFILES_DIR
from wg_config import build_config

WG_PATH = resolve_vendor_binary("wg")
WIREGUARD_GO_PATH = resolve_vendor_binary("wireguard")
log = logging.getLogger(__name__)

class Interface:
    def __init__(self, sudo_pwd):
        # Sudo password is kept in-memory and passed via stdin (no argv leaks).
        self._sudo_pwd = sudo_pwd

    def _sudo_cmd(self):
        if self._sudo_pwd:
            return ['/usr/bin/sudo', '-S']
        return ['/usr/bin/sudo', '-n']

    def _sudo_input(self):
        if not self._sudo_pwd:
            return None
        return (self._sudo_pwd + '\n').encode()

    def _parse_endpoint_host(self, endpoint):
        if not endpoint:
            return None
        endpoint = endpoint.strip()
        if endpoint.startswith('['):
            end = endpoint.find(']')
            if end != -1:
                return endpoint[1:end]
        if ':' in endpoint:
            return endpoint.rsplit(':', 1)[0]
        return endpoint

    def _resolve_endpoint_ips(self, endpoint):
        host = self._parse_endpoint_host(endpoint)
        if not host:
            return []
        try:
            infos = socket.getaddrinfo(host, None)
        except Exception:
            return []
        ips = []
        for info in infos:
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
        return ips

    def _connect(self, profile, config_file, use_kmod):
        interface_name = profile['interface_name']
        if self.interface_exists(interface_name):
            self.disconnect(interface_name)

        if use_kmod:
            if self.userspace_running():
                self.stop_userspace_daemons()
            subprocess.run(self._sudo_cmd() + ['ip', 'link', 'add', interface_name, 'type', 'wireguard'],
                           input=self._sudo_input(),
                           check=True)
            err = self.config_interface(profile, config_file)
            if err:
                return err
        else:
            if self.userspace_running():
                self.stop_userspace_daemons()
            err = self.check_userspace_binary()
            if err:
                return err
            self.start_daemon(profile, config_file)

        return None

    def check_userspace_binary(self):
        try:
            p = subprocess.run(
                [str(WIREGUARD_GO_PATH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
        except FileNotFoundError:
            return "Userspace binary not found"
        except OSError as e:
            return f"Userspace binary failed to start: {e}"

        stderr = p.stderr.decode(errors='ignore')
        if "GLIBC_" in stderr or "not found" in stderr:
            return "Userspace binary incompatible: " + stderr.strip()
        return None


    def start_daemon(self, profile, config_file):
        p = subprocess.Popen(['/usr/bin/python3', 'src/daemon.py', profile['profile_name']],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             start_new_session=True,
                            )
        try:
            if p.stdin:
                p.stdin.write((self._sudo_pwd or "") .encode() + b"\n")
                p.stdin.flush()
        finally:
            if p.stdin:
                p.stdin.close()
        print('started daemon')

    def userspace_running(self):
        try:
            p = subprocess.run(
                ['pgrep', '-f', str(WIREGUARD_GO_PATH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            return p.returncode == 0
        except FileNotFoundError:
            p = subprocess.run(
                ['ps', '-eo', 'cmd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if p.returncode != 0:
                return False
            haystack = p.stdout.decode(errors='ignore')
            return str(WIREGUARD_GO_PATH) in haystack

    def interface_exists(self, interface_name):
        try:
            return subprocess.run(
                ['ip', 'link', 'show', interface_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            ).returncode == 0
        except Exception:
            return False

    def stop_userspace_daemons(self):
        if not self.userspace_running():
            return
        subprocess.run(
            self._sudo_cmd() + ['pkill', '-f', str(WIREGUARD_GO_PATH)],
            input=self._sudo_input(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def _get_default_route(self, family):
        cmd = ['ip']
        if family == socket.AF_INET6:
            cmd.append('-6')
        elif family == socket.AF_INET:
            cmd.append('-4')
        cmd += ['route', 'show', 'default']
        try:
            output = subprocess.check_output(cmd).decode(errors='ignore').splitlines()
        except Exception:
            return None, None
        for line in output:
            parts = line.split()
            if not parts:
                continue
            gw = None
            dev = None
            if 'via' in parts:
                try:
                    gw = parts[parts.index('via') + 1]
                except Exception:
                    gw = None
            if 'dev' in parts:
                try:
                    dev = parts[parts.index('dev') + 1]
                except Exception:
                    dev = None
            return gw, dev
        return None, None

    def get_default_gateway(self):
        gw, _ = self._get_default_route(socket.AF_INET)
        return gw

    def get_default_interface(self):
        _, dev = self._get_default_route(socket.AF_INET)
        return dev

    def get_default_gateway_v6(self):
        gw, _ = self._get_default_route(socket.AF_INET6)
        return gw

    def get_default_interface_v6(self):
        _, dev = self._get_default_route(socket.AF_INET6)
        return dev

    def list_wireguard_interfaces(self):
        try:
            p = subprocess.run(
                ['ip', '-o', 'link', 'show', 'type', 'wireguard'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            if p.returncode != 0:
                raise RuntimeError("no wireguard type support")
            lines = p.stdout.decode(errors='ignore').splitlines()
        except Exception:
            try:
                p = subprocess.run(
                    ['ip', '-o', 'link', 'show'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                lines = p.stdout.decode(errors='ignore').splitlines()
            except Exception:
                return []

        ifaces = []
        for line in lines:
            parts = line.split(':', 2)
            if len(parts) < 2:
                continue
            name = parts[1].strip().split('@')[0]
            if name.startswith('wg'):
                ifaces.append(name)
        return ifaces


    def config_interface(self, profile, config_file):
        interface_name = profile['interface_name']
        log.info('Configuring interface %s', interface_name)

        def sudo_run(cmd, check=True):
            return subprocess.run(
                self._sudo_cmd() + cmd,
                input=self._sudo_input(),
                check=check
            )

        # Remove default routes before changes
        default_gw = self.get_default_gateway()
        real_iface = self.get_default_interface()
        default_gw_v6 = self.get_default_gateway_v6()
        real_iface_v6 = self.get_default_interface_v6()

        # 1. interface down
        sudo_run(['ip', 'link', 'set', 'down', 'dev', interface_name], check=False)

        # 2. setconf (use temp config to avoid writing secrets to disk)
        private_key = (profile.get('private_key') or "").strip()
        if not private_key:
            err = f'Private key not found for {profile.get("profile_name", interface_name)}'
            log.error(err)
            return err
        config_text = build_config(profile, private_key)
        tmp_path = None
        try:
            tmp_dir = Path(config_file).parent if config_file else None
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=str(tmp_dir) if tmp_dir else None) as tf:
                tf.write(config_text)
                tmp_path = tf.name
            try:
                os.chmod(tmp_path, 0o600)
            except Exception:
                pass
            p = subprocess.Popen(
                self._sudo_cmd() + [str(WG_PATH), 'setconf', interface_name, tmp_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = p.communicate(input=self._sudo_input())
            if p.returncode != 0:
                err = (stderr or b'').decode(errors='ignore')
                log.error(err)
                return err
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # 3. address
        ip_raw = profile.get('ip_address', '').strip()
        if not ip_raw:
            err = f'No IP address configured for {profile.get("name", interface_name)}'
            log.error(err)
            return err

        addr_list = [a for a in re.split(r'[\\s,]+', ip_raw) if a]

        # Replace the first address, add the rest (so multi-IP configs work)
        sudo_run(['ip', 'address', 'replace', addr_list[0], 'dev', interface_name])
        for extra_addr in addr_list[1:]:
            sudo_run(['ip', 'address', 'add', extra_addr, 'dev', interface_name], check=False)

        # PreUp hooks (wg-quick compatible)
        pre_up = (profile.get('pre_up') or '').strip()
        if pre_up:
            for cmd in [c.strip() for c in re.split(r'[;\\n]+', pre_up) if c.strip()]:
                log.info('Running PreUp: %s', cmd)
                res = sudo_run(['/bin/sh', '-c', cmd], check=False)
                if res.returncode != 0:
                    err = f'PreUp failed: {cmd}'
                    log.error(err)
                    return err

        # 4. interface up
        sudo_run(['ip', 'link', 'set', 'up', 'dev', interface_name])
        log.info('Interface up')

        # ---------- ROUTING ----------

        # 5. endpoint exclusion
        endpoint = None
        for peer in profile.get('peers', []):
            if peer.get('endpoint'):
                endpoint = peer['endpoint']
                break

        if endpoint:
            endpoint_ips = self._resolve_endpoint_ips(endpoint)
            if not endpoint_ips:
                log.warning('Failed to resolve endpoint: %s', endpoint)
            for endpoint_ip in endpoint_ips:
                try:
                    if ':' in endpoint_ip:
                        if default_gw_v6 and real_iface_v6:
                            sudo_run([
                                'ip', '-6', 'route', 'replace',
                                f'{endpoint_ip}/128',
                                'via', default_gw_v6,
                                'dev', real_iface_v6
                            ], check=False)
                            log.info('Endpoint IPv6 route added: %s via %s (%s)', endpoint_ip, default_gw_v6, real_iface_v6)
                    else:
                        if default_gw and real_iface:
                            sudo_run([
                                'ip', 'route', 'replace',
                                f'{endpoint_ip}/32',
                                'via', default_gw,
                                'dev', real_iface
                            ], check=False)
                            log.info('Endpoint IPv4 route added: %s via %s (%s)', endpoint_ip, default_gw, real_iface)
                except Exception as e:
                    log.warning('Failed to add endpoint route: %s', e)

        # 6. AllowedIPs
        add_default_v4 = False
        add_default_v6 = False
        for peer in profile.get('peers', []):
            for prefix in peer.get('allowed_prefixes', '').split(','):
                prefix = prefix.strip()
                if not prefix:
                    continue
                if prefix == '0.0.0.0/0':
                    add_default_v4 = True
                    continue
                if prefix == '::/0':
                    add_default_v6 = True
                    continue
                if ':' in prefix:
                    sudo_run(['ip', '-6', 'route', 'replace', prefix, 'dev', interface_name], check=False)
                else:
                    sudo_run(['ip', 'route', 'replace', prefix, 'dev', interface_name], check=False)

        # 7. default route via wg
        if add_default_v4:
            sudo_run(['ip', 'route', 'replace', 'default', 'dev', interface_name], check=False)
            log.info('Default IPv4 route via %s enabled', interface_name)
        if add_default_v6:
            sudo_run(['ip', '-6', 'route', 'replace', 'default', 'dev', interface_name], check=False)
            log.info('Default IPv6 route via %s enabled', interface_name)

        # ---------- DNS ----------
        dns_servers = [dns.strip() for dns in profile.get('dns_servers', '').split(',') if dns.strip()]
        if dns_servers:
            sudo_run(['resolvectl', 'dns', interface_name] + dns_servers)
            sudo_run(['resolvectl', 'domain', interface_name, '~.'])
            log.info('DNS configured for %s', interface_name)

        # ---------- EXTRA ROUTES ----------
        for extra_route in profile.get('extra_routes', '').split(','):
            extra_route = extra_route.strip()
            if not extra_route:
                continue
            if ':' in extra_route:
                sudo_run(['ip', '-6', 'route', 'replace', extra_route, 'dev', interface_name], check=False)
            else:
                sudo_run(['ip', 'route', 'replace', extra_route, 'dev', interface_name], check=False)

        return None


    def disconnect(self, interface_name):
        # Always stop userspace daemons to avoid stale wireguard-go processes
        try:
            self.stop_userspace_daemons()
        except Exception:
            # Best-effort cleanup – ignore failures so we can still tear down the interface
            pass

        def sudo_run(cmd, check=False):
            return subprocess.run(
                self._sudo_cmd() + cmd,
                input=self._sudo_input(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=check
            )

        # Load profile by interface name (no assumptions about prefixes)
        profile = {}
        if PROFILES_DIR.exists():
            for profile_json in PROFILES_DIR.glob('*/profile.json'):
                try:
                    data = json.loads(profile_json.read_text())
                except Exception:
                    continue
                if data.get('interface_name') == interface_name:
                    profile = data
                    break

        # Check if interface exists
        iface_exists = subprocess.run(
            ['ip', 'link', 'show', interface_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).returncode == 0

        if iface_exists:
            sudo_run(['ip', 'route', 'flush', 'dev', interface_name])
            sudo_run(['ip', '-6', 'route', 'flush', 'dev', interface_name], check=False)
            sudo_run(['resolvectl', 'revert', interface_name])
            sudo_run(['ip', 'link', 'set', 'down', 'dev', interface_name])
            sudo_run(['ip', 'link', 'del', 'dev', interface_name])

        # Drop endpoint routes via physical interface
        default_gw = self.get_default_gateway()
        real_iface = self.get_default_interface()
        default_gw_v6 = self.get_default_gateway_v6()
        real_iface_v6 = self.get_default_interface_v6()

        if profile and 'peers' in profile:
            for peer in profile['peers']:
                endpoint = peer.get('endpoint')
                if endpoint:
                    endpoint_ips = self._resolve_endpoint_ips(endpoint)
                    for endpoint_ip in endpoint_ips:
                        try:
                            if ':' in endpoint_ip:
                                routes = subprocess.check_output(['ip', '-6', 'route']).decode().splitlines()
                                for line in routes:
                                    if endpoint_ip in line:
                                        parts = line.split()
                                        sudo_run(['ip', '-6', 'route', 'del'] + parts)
                            else:
                                routes = subprocess.check_output(['ip', 'route']).decode().splitlines()
                                for line in routes:
                                    if endpoint_ip in line:
                                        parts = line.split()
                                        sudo_run(['ip', 'route', 'del'] + parts)
                        except Exception:
                            pass

        # Restore default route via physical interface
        if default_gw and real_iface:
            try:
                routes = subprocess.check_output(['ip', 'route', 'show', 'default']).decode()
                if f'dev {real_iface}' not in routes:
                    sudo_run(['ip', 'route', 'replace', 'default', 'via', default_gw, 'dev', real_iface])
            except Exception:
                pass
        if default_gw_v6 and real_iface_v6:
            try:
                routes = subprocess.check_output(['ip', '-6', 'route', 'show', 'default']).decode()
                if f'dev {real_iface_v6}' not in routes:
                    sudo_run(['ip', '-6', 'route', 'replace', 'default', 'via', default_gw_v6, 'dev', real_iface_v6])
            except Exception:
                pass






    def _get_wg_status(self):
        if Path('/usr/bin/sudo').exists():
            sudo_cmd = self._sudo_cmd()
            stdin = self._sudo_input()
            try:
                cmd = [str(WG_PATH), 'show', 'all', 'dump']
                # Prefer external timeout to avoid PermissionError on kill
                if Path('/usr/bin/timeout').exists():
                    cmd = ['/usr/bin/timeout', '2'] + cmd
                p = subprocess.run(
                    sudo_cmd + cmd,
                    input=stdin,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
            except Exception as e:
                print('`wg show all dump` failed:', e)
                return []
            if p.returncode != 0:
                print('Failed to run `wg show all dump`:')
                print(p.stdout.decode(errors='ignore').strip())
                print(p.stderr.decode(errors='ignore').strip())
                return []
            lines = p.stdout.decode(errors='ignore').strip().splitlines()
            return lines
        return '''
    wg0	qJ1YWXV6nPmouAditrRahp+5X/DlBJD02ZPkFjbLdE4=	iSOYKa61gszRvGnA4+IMkxEp364e1LrIcGuXcM4IeU8=	0	off
    wg0	YLA3Gq/GW0QrQQfPA5wq7zfXnQI94a7oA8780hwHxWU=	(none)	143.178.241.68:1194	10.88.88.1/32,192.168.2.0/24	1630599999	0	0	off
    wg0	YLA3Gq/GW0QrQQfPA5wq7zfXnQI94a7oA8780hwHxWU=	(none)	143.178.241.68:1194	10.88.88.1/32,192.168.2.0/24	0	0	0	off
    wg1	my_privkey	my_pubkey	0	off
    wg1	peer_pubkey	(none)	143.178.241.68:1194	10.88.88.1/32,192.168.2.0/24	0	0	0	off
    '''.strip().splitlines()

    def current_status_by_interface(self):
        last_interface = None
        data = self._get_wg_status()
        interface_status = {}
        status_by_interface = {}

        for line in data:
            parts = line.split('\t')
            iface = parts[0]

            if iface != last_interface and interface_status:
                status_by_interface[last_interface] = interface_status
                interface_status = {}

            if len(parts) == 5:
                iface, private_key, public_key, listen_port, fwmark = parts
                interface_status = {
                    'my_privkey': private_key,
                    'peers': []
                }
                last_interface = iface

            elif len(parts) == 9:
                iface, public_key, preshared_key, endpoint, allowed_ips, latest_handshake, transfer_rx, transfer_tx, persistent_keepalive = parts
                peer_data = {
                    'public_key': public_key,
                    'rx': int(transfer_rx),
                    'tx': int(transfer_tx),
                    'latest_handshake': int(latest_handshake),
                    'up': int(latest_handshake) > 0,
                }
                interface_status.setdefault('peers', []).append(peer_data)
                interface_status['peers'].sort(key=lambda x: not x['up'])

            else:
                raise ValueError(f"Can't parse line: {line}")

        if last_interface:
            status_by_interface[last_interface] = interface_status

        return status_by_interface
