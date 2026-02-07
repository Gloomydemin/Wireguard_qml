# Wireguard pour Ubuntu Touch

Fork du projet d’origine wireguard_qml, adapté et maintenu pour les appareils de la communauté Ubuntu Touch.

## Fonctionnalités
- Bascule en userspace (wireguard‑go) si le module noyau est indisponible
- Support QR/ZIP/import pour les configs .conf
- Routes supplémentaires et DNS par profil

## Compilation & installation
Prérequis : `clickable` ≥ 8.6, Docker disponible, image Ubuntu SDK 20.04.

```bash
clickable build --arch arm64  # pour l’appareil
clickable install --arch arm64 --ssh <ip-appareil>
```

Pour l’émulateur (x86_64) : `clickable build --arch amd64`.

## Journaux
Les journaux de l’application sont dans `~/.cache/wireguard.sysadmin/`. Dans Paramètres, touchez « View application logs » pour y accéder.

## Support du module noyau
Si le module WireGuard est présent dans le noyau de l’appareil, il sera utilisé, sinon bascule vers l’implémentation userspace.
Pour ajouter WireGuard au noyau UT : https://www.wireguard.com/compilation/

## Export des configs
Tous les profils peuvent être exportés via Paramètres → « Export tunnels to zip file » vers `/home/phablet/Downloads/wireguard.zip` (le nom est incrémenté si le fichier existe déjà).

## Mainteneur
Sysadmin <bytebuddy@yandex.ru>

## Licence
Ce projet est un fork de [Wireguard_qml](https://github.com/DavidVentura/Wireguard_qml) (MIT).  
Nos modifications sont également publiées sous licence MIT.

Copyright (c) 2026 Sysadmin  
Copyright (c) 2021 David Ventura
