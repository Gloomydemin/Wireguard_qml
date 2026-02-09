# Project Changes & Function Map

Last updated: 2026-02-09

This document records the recent changes and lists the functions that were added or modified.

## Summary of changes
- Encrypted private key storage using the **sudo password** (no external secret service).
- Re-encryption workflow for all keys when password changes.
- **PreUp** support (import/export, UI field, and execution before interface up).
- IPv6 routing fixes for endpoint exclusion, AllowedIPs, extra routes, and default route.
- Temporary QR frame cleanup after decoding.
- Backend badge visual indicator (colored dot).
- Faster profile list loading by caching keys (decryption happens only when needed).
- CI: minimal pytest + GitHub Actions workflow.

## Function changes (by file)

### `src/secrets_store.py` (new)
- `available()` — always true (local storage).
- `secret_exists(profile_name)` — check if encrypted secret exists.
- `set_private_key(profile_name, private_key, password)` — encrypt and store key using scrypt/PBKDF2 + AES-CTR + HMAC.
- `get_private_key(profile_name, password, return_error=False)` — decrypt key, returns error code on failure.
- `delete_private_key(profile_name)` — delete encrypted secret file.

### `src/pyaes.py` (new)
- Pure‑Python AES CTR implementation used by `secrets_store`.

### `src/wg_config.py` (new)
- `build_config(profile, private_key)` — build wg‑quick compatible config text from profile + key.

### `src/vpn.py` (modified)
- `Vpn.set_pwd(sudo_pwd)` — now resets in‑memory key cache.
- `Vpn._load_profiles()` — triggers secret migration (if needed).
- `Vpn._write_profile()` — strips `private_key` before writing `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data)` — moves legacy key to encrypted storage.
- `Vpn._get_private_key_status(profile_name, data=None)` — returns `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — wrapper returning key only.
- `Vpn._connect(profile_name, use_kmod)` — now handles missing/wrong password errors explicitly.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **signature changed**: added `pre_up`.
  - stores key in encrypted storage instead of `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — now parse and save `PreUp`.
- `Vpn._parse_wireguard_conf_lines(...)` — returns `pre_up` as last tuple element.
- `Vpn.export_confs_zip()` — exports `PreUp` and uses decrypted key.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — re-encrypt all stored keys.
- `Vpn.delete_profile(profile)` — deletes encrypted secret on profile removal.
- `Vpn.list_profiles()` — uses cached keys (faster list loading).

### `src/interface.py` (modified)
- `_sudo_cmd()` / `_sudo_input()` — pass sudo password via stdin.
- `_parse_endpoint_host()` / `_resolve_endpoint_ips()` — IPv4/IPv6 endpoint handling.
- `_get_default_route()` + `get_default_gateway_v6()` / `get_default_interface_v6()` — IPv6 defaults.
- `config_interface(...)`
  - uses temporary config file (no secret left on disk).
  - adds IPv6 routing support.
  - executes `PreUp` commands before interface up.
- `disconnect(...)` — flushes IPv6 routes and cleans endpoint routes for v6.
- `_get_wg_status()` — uses stdin for sudo password.

### `src/daemon.py` (modified)
- Reads sudo password from stdin.
- `bring_up_interface(interface_name, sudo_pwd)` now uses sudo stdin.
- Default gateway detection uses `ip route` (IPv4/IPv6).

### `qml/Main.qml` (modified)
- Exposes `settings` via alias, adds `canUseKmod` global setting.

### `qml/pages/ProfilePage.qml` (modified)
- Added `PreUp` field and saved it via `save_profile`.

### `qml/pages/PickProfilePage.qml` (modified)
- Uses global backend setting and adds colored backend indicator.
- Passes `pre_up` into profile editor.

### `qml/pages/QrScanPage.qml` (modified)
- Cleans up temporary QR images after decoding.

### `qml/pages/SettingsPage.qml` (modified)
- Added re-encrypt dialog (`rekey_secrets`).
- Uses `root.pwd` to initialize backend state.

### Tests & CI (new)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`

## Error codes from secret storage
- `NO_PASSWORD` — password not provided.
- `MISSING` — secret file not found.
- `BAD_PASSWORD` — HMAC mismatch (wrong password).
- `CORRUPT` — broken secret file.
- `DECRYPT_FAILED` — decryption error.
