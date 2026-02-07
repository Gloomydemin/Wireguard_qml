# Wireguard for Ubuntu Touch

Fork of the original wireguard_qml adapted and maintained for Ubuntu Touch community devices.

[Translations](#translations)

## Features
- Userspace fallback (wireguard-go) when kernel module unavailable
- QR/zip/import support for .conf configs
- Extra routes and DNS per profile

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
