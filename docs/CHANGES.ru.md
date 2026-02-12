# Изменения проекта и список функций

Последнее обновление: 2026-02-12

Этот документ фиксирует недавние изменения и перечисляет функции, которые были добавлены или изменены.
Примечание: при обновлении не переписывайте документ целиком — добавляйте новые изменения, сохраняя структуру ниже.

## Сводка изменений
- Оптимизирована проверка наличия ключей: один скан каталога (меньше sudo, быстрее список профилей).
- Импорт ZIP теперь парсит конфиги прямо из архива (без временных файлов), быстрее импорт.
- Добавлены хуки PreUp/PostUp/PreDown/PostDown с safe‑валидацией.
- Хуки игнорируются при импорте; перед запуском показывается предупреждение.
- В поле приватного ключа показывается маска (ключ не раскрывается).
- Приватные ключи теперь хранятся как root‑only файлы в `/home/phablet/.local/share/wireguard.sysadmin/keys` (0600), без парольного шифрования.
- Удалено перешифрование и кеширование приватных ключей в GUI/бекенде.
- `wg_config` допускает отсутствие `PrivateKey` до подключения; ключ подгружается при connect.
- Тесты обновлены под sudo‑хранилище ключей и `WIREGUARD_KEY_DIR`.
- Шифрованное хранение приватных ключей с использованием **sudo‑пароля** (без внешнего secret‑сервиса).
- Перешифрование всех ключей при смене пароля.
- Поддержка **PreUp** (импорт/экспорт, поле в UI и выполнение до поднятия интерфейса).
- Исправления IPv6‑маршрутизации для исключения endpoint, AllowedIPs, дополнительных маршрутов и маршрута по умолчанию.
- Очистка временных QR‑кадров после декодирования.
- Визуальный индикатор backend‑бейджа (цветная точка).
- Быстрая загрузка списка профилей за счет кеша ключей (дешифрование только при необходимости).
- CI: минимальные тесты pytest + workflow GitHub Actions.

## Изменения функций (по файлам)

### `src/secrets_store.py` (новый)
- `available()` — всегда true (локальное хранилище).
- `secret_exists(profile_name)` — проверяет, есть ли зашифрованный секрет.
- `set_private_key(profile_name, private_key, password)` — шифрует и сохраняет ключ (scrypt/PBKDF2 + AES‑CTR + HMAC).
- `get_private_key(profile_name, password, return_error=False)` — расшифровывает ключ, возвращает код ошибки при неудаче.
- `delete_private_key(profile_name)` — удаляет файл секрета.
- `list_private_keys(sudo_pwd=None)` — список ключей одним вызовом sudo (быстрее список профилей).
- Переключено на root‑only файлы в `KEY_DIR` (по умолчанию `/home/phablet/.local/share/wireguard.sysadmin/keys`).
- `WIREGUARD_KEY_DIR` для тестов/оверрайдов; сначала пробуется `sudo -n`, чтобы не писать пароль в stdin при кешированных кредах.
- Legacy‑шифрованное хранилище оставлено только для миграции.

### `src/pyaes.py` (новый)
- Реализация AES‑CTR на чистом Python, используется `secrets_store`.

### `src/wg_config.py` (новый)
- `build_config(profile, private_key)` — строит текст конфигурации, совместимый с wg‑quick.
- `build_config(profile, private_key=None)` — пропускает `PrivateKey`, если ключ не задан.

### `src/vpn.py` (изменен)
- `Vpn.set_pwd(sudo_pwd)` — сбрасывает кеш ключей в памяти.
- `Vpn._load_profiles()` — запускает миграцию секретов (если нужно) и использует один скан ключей.
- `Vpn._write_profile()` — удаляет `private_key` перед записью `profile.json`.
- `Vpn._migrate_profile_secret(profile_name, data, existing_keys=None)` — переносит legacy‑ключ в зашифрованное хранилище, опционально с кешем ключей.
- `Vpn._get_private_key_status(profile_name, data=None)` — возвращает `(key, error_code)`.
- `Vpn._get_private_key(profile_name, data=None)` — обертка, возвращает только ключ.
- `Vpn._connect(profile_name, use_kmod)` — явно обрабатывает отсутствие/ошибку пароля.
- `Vpn.save_profile(profile_name, ip_address, private_key, interface_name, extra_routes, dns_servers, pre_up, peers)`
  - **сигнатура изменена**: добавлен `pre_up`.
  - сохраняет ключ в зашифрованном хранилище вместо `profile.json`.
