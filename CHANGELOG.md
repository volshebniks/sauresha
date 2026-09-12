# Changelog

Все заметные изменения проекта SauresHA документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект следует [Semantic Versioning](https://semver.org/lang/ru/).

## [2.1.1] - 2026-09-12

### Added
- Для многотарифных электросчётчиков создаются отдельные числовые сенсоры T1..Tn (кВт·ч)

### Fixed
- Ошибка добавления сенсора с значением вида `4803.08/1774.58`: комбинированная строка тарифов больше не публикуется с единицей `kWh`

## [2.1.0] - 2026-09-09

### Changed
- Docstring’и функций и классов переведены на русский язык
- Сущности обновляют состояние через `_attr_*` (совместимость с `cached_property` в новых версиях Home Assistant)

### Fixed
- Исправлен старт интеграции: убрана пауза 10 секунд между объектами при первом опросе (устраняет `CancelledError` / ошибку setup entry)

## [2.0.0] - 2026-09-09

### Added
- DataUpdateCoordinator: один опрос API Saures на все сущности
- Группировка sensor / binary_sensor / switch в устройство контроллера в реестре Home Assistant
- Корректные `device_class` и единицы измерения (вода, газ, энергия, температура)
- Unload / reload интеграции при изменении настроек
- Поля `iot_class: cloud_polling` и `integration_type: hub` в манифесте

### Changed
- Обновление под Home Assistant 2025.1+ / 2026.x
- Сущности переведены на SensorEntity / BinarySensorEntity / SwitchEntity + CoordinatorEntity
- Обновлены `manifest.json` / `hacs.json`
- **Требуется Home Assistant >= 2025.1.0**

### Fixed
- OptionsFlow для совместимости с HA 2025.12+
- Ошибки API: auth lock, имя неизвестных контроллеров, URL команды управления краном
- Устойчивость к обрывам связи с api.saures.ru (`Connection reset by peer`): User-Agent `HTTPie`, IPv4-сессия, повтор запросов

## [1.0.0] - 2022-11-09

### Added
- Управление кранами (switch)
- Настройка через GUI (config flow)

### Changed
- Полностью переработан код для минимизации обращений к серверу Saures
- Внедрён асинхронный режим работы

## [0.6.0] - 2021-03-04

### Changed
- Значительно изменён механизм настройки
- Можно задавать свои имена
- Поддержка ссылок на `!secret` в настройках
- Добавлена версия в `manifest`

## [0.5.0] - 2020-10-01

### Changed
- Существенно сокращено количество обращений к серверу Saures для предотвращения блокировки
- Рекомендуемый `scan_interval`: 30 минут

## [0.3.8] - 2020-02-04

### Changed
- Возвращены синхронные вызовы

## [0.3.5] - 2020-01-31

### Changed
- Уменьшено количество вызовов API
- Ускорена первоначальная инициализация модуля
- Переход на асинхронные методы

### Fixed
- Ошибка с заданием своего `scan_interval`
- Ошибка, связанная с наличием русских букв в серийных номерах

## [0.3.0] - 2020-01-29

### Added
- Переход на новое клиентское API
- Необязательная настройка `scan_interval` для sensor (по умолчанию 10 минут)
- Новые атрибуты у сенсоров

[Unreleased]: https://github.com/volshebniks/sauresha/compare/2.1.1...HEAD
[2.1.1]: https://github.com/volshebniks/sauresha/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/volshebniks/sauresha/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/volshebniks/sauresha/compare/v.1.0.4...2.0.0
[1.0.0]: https://github.com/volshebniks/sauresha/releases/tag/v.1.0.0
[0.6.0]: https://github.com/volshebniks/sauresha/releases/tag/v0.6.0
[0.5.0]: https://github.com/volshebniks/sauresha/releases/tag/v0.5
[0.3.8]: https://github.com/volshebniks/sauresha/releases/tag/v0.3.8
[0.3.5]: https://github.com/volshebniks/sauresha/releases/tag/v0.3.5
[0.3.0]: https://github.com/volshebniks/sauresha/releases/tag/v0.3

