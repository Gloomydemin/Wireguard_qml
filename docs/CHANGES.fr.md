# Changements du projet & carte des fonctions

Dernière mise à jour : 2026-02-10

Ce document décrit les changements récents et liste les fonctions ajoutées ou modifiées.

## Résumé des changements
- Stockage chiffré des clés privées avec le **mot de passe sudo** (pas de service secret externe).
- Flux de re‑chiffrement de toutes les clés lors d’un changement de mot de passe.
- Support **PreUp** (import/export, champ UI et exécution avant l’interface up).
- Corrections IPv6 pour l’exclusion d’endpoint, AllowedIPs, routes supplémentaires et route par défaut.
- Nettoyage des images QR temporaires après décodage.
- Badge backend avec indicateur visuel (point coloré).
- Chargement plus rapide des profils via cache de clés (décryptage à la demande).
- CI : pytest minimal + GitHub Actions.

## Fonctions modifiées (par fichier)

### `src/secrets_store.py` (nouveau)
- `available()` — toujours true (stockage local).
- `secret_exists(profile_name)` — vérifie l’existence d’un secret chiffré.
- `set_private_key(profile_name, private_key, password)` — chiffre et stocke la clé (scrypt/PBKDF2 + AES‑CTR + HMAC).
- `get_private_key(profile_name, password, return_error=False)` — déchiffre la clé, retourne un code d’erreur si échec.
- `delete_private_key(profile_name)` — supprime le fichier secret chiffré.

### `src/pyaes.py` (nouveau)
- Implémentation AES‑CTR en Python pur, utilisée par `secrets_store`.

### `src/wg_config.py` (nouveau)
- `build_config(profile, private_key)` — génère un texte de configuration compatible wg‑quick.

### `src/vpn.py` (modifié)
- `Vpn.set_pwd(sudo_pwd)` — réinitialise le cache de clés en mémoire.
- `Vpn._load_profiles()` — déclenche la migration des secrets si nécessaire.
- `Vpn._write_profile()` — retire `private_key` avant d’écrire `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data)` — migre l’ancienne clé vers le stockage chiffré.
- `Vpn._get_private_key_status(profile_name, data=None)` — retourne `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — wrapper qui retourne uniquement la clé.
- `Vpn._connect(profile_name, use_kmod)` — gère explicitement mot de passe manquant/faux.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **signature changée** : ajout de `pre_up`.
  - stockage de la clé en mémoire chiffrée au lieu de `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — parse et stocke `PreUp`.
- `Vpn._parse_wireguard_conf_lines(...)` — renvoie `pre_up` en dernier élément.
- `Vpn.export_confs_zip()` — exporte `PreUp` et utilise la clé déchiffrée.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — re‑chiffre toutes les clés stockées.
- `Vpn.delete_profile(profile)` — supprime le secret lors de la suppression du profil.
- `Vpn.list_profiles()` — utilise le cache de clés (liste plus rapide).

### `src/interface.py` (modifié)
- `_sudo_cmd()` / `_sudo_input()` — mot de passe sudo via stdin.
- `_parse_endpoint_host()` / `_resolve_endpoint_ips()` — prise en charge IPv4/IPv6.
- `_get_default_route()` + `get_default_gateway_v6()` / `get_default_interface_v6()` — defaults IPv6.
- `config_interface(...)`
  - utilise un fichier config temporaire (pas de secret sur disque).
  - support du routage IPv6.
  - exécute les commandes `PreUp` avant interface up.
- `disconnect(...)` — purge des routes IPv6 et suppression des routes d’endpoint v6.
- `_get_wg_status()` — mot de passe sudo via stdin.

### `src/daemon.py` (modifié)
- Lit le mot de passe sudo depuis stdin.
- `bring_up_interface(interface_name, sudo_pwd)` utilise stdin pour sudo.
- Détection de la route par défaut via `ip route` (IPv4/IPv6).

### `qml/Main.qml` (modifié)
- Expose `settings` via alias, ajout de `canUseKmod` global.

### `qml/pages/ProfilePage.qml` (modifié)
- Ajout du champ `PreUp` et sauvegarde via `save_profile`.

### `qml/pages/PickProfilePage.qml` (modifié)
- Utilise les réglages globaux du backend et un indicateur coloré.
- Transmet `pre_up` à l’éditeur de profil.

### `qml/pages/QrScanPage.qml` (modifié)
- Nettoie les images QR temporaires après décodage.

### `qml/pages/SettingsPage.qml` (modifié)
- Ajout du dialogue de re‑chiffrement (`rekey_secrets`).
- Initialise l’état backend via `root.pwd`.

### Tests & CI (nouveau)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`

## Codes d’erreur du stockage secret
- `NO_PASSWORD` — aucun mot de passe fourni.
- `MISSING` — fichier secret absent.
- `BAD_PASSWORD` — HMAC invalide (mot de passe incorrect).
- `CORRUPT` — fichier secret corrompu.
- `DECRYPT_FAILED` — échec du déchiffrement.