- `Vpn.import_conf(...) / Vpn.import_conf_text(...)` — парсят и сохраняют `PreUp`.
- `Vpn.import_conf(...)` — ZIP‑импорт парсит конфиги в памяти (без временных файлов).
- `Vpn._parse_wireguard_conf_lines(...)` — возвращает `pre_up` как последний элемент кортежа.
- `Vpn.export_confs_zip()` — экспортирует `PreUp` и использует расшифрованный ключ.
- `Vpn.rekey_secrets(old_pwd, new_pwd)` — перешифровывает все сохраненные ключи.
- `Vpn.delete_profile(profile)` — удаляет секрет при удалении профиля.
- `Vpn.list_profiles()` — использует список ключей (быстрее список).
- `Vpn.get_profile()` / `Vpn.list_profiles()` — `has_private_key` вычисляется из одного скана ключей.
- `Vpn.rekey_secrets(...)` — теперь сообщает, что перешифрование не поддерживается.
- `Vpn.get_profile()` / `Vpn.list_profiles()` — больше не отдают `private_key`.
- `_connect(...)` — подгружает ключ непосредственно перед подключением.
- `Vpn.save_profile(...)` — расширена сигнатура: `post_up`, `pre_down`, `post_down`.
- `import_conf*()` — игнорируют хуки при импорте.
- `parse_wireguard_conf*()` — парсят `PostUp/PreDown/PostDown`.
- `export_confs_zip()` — экспортирует `PostUp/PreDown/PostDown`.

### `src/interface.py` (изменен)
- `_sudo_cmd()` / `_sudo_input()` — передача sudo‑пароля через stdin.
- `_parse_endpoint_host()` / `_resolve_endpoint_ips()` — обработка IPv4/IPv6 endpoint.
- `_get_default_route()` + `get_default_gateway_v6()` / `get_default_interface_v6()` — IPv6‑маршрут по умолчанию.
- `config_interface(...)`
  - использует временный файл конфигурации (секреты не остаются на диске).
  - поддержка IPv6‑маршрутизации.
  - выполняет `PreUp`‑команды до поднятия интерфейса.
- `disconnect(...)` — очищает IPv6‑маршруты и удаляет endpoint‑маршруты для v6.
- `_get_wg_status()` — sudo‑пароль через stdin.
- Safe‑валидация hook‑команд и проверка доступности бинарников.
- `PostUp` выполняется после интерфейса/маршрутов/DNS.
- `PreDown`/`PostDown` выполняются при отключении.

### `src/daemon.py` (изменен)
- Читает sudo‑пароль из stdin.
- `bring_up_interface(interface_name, sudo_pwd)` использует sudo‑stdin.
- Определение default‑gateway через `ip route` (IPv4/IPv6).

### `qml/Main.qml` (изменен)
- Экспортирует `settings` через alias, добавлено глобальное `canUseKmod`.

### `qml/pages/ProfilePage.qml` (изменен)
- Добавлены поля `PreUp/PostUp/PreDown/PostDown` и сохранение через `save_profile`.
- В поле приватного ключа показывается маска, если ключ есть.

### `qml/pages/PickProfilePage.qml` (изменен)
- Использует глобальную настройку backend и цветовой индикатор.
- Передает `pre_up` в редактор профиля.
- Предупреждает перед запуском хуков и передает все поля хуков в редактор.

### `qml/pages/QrScanPage.qml` (изменен)
- Очищает временные QR‑картинки после декодирования.

### `qml/pages/SettingsPage.qml` (изменен)
- Добавлен диалог перешифрования (`rekey_secrets`).
- Инициализация состояния backend через `root.pwd`.
- Удален диалог перешифрования (root‑only хранилище).

### Tests & CI (новое)
- `tests/test_secrets_store.py`
- `tests/test_vpn_parsing.py`
- `tests/test_wg_config.py`
- `.github/workflows/ci.yml`
- `pytest.ini`
- Тесты поддерживают `WIREGUARD_KEY_DIR` и пропускаются без sudo‑доступа.
- Тесты парсинга обновлены для PostUp/PreDown/PostDown.

## Коды ошибок хранилища секретов
- `NO_PASSWORD` — пароль не указан.
- `MISSING` — файл секрета не найден.
- `BAD_PASSWORD` — HMAC‑несовпадение (неверный пароль).
- `CORRUPT` — поврежденный файл секрета.
- `DECRYPT_FAILED` — ошибка расшифровки.
