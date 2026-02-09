# Projectwijzigingen & Functieoverzicht

Laatst bijgewerkt: 2026-02-09

Dit document beschrijft de recente wijzigingen en somt functies op die zijn toegevoegd of gewijzigd.

## Samenvatting van wijzigingen
- Versleutelde opslag van private keys met het **sudo‑wachtwoord** (geen externe secret service).
- Her‑encryptieworkflow voor alle sleutels bij wachtwoordwijziging.
- **PreUp**‑ondersteuning (import/export, UI‑veld en uitvoering vóór interface‑up).
- IPv6‑routingfixes voor endpoint‑uitsluiting, AllowedIPs, extra routes en default route.
- Opruimen van tijdelijke QR‑frames na het decoderen.
- Backend‑badge met visuele indicator (gekleurde stip).
- Snellere profiel‑lijst door key‑cache (ontsleuteling alleen wanneer nodig).
- CI: minimale pytest‑tests + GitHub Actions‑workflow.

## Functiewijzigingen (per bestand)

### `src/secrets_store.py` (nieuw)
- `available()` — altijd true (lokale opslag).
- `secret_exists(profile_name)` — controleert of er een versleuteld secret bestaat.
- `set_private_key(profile_name, private_key, password)` — versleutelt en slaat de sleutel op (scrypt/PBKDF2 + AES‑CTR + HMAC).
- `get_private_key(profile_name, password, return_error=False)` — ontsleutelt de sleutel, geeft foutcode bij mislukking.
- `delete_private_key(profile_name)` — verwijdert het versleutelde secret‑bestand.

### `src/pyaes.py` (nieuw)
- Pure‑Python AES‑CTR‑implementatie, gebruikt door `secrets_store`.

### `src/wg_config.py` (nieuw)
- `build_config(profile, private_key)` — bouwt wg‑quick‑compatibele configtekst uit profiel + sleutel.

### `src/vpn.py` (gewijzigd)
- `Vpn.set_pwd(sudo_pwd)` — reset de in‑memory key‑cache.
- `Vpn._load_profiles()` — triggert secret‑migratie (indien nodig).
- `Vpn._write_profile()` — verwijdert `private_key` vóór het schrijven van `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data)` — verplaatst legacy‑sleutel naar versleutelde opslag.
- `Vpn._get_private_key_status(profile_name, data=None)` — retourneert `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — wrapper die alleen de sleutel teruggeeft.
- `Vpn._connect(profile_name, use_kmod)` — behandelt ontbrekend/verkeerd wachtwoord expliciet.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **signatuur gewijzigd**: `pre_up` toegevoegd.
  - slaat de sleutel op in versleutelde opslag in plaats van in `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — parseert en slaat `PreUp` op.
- `Vpn._parse_wireguard_conf_lines(...)` — retourneert `pre_up` als laatste tuple‑element.
- `Vpn.export_confs_zip()` — exporteert `PreUp` en gebruikt de ontsleutelde sleutel.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — her‑encrypteert alle opgeslagen sleutels.
- `Vpn.delete_profile(profile)` — verwijdert het secret bij profielverwijdering.
- `Vpn.list_profiles()` — gebruikt key‑cache (snellere lijst).

### `src/interface.py` (gewijzigd)
- `_sudo_cmd()` / `_sudo_input()` — sudo‑wachtwoord via stdin.
- `_parse_endpoint_host()` / `_resolve_endpoint_ips()` — IPv4/IPv6‑endpoint‑afhandeling.
- `_get_default_route()` + `get_default_gateway_v6()` / `get_default_interface_v6()` — IPv6‑defaults.
- `config_interface(...)`
  - gebruikt tijdelijk configbestand (geen secret op schijf).
  - IPv6‑routing‑support.
  - voert `PreUp`‑commando’s uit vóór interface‑up.
- `disconnect(...)` — wist IPv6‑routes en verwijdert endpoint‑routes voor v6.
- `_get_wg_status()` — sudo‑wachtwoord via stdin.

### `src/daemon.py` (gewijzigd)
- Leest sudo‑wachtwoord van stdin.
- `bring_up_interface(interface_name, sudo_pwd)` gebruikt sudo‑stdin.
- Default‑gateway‑detectie via `ip route` (IPv4/IPv6).

### `qml/Main.qml` (gewijzigd)
- Stelt `settings` beschikbaar via alias, globale `canUseKmod` toegevoegd.

### `qml/pages/ProfilePage.qml` (gewijzigd)
- `PreUp`‑veld toegevoegd en opgeslagen via `save_profile`.

### `qml/pages/PickProfilePage.qml` (gewijzigd)
- Gebruikt globale backend‑instelling en voegt een gekleurde backend‑indicator toe.
- Geeft `pre_up` door aan de profiel‑editor.

### `qml/pages/QrScanPage.qml` (gewijzigd)
- Ruimt tijdelijke QR‑afbeeldingen op na decoderen.

### `qml/pages/SettingsPage.qml` (gewijzigd)
- Re‑encrypt‑dialog (`rekey_secrets`) toegevoegd.
- Initialiseert backend‑state via `root.pwd`.

### Tests & CI (nieuw)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`

## Foutcodes uit secret‑opslag
- `NO_PASSWORD` — wachtwoord niet opgegeven.
- `MISSING` — secret‑bestand niet gevonden.
- `BAD_PASSWORD` — HMAC‑mismatch (verkeerd wachtwoord).
- `CORRUPT` — beschadigd secret‑bestand.
- `DECRYPT_FAILED` — ontsleutelingsfout.
