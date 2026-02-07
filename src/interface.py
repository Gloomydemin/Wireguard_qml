import logging
import subprocess
import os
import socket
import json

from pathlib import Path

from vendor_paths import resolve_vendor_binary

WG_PATH = resolve_vendor_binary("wg")
WIREGUARD_GO_PATH = resolve_vendor_binary("wireguard")
log = logging.getLogger(__name__)

class Interface:
    def __init__(self, sudo_pwd):
        # sudo_cmd_list variable is a list like: ['echo', 'password', '|', '/usr/bin/sudo', '-S']
        self._sudo_pwd = sudo_pwd

    def serve_sudo_pwd(self):
        return subprocess.Popen(['echo', self._sudo_pwd], stdout=subprocess.PIPE)

    def _connect(self, profile, config_file, use_kmod):
        interface_name = profile['interface_name']
        self.disconnect(interface_name)

        if use_kmod:
            self.stop_userspace_daemons()
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'add', interface_name, 'type', 'wireguard'],
                            stdin=serve_pwd.stdout,
                            check=True)
            err = self.config_interface(profile, config_file)
            if err:
                return err
        else:
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
        serve_pwd = self.serve_sudo_pwd()
        p = subprocess.Popen(['/usr/bin/sudo', '-S', '/usr/bin/python3', 'src/daemon.py', profile['profile_name'], self._sudo_pwd],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              stdin=serve_pwd.stdout,
                              start_new_session=True,
                            )
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

    def stop_userspace_daemons(self):
        serve_pwd = self.serve_sudo_pwd()
        subprocess.run(
            ['/usr/bin/sudo', '-S', 'pkill', '-f', str(WIREGUARD_GO_PATH)],
            stdin=serve_pwd.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def get_default_gateway(self):
        p = subprocess.check_output(['ip', 'route', 'show', 'default']).decode()
        # default via 10.0.2.2 dev ens5
        return p.split('via')[1].split()[0]

    def get_default_interface(self):
        p = subprocess.check_output(['ip', 'route', 'show', 'default']).decode()
        return p.split('dev')[1].split()[0]



    def config_interface(self, profile, config_file):
        interface_name = profile['interface_name']
        log.info('Configuring interface %s', interface_name)

        def sudo_run(cmd, check=True):
            serve_pwd = self.serve_sudo_pwd()
            return subprocess.run(
                ['/usr/bin/sudo', '-S'] + cmd,
                stdin=serve_pwd.stdout,
                check=check
            )

        # Remove default routes before changes
        default_gw = self.get_default_gateway()
        real_iface = self.get_default_interface()

        # 1. interface down
        sudo_run(['ip', 'link', 'set', 'down', 'dev', interface_name], check=False)

        # 2. setconf
        p = subprocess.Popen(
            ['/usr/bin/sudo', '-S', str(WG_PATH), 'setconf', interface_name, str(config_file)],
            stdin=self.serve_sudo_pwd().stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.wait()
        if p.returncode != 0:
            err = p.stderr.read().decode()
            log.error(err)
            return err

        # 3. address
        sudo_run(['ip', 'address', 'replace', profile['ip_address'], 'dev', interface_name])

        # 4. interface up
        sudo_run(['ip', 'link', 'set', 'up', 'dev', interface_name])
        log.info('Interface up')

        # ---------- ROUTING ----------

        # 5. endpoint exclusion
        endpoint_ip = None
        endpoint = None
        for peer in profile.get('peers', []):
            if peer.get('endpoint'):
                endpoint = peer['endpoint']
                break

        if endpoint:
            endpoint_host = endpoint.split(':')[0]
            try:
                endpoint_ip = socket.gethostbyname(endpoint_host)
                sudo_run([
                    'ip', 'route', 'replace',
                    f'{endpoint_ip}/32',
                    'via', default_gw,
                    'dev', real_iface
                ], check=False)

                self._last_endpoint_ip = endpoint_ip
                log.info('Endpoint route added: %s via %s (%s)', endpoint_ip, default_gw, real_iface)

            except Exception as e:
                log.warning('Failed to add endpoint route: %s', e)
                self._last_endpoint_ip = None

        # 6. AllowedIPs
        add_default = False
        for peer in profile.get('peers', []):
            for prefix in peer.get('allowed_prefixes', '').split(','):
                prefix = prefix.strip()
                if not prefix:
                    continue
                if prefix in ('0.0.0.0/0', '::/0'):
                    add_default = True
                    continue
                sudo_run(['ip', 'route', 'replace', prefix, 'dev', interface_name], check=False)

        # 7. default route via wg
        if add_default:
            sudo_run(['ip', 'route', 'replace', 'default', 'dev', interface_name], check=False)
            log.info('Default route via %s enabled', interface_name)

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
            sudo_run(['ip', 'route', 'replace', extra_route, 'dev', interface_name], check=False)

        return None


    def disconnect(self, interface_name):
        CONFIG_DIR = Path('/home/phablet/.local/share/wireguard.sysadmin')
        PROFILES_DIR = CONFIG_DIR / 'profiles'

        # Always stop userspace daemons to avoid stale wireguard-go processes
        try:
            self.stop_userspace_daemons()
        except Exception:
            # Best-effort cleanup – ignore failures so we can still tear down the interface
            pass

        def sudo_run(cmd, check=False):
            serve_pwd = self.serve_sudo_pwd()
            return subprocess.run(
                ['/usr/bin/sudo', '-S'] + cmd,
                stdin=serve_pwd.stdout,
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
            sudo_run(['resolvectl', 'revert', interface_name])
            sudo_run(['ip', 'link', 'set', 'down', 'dev', interface_name])
            sudo_run(['ip', 'link', 'del', 'dev', interface_name])

        # Drop endpoint routes via physical interface
        try:
            default_gw = self.get_default_gateway()
            real_iface = self.get_default_interface()
        except Exception:
            default_gw = None
            real_iface = None

        if profile and 'peers' in profile and default_gw and real_iface:
            for peer in profile['peers']:
                endpoint = peer.get('endpoint')
                if endpoint:
                    endpoint_host = endpoint.split(':')[0]
                    try:
                        endpoint_ip = socket.gethostbyname(endpoint_host)
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






    def _get_wg_status(self):
        if Path('/usr/bin/sudo').exists():
            if self._sudo_pwd:
                sudo_cmd = ['/usr/bin/sudo', '-S']
                stdin = self.serve_sudo_pwd().stdout
            else:
                sudo_cmd = ['/usr/bin/sudo', '-n']
                stdin = None
            try:
                p = subprocess.run(
                    sudo_cmd + [str(WG_PATH), 'show', 'all', 'dump'],
                    stdin=stdin,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2,
                    check=False
                )
            except subprocess.TimeoutExpired:
                print('`wg show all dump` timed out')
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
