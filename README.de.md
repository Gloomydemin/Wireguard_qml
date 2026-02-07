# Wireguard für Ubuntu Touch

Fork des ursprünglichen wireguard_qml, angepasst und gepflegt für Geräte der Ubuntu‑Touch‑Community.

## Funktionen
- Userspace‑Fallback (wireguard‑go), wenn kein Kernelmodul verfügbar ist
- QR/ZIP/Import‑Support für .conf‑Configs
- Zusätzliche Routen und DNS pro Profil

## Bauen & Installieren
Voraussetzungen: `clickable` ≥ 8.6, Docker verfügbar, Ubuntu‑SDK 20.04‑Image.

```bash
clickable build --arch arm64  # für Gerät
clickable install --arch arm64 --ssh <device-ip>
```

Für Emulator (x86_64): `clickable build --arch amd64`.

## Logs
App‑Logs liegen unter `~/.cache/wireguard.sysadmin/`. Auf der Einstellungsseite „View application logs“ antippen, um dorthin zu springen.

## Kernelmodul‑Support
Ist ein WireGuard‑Kernelmodul vorhanden, wird es genutzt, sonst erfolgt Fallback auf Userspace.
Anleitungen zum Nachrüsten im UT‑Kernel: https://www.wireguard.com/compilation/

## Konfigurationen exportieren
Alle Profile lassen sich über Einstellungen → „Export tunnels to zip file“ nach `/home/phablet/Downloads/wireguard.zip` exportieren (Dateiname wird bei Kollision hochgezählt).

## Maintainer
Sysadmin <bytebuddy@yandex.ru>

## Lizenz
Dieses Projekt ist ein Fork von [Wireguard_qml](https://github.com/DavidVentura/Wireguard_qml) (MIT).  
Unsere Anpassungen stehen ebenfalls unter der MIT‑Lizenz.

Copyright (c) 2026 Sysadmin  
Copyright (c) 2021 David Ventura
