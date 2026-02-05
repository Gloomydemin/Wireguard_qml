import subprocess
from pathlib import Path

def test_sudo(sudo_pwd):
        if not Path('/usr/bin/sudo').exists():
            return False

        try:
            # If cached credentials exist, don't prompt.
            if subprocess.run(['/usr/bin/sudo', '-n', 'true'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).returncode == 0:
                return True
            if sudo_pwd is None:
                return False
            # Validate provided password.
            p = subprocess.run(
                ['/usr/bin/sudo', '-S', '-p', '', 'true'],
                input=(sudo_pwd + '\n').encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            return p.returncode == 0
        except Exception:
            return False
