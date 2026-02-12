# Wireguard for Ubuntu Touch

Fork of the original wireguard_qml adapted and maintained for Ubuntu Touch community devices.

[Translations](#translations)

## Features
- Userspace fallback (wireguard-go) when kernel module unavailable
- QR/zip/import support for .conf configs
- Extra routes and DNS per profile
- PreUp hooks (run commands before interface up)
- Root-only private key storage (0600) under `/home/phablet/.local/share/wireguard.sysadmin/keys`

## Screenshots
![Main screen](screenshots/screenshot20260210_132652130.png)
![Profile list](screenshots/screenshot20260210_132705511.png)
![Profile details](screenshots/screenshot20260210_132712196.png)

## Building & installing
Prerequisites: `clickable` 8.6+, Docker available, Ubuntu SDK 20.04 image.

```bash
clickable build --arch arm64  # for device
clickable install --arch arm64 --ssh <device-ip>
```

For emulator (x86_64): `clickable build --arch amd64`.

## Logs
Application logs live in `~/.cache/wireguard.sysadmin/` on the device. Open the Settings page and tap “View application logs” to jump there.

## Kernel module support
If your device kernel ships WireGuard module, the app will use it. Otherwise it falls back to userspace.
For adding WireGuard to a UT kernel, follow upstream instructions: https://www.wireguard.com/compilation/

## Export configs
All profiles can be exported to `/home/phablet/Downloads/wireguard.zip` (auto-increments if the file exists) via Settings → “Export tunnels to zip file”.

## PreUp (usage)
PreUp runs **before** the interface is brought up. It is useful for setup tasks (e.g., add custom routes, set firewall marks, etc.).

Usage:
1. Open a profile.
2. Fill the “PreUp command” field.
3. You can provide multiple commands separated by `;` or on new lines.

Example:
```
ip rule add fwmark 51820 table 51820
ip route add default dev wg0 table 51820
```

## Changes & function map
See `docs/CHANGES.md` for a full list of modifications and functions that were added or changed.

## ⭐ Support development
YooMoney:
https://yoomoney.ru/to/4100119470150396

Donations support open-source development.

## Maintainer
Sysadmin <bytebuddy@yandex.ru>

## License
This project is a fork of [Wireguard_qml](https://github.com/DavidVentura/Wireguard_qml) (MIT).  
Our modifications are also released under the MIT License.

Copyright (c) 2026 Sysadmin  
Copyright (c) 2021 David Ventura

## Translations
- Deutsch: [README.de.md](README.de.md)
- Français: [README.fr.md](README.fr.md)
- Nederlands: [README.nl.md](README.nl.md)
- Русский: [README.ru.md](README.ru.md)
