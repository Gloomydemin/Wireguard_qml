# Changements du projet & carte des fonctions

Dernière mise à jour : 2026-02-12

Ce document décrit les changements récents et liste les fonctions ajoutées ou modifiées.
Remarque : lors des mises à jour, ne réécrivez pas le document en entier ; ajoutez les nouvelles modifications en conservant la structure ci‑dessous.

## Résumé des changements
- Optimisation de la vérification des clés : un seul scan du répertoire (moins de sudo, liste des profils plus rapide).
- L’import ZIP parse les configs directement depuis l’archive (sans fichiers temporaires), plus rapide.
- Support complet des hooks : PreUp/PostUp/PreDown/PostDown avec validation safe‑mode.
- Hooks ignorés à l’import ; avertissement avant exécution.
- Le champ clé privée affiche un masque (pas de clé en clair).
- Les clés privées sont désormais stockées en fichiers root‑only dans `/home/phablet/.local/share/wireguard.sysadmin/keys` (0600), sans chiffrement par mot de passe.
- Suppression du flux/UI de re‑chiffrement et du cache des clés privées dans le GUI/backend.
- `wg_config` accepte un `PrivateKey` manquant jusqu’à la connexion ; la clé est chargée au moment du connect.
- Tests mis à jour pour le stockage via sudo et les overrides `WIREGUARD_KEY_DIR`.
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
- `list_private_keys(sudo_pwd=None)` — liste les clés avec un seul appel sudo (liste des profils plus rapide).
- Passage à des fichiers de clés root‑only dans `KEY_DIR` (par défaut `/home/phablet/.local/share/wireguard.sysadmin/keys`).
- `WIREGUARD_KEY_DIR` pour tests/overrides ; tentative `sudo -n` d’abord pour éviter le stdin si sudo est déjà validé.
- L’ancien stockage chiffré est conservé en lecture seule pour la migration.

### `src/pyaes.py` (nouveau)
- Implémentation AES‑CTR en Python pur, utilisée par `secrets_store`.

### `src/wg_config.py` (nouveau)
- `build_config(profile, private_key)` — génère un texte de configuration compatible wg‑quick.
- `build_config(profile, private_key=None)` — omet `PrivateKey` si absent.

### `src/vpn.py` (modifié)
- `Vpn.set_pwd(sudo_pwd)` — réinitialise le cache de clés en mémoire.
- `Vpn._load_profiles()` — déclenche la migration des secrets si nécessaire et réutilise un seul scan des clés.
- `Vpn._write_profile()` — retire `private_key` avant d’écrire `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data, existing_keys=None)` — migre l’ancienne clé vers le stockage chiffré, avec cache optionnel.
- `Vpn._get_private_key_status(profile_name, data=None)` — retourne `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — wrapper qui retourne uniquement la clé.
- `Vpn._connect(profile_name, use_kmod)` — gère explicitement mot de passe manquant/faux.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **signature changée** : ajout de `pre_up`.
  - stockage de la clé en mémoire chiffrée au lieu de `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — parse et stocke `PreUp`.
- `Vpn.import_conf(...)` — import ZIP en mémoire (pas de fichiers temporaires).
- `Vpn._parse_wireguard_conf_lines(...)` — renvoie `pre_up` en dernier élément.
- `Vpn.export_confs_zip()` — exporte `PreUp` et utilise la clé déchiffrée.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — re‑chiffre toutes les clés stockées.
- `Vpn.delete_profile(profile)` — supprime le secret lors de la suppression du profil.
- `Vpn.list_profiles()` — utilise une liste de clés (liste plus rapide).
- `Vpn.get_profile()` / `Vpn.list_profiles()` — `has_private_key` résolu via un seul scan.
- `Vpn.rekey_secrets(...)` — indique maintenant que le re‑chiffrement n’est pas supporté.
- `Vpn.get_profile()` / `Vpn.list_profiles()` — n’exposent plus `private_key`.
- `_connect(...)` — charge la clé à la demande avant la connexion.
- `Vpn.save_profile(...)` — signature étendue avec `post_up`, `pre_down`, `post_down`.
- `import_conf*()` — hooks ignorés à l’import.
- `parse_wireguard_conf*()` — parse `PostUp/PreDown/PostDown`.
- `export_confs_zip()` — exporte `PostUp/PreDown/PostDown`.

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
- Validation safe‑mode des hooks + vérification de disponibilité des binaires.
- `PostUp` exécuté après interface/routage/DNS.
- `PreDown`/`PostDown` exécutés au disconnect.

### `src/daemon.py` (modifié)
- Lit le mot de passe sudo depuis stdin.
- `bring_up_interface(interface_name, sudo_pwd)` utilise stdin pour sudo.
- Détection de la route par défaut via `ip route` (IPv4/IPv6).

### `qml/Main.qml` (modifié)
- Expose `settings` via alias, ajout de `canUseKmod` global.

### `qml/pages/ProfilePage.qml` (modifié)
- Ajout des champs `PreUp/PostUp/PreDown/PostDown` et sauvegarde.
- Le champ clé privée affiche un masque si une clé existe.

### `qml/pages/PickProfilePage.qml` (modifié)
- Utilise les réglages globaux du backend et un indicateur coloré.
- Transmet `pre_up` à l’éditeur de profil.
- Avertit avant exécution des hooks et transmet tous les champs.

### `qml/pages/QrScanPage.qml` (modifié)
- Nettoie les images QR temporaires après décodage.

### `qml/pages/SettingsPage.qml` (modifié)
- Ajout du dialogue de re‑chiffrement (`rekey_secrets`).
- Initialise l’état backend via `root.pwd`.
- Suppression du dialogue de re‑chiffrement (stockage root‑only).

### Tests & CI (nouveau)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`
- Tests compatibles avec `WIREGUARD_KEY_DIR` et ignorés sans identifiants sudo.
- Tests de parsing mis à jour pour PostUp/PreDown/PostDown.

## Codes d’erreur du stockage secret
- `NO_PASSWORD` — aucun mot de passe fourni.
- `MISSING` — fichier secret absent.
- `BAD_PASSWORD` — HMAC invalide (mot de passe incorrect).
- `CORRUPT` — fichier secret corrompu.
- `DECRYPT_FAILED` — échec du déchiffrement.
