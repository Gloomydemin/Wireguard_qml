# Wireguard для Ubuntu Touch

Форк оригинального wireguard_qml, адаптирован и поддерживается для устройств сообщества Ubuntu Touch.

## Возможности
- Userspace‑fallback (wireguard‑go), если нет модульной поддержки ядра
- Поддержка QR/ZIP/импорта `.conf`
- Дополнительные маршруты и DNS для каждого профиля
- PreUp‑хуки (команды выполняются до поднятия интерфейса)
- Хранение приватных ключей root‑only (0600) в `/home/phablet/.local/share/wireguard.sysadmin/keys`

## Скриншоты
![Главный экран](screenshots/screenshot20260210_132652130.png)
![Список профилей](screenshots/screenshot20260210_132705511.png)
![Детали профиля](screenshots/screenshot20260210_132712196.png)

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

## PreUp (использование)
PreUp выполняется **до** поднятия интерфейса. Подходит для подготовительных команд (маршруты, правила и т.п.).

Как использовать:
1. Откройте профиль.
2. Заполните поле «PreUp command».
3. Несколько команд можно разделять `;` или писать на отдельных строках.

Пример:
```
ip rule add fwmark 51820 table 51820
ip route add default dev wg0 table 51820
```

## Изменения и список функций
Полный список изменений и функций: `docs/CHANGES.ru.md`.

## ⭐ Поддержать разработку
YooMoney:
https://yoomoney.ru/to/4100119470150396

Донаты идут на развитие open-source проектов.

## Мейнтейнер
Sysadmin <bytebuddy@yandex.ru>

## Лицензия
Проект — форк [Wireguard_qml](https://github.com/DavidVentura/Wireguard_qml) (MIT).  
Наши изменения также распространяются под лицензией MIT.

Copyright (c) 2026 Sysadmin  
Copyright (c) 2021 David Ventura
