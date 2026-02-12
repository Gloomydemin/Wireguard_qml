# Wireguard для Ubuntu Touch

Форк оригинального wireguard_qml, адаптирован и поддерживается для устройств сообщества Ubuntu Touch.

## Возможности
- Userspace‑fallback (wireguard‑go), если нет модульной поддержки ядра
- Поддержка QR/ZIP/импорта `.conf`
- Дополнительные маршруты и DNS для каждого профиля
- Хуки (PreUp/PostUp/PreDown/PostDown)
- Хранение приватных ключей root‑only (0600) в `/home/phablet/.local/share/wireguard.sysadmin/keys`
- Быстрый импорт ZIP и загрузка списка профилей (один скан ключей; меньше sudo)

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

## Хуки (использование)
Хуки выполняются от root при подключении/отключении:
- `PreUp` — до поднятия интерфейса
- `PostUp` — после поднятия интерфейса
- `PreDown` — до выключения интерфейса
- `PostDown` — после выключения интерфейса

Как использовать:
1. Откройте профиль.
2. Заполните нужные поля хуков.
3. Несколько команд можно разделять `;` или писать на отдельных строках.

Примечания:
- Safe‑режим блокирует небезопасные команды и команды, которых нет в системе.
- Хуки из импортированных конфигов игнорируются.

Пример (PreUp):
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
