# Wireguard für Ubuntu Touch

Fork des ursprünglichen wireguard_qml, angepasst und gepflegt für Geräte der Ubuntu‑Touch‑Community.

## Funktionen
- Userspace‑Fallback (wireguard‑go), wenn kein Kernelmodul verfügbar ist
- QR/ZIP/Import‑Support für .conf‑Configs
- Zusätzliche Routen und DNS pro Profil
- Hooks (PreUp/PostUp/PreDown/PostDown)
- Root‑only Speicherung privater Schlüssel (0600) unter `/home/phablet/.local/share/wireguard.sysadmin/keys`
- Schnellere ZIP‑Imports und Profil‑Liste (ein Key‑Scan; weniger sudo)

## Screenshots
![Hauptbildschirm](screenshots/screenshot20260210_132652130.png)
![Profilübersicht](screenshots/screenshot20260210_132705511.png)
![Profildetails](screenshots/screenshot20260210_132712196.png)

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

## Hooks (Verwendung)
Hooks laufen als root rund um connect/disconnect:
- `PreUp` — vor Interface‑Up
- `PostUp` — nach Interface‑Up
- `PreDown` — vor Interface‑Down
- `PostDown` — nach Interface‑Down

So geht’s:
1. Profil öffnen.
2. Gewünschte Hook‑Felder ausfüllen.
3. Mehrere Befehle mit `;` trennen oder in neue Zeilen schreiben.

Hinweise:
- Safe‑Mode blockiert unsichere Befehle und Befehle, die im System fehlen.
- Hooks aus importierten Configs werden ignoriert.

Beispiel (PreUp):
```
ip rule add fwmark 51820 table 51820
ip route add default dev wg0 table 51820
```

## Änderungen & Funktionsliste
Siehe `docs/CHANGES.de.md`.

## ⭐ Entwicklung unterstützen
YooMoney:
https://yoomoney.ru/to/4100119470150396

Spenden unterstützen die Entwicklung von Open-Source-Projekten.

## Maintainer
Sysadmin <bytebuddy@yandex.ru>

## Lizenz
Dieses Projekt ist ein Fork von [Wireguard_qml](https://github.com/DavidVentura/Wireguard_qml) (MIT).  
Unsere Anpassungen stehen ebenfalls unter der MIT‑Lizenz.

Copyright (c) 2026 Sysadmin  
Copyright (c) 2021 David Ventura
