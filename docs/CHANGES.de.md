# Projektänderungen & Funktionsübersicht

Zuletzt aktualisiert: 2026-02-10

Dieses Dokument beschreibt die jüngsten Änderungen und listet Funktionen auf, die hinzugefügt oder geändert wurden.

## Zusammenfassung der Änderungen
- Verschlüsselte Speicherung privater Schlüssel mit dem **sudo‑Passwort** (kein externer Secret‑Dienst).
- Re‑Encryption‑Workflow für alle Schlüssel bei Passwortänderung.
- **PreUp**‑Unterstützung (Import/Export, UI‑Feld und Ausführung vor Interface‑Up).
- IPv6‑Routing‑Fixes für Endpoint‑Exclusion, AllowedIPs, Extra‑Routen und Default‑Route.
- Aufräumen temporärer QR‑Frames nach dem Decoding.
- Backend‑Badge mit visuellem Indikator (farbiger Punkt).
- Schnellere Profil‑Liste durch Key‑Cache (Entschlüsselung nur bei Bedarf).
- CI: minimale pytest‑Tests + GitHub Actions.

## Funktionsänderungen (nach Datei)

### `src/secrets_store.py` (neu)
- `available()` — immer true (lokaler Speicher).
- `secret_exists(profile_name)` — prüft, ob ein verschlüsseltes Secret existiert.
- `set_private_key(profile_name, private_key, password)` — verschlüsselt und speichert den Key (scrypt/PBKDF2 + AES‑CTR + HMAC).
- `get_private_key(profile_name, password, return_error=False)` — entschlüsselt den Key, liefert Fehlercode bei Fehlschlag.
- `delete_private_key(profile_name)` — löscht die verschlüsselte Secret‑Datei.

### `src/pyaes.py` (neu)
- Reine Python‑Implementierung von AES‑CTR, genutzt von `secrets_store`.

### `src/wg_config.py` (neu)
- `build_config(profile, private_key)` — erzeugt wg‑quick‑kompatiblen Config‑Text.

### `src/vpn.py` (geändert)
- `Vpn.set_pwd(sudo_pwd)` — setzt den In‑Memory‑Key‑Cache zurück.
- `Vpn._load_profiles()` — triggert Secret‑Migration (falls nötig).
- `Vpn._write_profile()` — entfernt `private_key` vor dem Schreiben von `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data)` — migriert Legacy‑Key in verschlüsselten Speicher.
- `Vpn._get_private_key_status(profile_name, data=None)` — liefert `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — Wrapper, liefert nur den Key.
- `Vpn._connect(profile_name, use_kmod)` — behandelt fehlendes/falsches Passwort explizit.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **Signatur geändert**: `pre_up` hinzugefügt.
  - speichert Key im verschlüsselten Speicher statt in `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — parst und speichert `PreUp`.
- `Vpn._parse_wireguard_conf_lines(...)` — gibt `pre_up` als letztes Tupel‑Element zurück.
- `Vpn.export_confs_zip()` — exportiert `PreUp` und nutzt entschlüsselten Key.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — re‑encryptet alle gespeicherten Keys.
- `Vpn.delete_profile(profile)` — löscht Secret beim Entfernen des Profils.
- `Vpn.list_profiles()` — nutzt Key‑Cache (schnellere Liste).

### `src/interface.py` (geändert)
- `_sudo_cmd()` / `_sudo_input()` — sudo‑Passwort via stdin.
- `_parse_endpoint_host()` / `_resolve_endpoint_ips()` — IPv4/IPv6‑Endpoint‑Handling.
- `_get_default_route()` + `get_default_gateway_v6()` / `get_default_interface_v6()` — IPv6‑Defaults.
- `config_interface(...)`
  - nutzt temporäre Config‑Datei (kein Secret auf Disk).
  - IPv6‑Routing‑Support.
  - führt `PreUp`‑Commands vor Interface‑Up aus.
- `disconnect(...)` — IPv6‑Routes flushen und Endpoint‑Routes für v6 entfernen.
- `_get_wg_status()` — sudo‑Passwort via stdin.

### `src/daemon.py` (geändert)
- Liest sudo‑Passwort von stdin.
- `bring_up_interface(interface_name, sudo_pwd)` nutzt sudo‑stdin.
- Default‑Gateway‑Ermittlung per `ip route` (IPv4/IPv6).

### `qml/Main.qml` (geändert)
- Stellt `settings` per Alias bereit, globales `canUseKmod` hinzugefügt.

### `qml/pages/ProfilePage.qml` (geändert)
- `PreUp`‑Feld hinzugefügt und in `save_profile` gespeichert.

### `qml/pages/PickProfilePage.qml` (geändert)
- Nutzt globale Backend‑Einstellung und farbigen Backend‑Indikator.
- Übergibt `pre_up` an den Profileditor.

### `qml/pages/QrScanPage.qml` (geändert)
- Löscht temporäre QR‑Bilder nach dem Decoding.

### `qml/pages/SettingsPage.qml` (geändert)
- Re‑encrypt‑Dialog (`rekey_secrets`) hinzugefügt.
- Initialisiert Backend‑State via `root.pwd`.

### Tests & CI (neu)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`

## Fehlercodes aus dem Secret‑Speicher
- `NO_PASSWORD` — kein Passwort angegeben.
- `MISSING` — Secret‑Datei fehlt.
- `BAD_PASSWORD` — HMAC‑Mismatch (falsches Passwort).
- `CORRUPT` — beschädigte Secret‑Datei.
- `DECRYPT_FAILED` — Entschlüsselungsfehler.
