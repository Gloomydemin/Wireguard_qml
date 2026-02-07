# Wireguard для Ubuntu Touch

Форк оригинального wireguard_qml, адаптирован и поддерживается для устройств сообщества Ubuntu Touch.

## Возможности
- Userspace‑fallback (wireguard‑go), если нет модульной поддержки ядра
- Поддержка QR/ZIP/импорта `.conf`
- Дополнительные маршруты и DNS для каждого профиля

## Сборка и установка
Требования: `clickable` ≥ 8.6, доступен Docker, образ Ubuntu SDK 20.04.

```bash
clickable build --arch arm64  # для устройства
clickable install --arch arm64 --ssh <ip-устройства>
```

Для эмулятора (x86_64): `clickable build --arch amd64`.

## Логи
Журналы приложения находятся в `~/.cache/wireguard.sysadmin/`. В настройках нажмите «View application logs», чтобы открыть каталог.

## Поддержка модуля ядра
Если в ядре устройства есть модуль WireGuard, он будет использован, иначе включится userspace‑реализация. Добавить WireGuard в ядро UT: https://www.wireguard.com/compilation/

## Экспорт конфигураций
Все профили можно экспортировать через Настройки → «Export tunnels to zip file» в `/home/phablet/Downloads/wireguard.zip` (имя файла автоматически увеличивается, если уже существует).

## Мейнтейнер
Sysadmin <bytebuddy@yandex.ru>

## Лицензия
Проект — форк [Wireguard_qml](https://github.com/DavidVentura/Wireguard_qml) (MIT).  
Наши изменения также распространяются под лицензией MIT.

Copyright (c) 2026 Sysadmin  
Copyright (c) 2021 David Ventura
