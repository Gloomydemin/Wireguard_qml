# Projektänderungen & Funktionsübersicht

Zuletzt aktualisiert: 2026-02-12

Dieses Dokument beschreibt die jüngsten Änderungen und listet Funktionen auf, die hinzugefügt oder geändert wurden.
Hinweis: Beim Aktualisieren das Dokument nicht komplett neu schreiben, sondern neue Änderungen hinzufügen und die Struktur unten beibehalten.

## Zusammenfassung der Änderungen
- Optimierte Schlüsselprüfung: einmaliger Scan des Key‑Verzeichnisses (weniger sudo, schnellere Profil‑Liste).
- ZIP‑Import parst Configs direkt aus dem Archiv (keine temporären Dateien) für schnellere Importe.
- Vollständige Hook‑Unterstützung: PreUp/PostUp/PreDown/PostDown mit Safe‑Validierung.
- Hooks werden beim Import ignoriert; Warn‑Dialog vor der Ausführung.
- Private‑Key‑Feld zeigt eine Maskierung (kein Klartext).
- Private Schlüssel werden jetzt als root‑only Dateien in `/home/phablet/.local/share/wireguard.sysadmin/keys` (0600) gespeichert, ohne passwortbasierte Verschlüsselung.
- Re‑Encryption‑Flow/UI und Private‑Key‑Cache in GUI/Backend entfernt.
- `wg_config` erlaubt fehlendes `PrivateKey` bis zum Connect; der Key wird erst beim Connect geladen.
- Tests für sudo‑basierten Key‑Speicher und `WIREGUARD_KEY_DIR` aktualisiert.
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
- `list_private_keys(sudo_pwd=None)` — listet gespeicherte Schlüssel mit einem sudo‑Aufruf (schnellere Profil‑Liste).
- Umgestellt auf root‑only Key‑Dateien in `KEY_DIR` (Standard: `/home/phablet/.local/share/wireguard.sysadmin/keys`).
- `WIREGUARD_KEY_DIR` für Tests/Overrides; zuerst `sudo -n`, um Passwort‑stdin bei gecachten Credentials zu vermeiden.
- Legacy‑verschlüsselter Store bleibt nur für Migration.

### `src/pyaes.py` (neu)
- Reine Python‑Implementierung von AES‑CTR, genutzt von `secrets_store`.

### `src/wg_config.py` (neu)
- `build_config(profile, private_key)` — erzeugt wg‑quick‑kompatiblen Config‑Text.
- `build_config(profile, private_key=None)` — lässt `PrivateKey` weg, wenn nicht vorhanden.

### `src/vpn.py` (geändert)
- `Vpn.set_pwd(sudo_pwd)` — setzt den In‑Memory‑Key‑Cache zurück.
- `Vpn._load_profiles()` — triggert Secret‑Migration (falls nötig) und nutzt einen Key‑Scan.
- `Vpn._write_profile()` — entfernt `private_key` vor dem Schreiben von `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data, existing_keys=None)` — migriert Legacy‑Key in verschlüsselten Speicher, optional mit Key‑Cache.
- `Vpn._get_private_key_status(profile_name, data=None)` — liefert `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — Wrapper, liefert nur den Key.
- `Vpn._connect(profile_name, use_kmod)` — behandelt fehlendes/falsches Passwort explizit.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **Signatur geändert**: `pre_up` hinzugefügt.
  - speichert Key im verschlüsselten Speicher statt in `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — parst und speichert `PreUp`.
- `Vpn.import_conf(...)` — ZIP‑Import parst Configs im Speicher (keine temporären Dateien).
- `Vpn._parse_wireguard_conf_lines(...)` — gibt `pre_up` als letztes Tupel‑Element zurück.
- `Vpn.export_confs_zip()` — exportiert `PreUp` und nutzt entschlüsselten Key.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — re‑encryptet alle gespeicherten Keys.
- `Vpn.delete_profile(profile)` — löscht Secret beim Entfernen des Profils.
- `Vpn.list_profiles()` — nutzt eine Key‑Liste (schnellere Liste).
- `Vpn.get_profile()` / `Vpn.list_profiles()` — `has_private_key` aus einem Key‑Scan.
- `Vpn.rekey_secrets(...)` — meldet jetzt „nicht unterstützt“ bei root‑only Storage.
- `Vpn.get_profile()` / `Vpn.list_profiles()` — geben keinen `private_key` mehr aus.
- `_connect(...)` — lädt den Key bei Bedarf vor dem Verbinden.
- `Vpn.save_profile(...)` — Signatur erweitert um `post_up`, `pre_down`, `post_down`.
- `import_conf*()` — Hooks werden beim Import ignoriert.
- `parse_wireguard_conf*()` — parst `PostUp/PreDown/PostDown`.
- `export_confs_zip()` — exportiert `PostUp/PreDown/PostDown`.

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
- Safe‑Validierung der Hook‑Kommandos und Verfügbarkeitsprüfung.
- `PostUp` nach Interface/Routing/DNS.
- `PreDown`/`PostDown` beim Disconnect.

### `src/daemon.py` (geändert)
- Liest sudo‑Passwort von stdin.
- `bring_up_interface(interface_name, sudo_pwd)` nutzt sudo‑stdin.
- Default‑Gateway‑Ermittlung per `ip route` (IPv4/IPv6).

### `qml/Main.qml` (geändert)
- Stellt `settings` per Alias bereit, globales `canUseKmod` hinzugefügt.

### `qml/pages/ProfilePage.qml` (geändert)
- `PreUp/PostUp/PreDown/PostDown`‑Felder hinzugefügt und gespeichert.
- Private‑Key‑Feld zeigt Maskierung, wenn Key vorhanden ist.

### `qml/pages/PickProfilePage.qml` (geändert)
- Nutzt globale Backend‑Einstellung und farbigen Backend‑Indikator.
- Übergibt `pre_up` an den Profileditor.
- Warnt vor Hook‑Ausführung und übergibt alle Hook‑Felder.

### `qml/pages/QrScanPage.qml` (geändert)
- Löscht temporäre QR‑Bilder nach dem Decoding.

### `qml/pages/SettingsPage.qml` (geändert)
- Re‑encrypt‑Dialog (`rekey_secrets`) hinzugefügt.
- Initialisiert Backend‑State via `root.pwd`.
- Re‑encrypt‑Dialog entfernt (root‑only Storage).

### Tests & CI (neu)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`
- Tests unterstützen `WIREGUARD_KEY_DIR` und werden ohne sudo‑Zugang übersprungen.
- Parsing‑Tests erweitert für PostUp/PreDown/PostDown.

## Fehlercodes aus dem Secret‑Speicher
- `NO_PASSWORD` — kein Passwort angegeben.
- `MISSING` — Secret‑Datei fehlt.
- `BAD_PASSWORD` — HMAC‑Mismatch (falsches Passwort).
- `CORRUPT` — beschädigte Secret‑Datei.
- `DECRYPT_FAILED` — Entschlüsselungsfehler.
