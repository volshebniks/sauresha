# SauresHA
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/volshebniks/sauresha)](https://github.com/volshebniks/sauresha/releases)
![GitHub Release Date](https://img.shields.io/github/release-date/volshebniks/sauresha)
[![GitHub](https://img.shields.io/github/license/volshebniks/sauresha)](LICENSE)

[![Maintenance](https://img.shields.io/badge/Maintained%3F-Yes-brightgreen.svg)](https://github.com/volshebniks/sauresha/graphs/commit-activity)
[![GitHub issues](https://img.shields.io/github/issues/volshebniks/sauresha)](https://github.com/volshebniks/sauresha/issues)

Пожертвование на развитие проекта  [Яндекс.Деньги](https://money.yandex.ru/to/41001566881198)

## Update 1: Начиная с версии 0.3: 
 * сделан переход на новое клиентское API
 * добавлена необязательная настройка для sensor - scan_interval. Время обновления в минутах. По умолчанию = 10 минут.
 * из-за перехода появились новые атрибуты у сенсоров.
 
 Внимание - если данные будут обновляться с большой задежкой, рекомендую откатится на предыдущую версию! 


## Содержание

* [Установка](#устнановка)
  * [Ручная установка](#ручная-установка)
  * [Установка через HACS](#hacs_установка)
* [Настройка](#как-использовать)
  * [Параметры](#Параметры)



Для связи: <master@g-s-a.me>

Интеграция котроллеров [Saures](https://www.saures.ru) c [Home Assistant](https://www.home-assistant.io/)
# Описание

В настоящее время поддерживаются следующие типы устройств от Saurus
1. Счетчик холодной воды (м³) = sensor в Home Assistant
2. Счетчик горячей воды (м³) = sensor в Home Assistant
3. Счетчик газа (м³) = sensor в Home Assistant
4. Датчик протечки (0 – нет протечки, 1 - протечка) = binary_sensor в Home Assistant
5. Датчик температуры (градусы) = sensor в Home Assistant
6. Электро-шаровой кран управление (0 – открыться, 1 - закрыться) - не поддерживается
7. Счетчик тепла (кВт*ч) = sensor в Home Assistant
8. Счетчик электричества (кВт*ч) (в том числе многотарифные) = sensor в Home Assistant
9. Сухой контакт (0 – деактивирован, 1 – активирован) = binary_sensor в Home Assistant
10. Электро-шаровой кран состояние (0 – не подключен модуль, 1 – неизвестное состояние, 2 – открыт, 3 - закрыт) = sensor в Home Assistant
11. Непосредственно сами контроллеры = sensor в Home Assistant

## Установка

### Ручная установка

1. Добавляем компонент в Home Assistant
Распаковываем архив. Папку sauresha берем целиком и копируем в custom_components.
2. Осуществляем конфигурацию компонента в Home Assistant.
- email и password - Ваши учетные данные личного кабинета на saures.ru.
- controllers_sn - сериный номер контроллера
- counters_sn - сериный номер счетчика или датчика (задать в  личном кабине на saures.ru)
- flat_id (как заполнить указано ниже)
3. Перезагружаем HA

### HACS установка

1. Убедитесь, что [HACS](https://custom-components.github.io/hacs/) уже устновлен.
2. Перейдите на закладку SETTINGS
3. Введите https://github.com/volshebniks/sauresha   и выберите категорию Integration, нажмите Сохранить
4. Новый репозиторий Integration Saures controllers with HA будет добавлен на закладке Integration
5. Устновите SauresHA из него 
3. Настройте `sauresha` sensor и/или binary_sensor.
4. Перезапустите HA.

## Как использовать

### Параметры

Это добавляем в sensors
```yaml
- platform: sauresha
  email: вашemail
  password: вашпароль
  flat_id: 2
  # начиная с версии 0.3 (время обновления в минутах)
  scan_interval: 10
  counters_sn: 
      - 12311111
      - 12111111
  controllers_sn: 
      - 84VVEBXXFCXX
```
Это добавляем, при наличии соответвующих датчиков  в binary_sensors
```yaml
- platform: sauresha
  email: вашemail
  password: вашпароль
  flat_id: 2
  counters_sn: 
      - 12311111
      - 12111111
```

* Важно: Если не знаете как в личном кабине увидеть flat_id - высвечивается при наведении на адресс в адресной сроке, то вводите flat_id : 0. При наличии у вас только одного созданного адреса, работать будет и так. Но все же рекомендую - его узнать и заполнить - будет меньше запросов к API saures.

Узнать flat_id (усли указан flat_id: 0) можно найдя в логе Home Assistant, строки вида:
![Лог](https://github.com/volshebniks/images/raw/master/log_saures.jpg)
<br />
Цифра в конце, после двоеточия и есть необходимый flat_id

# План развития проекта
- [X] Добавить проект в HACS
- [ ] Сделать сенсоры для счетчиков с показаниями за день/месяц/год
- [ ] Добавить управление кранами
- [ ] Сделать pallete для Node-Red
- [ ] Сделать полноценную интеграцию с Home Assistant (добавляется в раздел интеграции)


# Credits

Большое спасибо следующим организациям и проектам, работа которых имеет важное значение для развития проекта:

Нет их пока :)

----------------------------------------------------------------------------------------------------------------------------------
Пожертвование на развитие проекта  [Яндекс.Деньги](https://money.yandex.ru/to/41001566881198)
