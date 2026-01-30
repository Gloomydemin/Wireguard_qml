import logging
import subprocess
import os
from pathlib import Path

WG_PATH = Path(os.getcwd()) / "vendored/wg"
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
            serve_pwd = self.serve_sudo_pwd()
            subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'add', interface_name, 'type', 'wireguard'],
                            stdin=serve_pwd.stdout,
                            check=True)
            self.config_interface(profile, config_file)
        else:
            self.start_daemon(profile, config_file)


    def start_daemon(self, profile, config_file):
        serve_pwd = self.serve_sudo_pwd()
        p = subprocess.Popen(['/usr/bin/sudo', '-S', '/usr/bin/python3', 'src/daemon.py', profile['profile_name'], self._sudo_pwd],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              stdin=serve_pwd.stdout,
                              start_new_session=True,
                            )
        print('started daemon')

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
        sudo_run(['ip', 'address', 'add', 'dev', interface_name, profile['ip_address']])

        # 4. interface up
        sudo_run(['ip', 'link', 'set', 'up', 'dev', interface_name])
        log.info('Interface up')

        # ---- ROUTING ----

        # 5. исключаем endpoint из wg (КРИТИЧНО)
        endpoint = profile.get('endpoint')  # "host:port"
        if endpoint:
            endpoint_host = endpoint.split(':')[0]
            try:
                endpoint_ip = socket.gethostbyname(endpoint_host)
                default_gw = self.get_default_gateway()  # ты её где-то уже получаешь
                real_iface = self.get_default_interface()

                sudo_run([
                    'ip', 'route', 'add',
                    f'{endpoint_ip}/32',
                    'via', default_gw,
                    'dev', real_iface
                ], check=False)

                log.info('Endpoint route added: %s via %s', endpoint_ip, real_iface)
            except Exception as e:
                log.warning('Failed to add endpoint route: %s', e)

        # 6. AllowedIPs (кроме default)
        add_default = False
        for peer in profile['peers']:
            allowed_ips = peer.get('allowed_prefixes', '')
            for prefix in allowed_ips.split(','):
                prefix = prefix.strip()
                if not prefix:
                    continue

                if prefix in ('0.0.0.0/0', '::/0'):
                    add_default = True
                    continue

                sudo_run(
                    ['ip', 'route', 'add', prefix, 'dev', interface_name],
                    check=False
                )

        # 7. default route — СТРОГО ПОСЛЕ endpoint
        if add_default:
            sudo_run(['ip', 'route', 'add', 'default', 'dev', interface_name], check=False)
            log.info('Default route via %s enabled', interface_name)

        # ---- DNS ----
        dns_servers = [
            dns.strip() for dns in profile.get('dns_servers', '').split(',')
            if dns.strip()
        ]

        if dns_servers:
            sudo_run(['resolvectl', 'dns', interface_name] + dns_servers)
            sudo_run(['resolvectl', 'domain', interface_name, '~.'])
            log.info('DNS configured for %s', interface_name)

        # ---- EXTRA ROUTES ----
        for extra_route in profile.get('extra_routes', '').split(','):
            extra_route = extra_route.strip()
            if not extra_route:
                continue
            sudo_run(['ip', 'route', 'add', extra_route, 'dev', interface_name], check=False)

        return None


    def disconnect(self, interface_name):
        # It is fine to have this fail, it is only trying to cleanup before starting
        serve_pwd = self.serve_sudo_pwd()
        subprocess.run(['/usr/bin/sudo', '-S', 'ip', 'link', 'del', 'dev', interface_name],
                       stdin=serve_pwd.stdout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)

        # remove temporary dns entries, reset resolv.conf
        serve_pwd = self.serve_sudo_pwd()
        subprocess.run(
            ['/usr/bin/sudo', '-S', 'resolvectl', 'revert', interface_name],
            stdin=serve_pwd.stdout,
            check=False
        )

    def _get_wg_status(self):
        if Path('/usr/bin/sudo').exists():
            serve_pwd = self.serve_sudo_pwd()
            p = subprocess.Popen(['/usr/bin/sudo', '-S', str(WG_PATH), 'show', 'all', 'dump'],
                                 stdin=serve_pwd.stdout,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 )
            p.wait()
            if p.returncode != 0:
                print('Failed to run `wg show all dump`:')
                print(p.stdout.read().decode().strip())
                print(p.stderr.read().decode().strip())
                return []
            lines = p.stdout.read().decode().strip().splitlines()
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
