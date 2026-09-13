# SauresHA
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/volshebniks/sauresha)](https://github.com/volshebniks/sauresha/releases)
![GitHub Release Date](https://img.shields.io/github/release-date/volshebniks/sauresha)
[![GitHub](https://img.shields.io/github/license/volshebniks/sauresha)](LICENSE)

[![Maintenance](https://img.shields.io/badge/Maintained%3F-Yes-brightgreen.svg)](https://github.com/volshebniks/sauresha/graphs/commit-activity)
[![GitHub issues](https://img.shields.io/github/issues/volshebniks/sauresha)](https://github.com/volshebniks/sauresha/issues)

[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://https://www.buymeacoffee.com/RlnBV9r)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://money.yandex.ru/to/41001566881198)

Пожертвование на развитие проекта  [Яндекс.Деньги](https://money.yandex.ru/to/41001566881198)

## Update 1: Начиная с версии 0.3:
 * сделан переход на новое клиентское API
 * добавлена необязательная настройка для sensor - scan_interval. Время обновления в минутах. По умолчанию = 10 минут.
 * из-за перехода появились новые атрибуты у сенсоров.

## Update 2: версия 0.3.5:
 * уменьшено количество вызово API
 * ускорена первоначальная инициализация модуля
 * сделан переход на асинхронные методы
 * исправлена ошибка с заднием своего scan_interval
 * исправлена ошибка связанная с наличием русских букв в серийных номерах
 * на стороне Saures явно починили кеширование для нового API

## Update 3: версия 0.3.8:
 * вернул синхронные вызовы

## Update 4: Начиная с версии 0.5:
 * Существенно сокращено кол-во обращений к серверу Saures, для предотвращения блокировки.
   <br />Рекомендую в настройках указать:
```yaml
  scan_interval:
    minutes: 30
```
   Иначе могут быть блокировки в будущем.

## Update 5: Начиная с версии 0.6:
 * значительно изменен механизм настройки
 * можно задавать свои мена для всего
 * можно в настройках делать ссылки на !secret
 * добавил в manifest, version

## Update 6: Начиная с версии 1.0:
 * полностью переработан код для минимизации обращений к серверу Saures
 * внедрен асинхронный режим работы
 * Добавлено управление кранами
 * настройка через GUI

## Update 7: Начиная с версии 2.0.0:
 * обновление модуля под Home Assistant 2025.1+ / 2026.x (актуальная версия на момент релиза)
 * внедрён DataUpdateCoordinator: один опрос API Saures на все сущности вместо индивидуального polling
 * сущности переведены на SensorEntity / BinarySensorEntity / SwitchEntity + CoordinatorEntity
 * корректные device_class и единицы измерения (вода, газ, энергия, температура)
 * исправлен OptionsFlow для совместимости с HA 2025.12+ (больше не падает при открытии параметров)
 * добавлены unload/reload интеграции при изменении настроек
 * обновлены manifest.json / hacs.json (`iot_class: cloud_polling`, `integration_type: hub`)
 * исправлены ошибки API: auth lock, имя неизвестных контроллеров, URL команды управления краном
 * устойчивость к обрывам связи с api.saures.ru (`Connection reset by peer`): User-Agent как в доке API (`HTTPie`), отдельная IPv4-сессия, повтор запросов
 * сенсоры, binary_sensor и switch группируются в устройство контроллера в реестре устройств Home Assistant
 * **требуется Home Assistant >= 2025.1.0**

## Update 8: Начиная с версии 2.1.0:
 * docstring’и функций и классов переведены на русский язык
 * сущности обновляют состояние через `_attr_*` (совместимость с `cached_property` в новых версиях HA)
 * исправлен старт интеграции: убрана пауза 10 сек между объектами при первом опросе (больше не возникает `CancelledError` / ошибка setup entry)

## Update 9: Начиная с версии 2.1.1:
 * исправлена ошибка сенсоров многотарифной электроэнергии со значением вида `4803.08/1774.58` (больше не выставляется unit `kWh` для комбинированной строки)
 * для тарифов T1..Tn создаются отдельные числовые сенсоры в кВт·ч

## Update 10: Начиная с версии 2.1.2:
 * исправлена ошибка `AttributeError: __attr_native_unit_of_measurement` при создании сенсоров на новых версиях Home Assistant

## Update 11: Начиная с версии 2.1.3:
 * исправлена типизация преобразования показаний: `float()` не вызывается для `None`

## Update 12: Начиная с версии 2.1.4:
 * добавлена поддержка датчика давления (тип Saures 14, бар)
 * добавлена поддержка теплосчётчиков типов 11 (кВт·ч) и 13 (Гкал)
 * ошибка одного счётчика при setup больше не блокирует остальные сенсоры объекта

## Update 13: Начиная с версии 2.1.5:
 * binary_sensor «Подозрительный расход» для счётчиков холодной/горячей воды и газа (API state.number = 3)
 * событие Home Assistant `sauresha_suspicious_consumption` при срабатывании
 * у счётчиков: атрибуты `condition_number`, `suspicious_consumption`
 * у контроллера: атрибуты `suspicious_consumption`, `suspicious_consumption_meters`

## Update 14: Начиная с версии 2.1.6:
 * у датчика давления корректно выставляются unit (бар), device_class (pressure) и state_class (measurement)

## Содержание

* [Установка](#устнановка)
  * [Ручная установка](#ручная-установка)
  * [Установка через HACS](#hacs_установка)

Для связи: <master@g-s-a.me>

Интеграция контроллеров [Saures](https://www.saures.ru) c [Home Assistant](https://www.home-assistant.io/)
# Описание

В настоящее время поддерживаются следующие типы устройств от Saures (номер типа по API):
1. Счётчик холодной воды (м³) = sensor в Home Assistant
2. Счётчик горячей воды (м³) = sensor в Home Assistant
3. Счётчик газа (м³) = sensor в Home Assistant
4. Датчик протечки (0 – нет протечки, 1 – протечка) = binary_sensor в Home Assistant
5. Датчик температуры (°C) = sensor в Home Assistant
6. Электро-шаровой кран / реле — управление (0 – открыться, 1 – закрыться) = switch в Home Assistant
7. Счётчик тепла = sensor в Home Assistant
8. Счётчик электричества (кВт·ч), в том числе многотарифные (отдельные сенсоры T1..Tn) = sensor в Home Assistant
9. Датчик / сухой контакт (0 – деактивирован, 1 – активирован) = binary_sensor в Home Assistant
10. Состояние электро-шарового крана = binary_sensor в Home Assistant
11. Счётчик тепла (кВт·ч) = sensor в Home Assistant
13. Счётчик тепла (Гкал) = sensor в Home Assistant
14. Датчик давления (бар) = sensor в Home Assistant
— Непосредственно сами контроллеры = sensor в Home Assistant
— Подозрительный расход по счётчикам воды/газа (API state = 3) = binary_sensor + событие `sauresha_suspicious_consumption`

## Установка

### Ручная установка

1. Добавляем компонент в Home Assistant
   Распаковываем архив. Папку sauresha берем целиком и копируем в custom_components.
2. Осуществляем конфигурацию компонента в Home Assistant через GUI.
3. Перезагружаем HA

### HACS установка

1. Убедитесь, что [HACS](https://custom-components.github.io/hacs/) уже устновлен.
2. Перейдите на закладку SETTINGS
3. Введите https://github.com/volshebniks/sauresha   и выберите категорию Integration, нажмите Сохранить
4. Новый репозиторий Integration Saures controllers with HA будет добавлен на закладке Integration
5. Устновите SauresHA из него
3. Осуществляем конфигурацию компонента в Home Assistant через GUI.
4. Перезапустите HA.

# План развития проекта
- [X] Добавить проект в HACS
- [ ] Сделать сенсоры для счетчиков с показаниями за день/месяц/год
- [X] Добавить управление кранами
- [ ] Сделать pallete для Node-Red
- [X] Сделать полноценную интеграцию с Home Assistant (добавляется в раздел интеграции)


# Credits

Большое спасибо следующим организациям и проектам, работа которых имеет важное значение для развития проекта:

Нет их пока :)

----------------------------------------------------------------------------------------------------------------------------------
Пожертвование на развитие проекта  [Яндекс.Деньги](https://money.yandex.ru/to/41001566881198)