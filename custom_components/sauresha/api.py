"""API for Saures"""
import logging
import time
import datetime
import requests
import functools
import async_timeout
from .classes import SauresController, SauresSensor
from .const import CONF_BINARY_SENSORS_DEF, CONF_SWITCH_DEF

_LOGGER = logging.getLogger(__name__)


class SauresHA:
    _sid: str
    _debug: bool
    _last_login_time: time
    _last_getsensors_time: time
    _binarysensors: dict
    _sensors: dict
    _switches: dict
    _data: dict
    _flats: list

    def __init__(self, email, password, is_debug, userflats):
        self.__session = requests.Session()
        self._email = email
        self._password = password
        self._debug = is_debug
        self._last_login_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
        self._last_getsensors_time_dict = {}
        self._data = dict()
        self._sensors = dict()
        self._controllers = dict()
        self._binarysensors = dict()
        self._switches = dict()
        self._flats = list()
        self.userflats = userflats

    def checkflatsfilter(self, filter_flats, flat_id):
        if len(filter_flats) == 0:
            return True

        for i in filter_flats:
            try:
                if i == str(flat_id):
                    return True
            except:
                pass
        return False

    @property
    def flats(self):
        return self.get_flats()

    @property
    def controllers(self):
        return self.get_controllers

    @property
    def sensors(self):
        return self.get_sensors

    @property
    def binary_sensors(self):
        return self.get_binary_sensors

    @property
    def re_auth(self):
        bln_return = False
        try:
            now = datetime.datetime.now()
            period = now - self._last_login_time
            if (period.total_seconds() / 60) > 5:
                self._last_login_time = datetime.datetime.now()
                auth_data = self.__session.post(
                    "https://api.saures.ru/login",
                    data={"email": self._email, "password": self._password},
                ).json()
                if not auth_data:
                    raise Exception("Invalid credentials")
                self._sid = auth_data["data"]["sid"]
                bln_return = auth_data["status"] != "bad"

            else:
                if self._sid == "":
                    bln_return = False
                else:
                    bln_return = True

        except Exception as e:  # catch *all* exceptions
            if self._debug:
                _LOGGER.warning(str(e))

        return bln_return

    def get_flats(self):
        flats = ""
        if len(self.userflats) == 0:
            try:
                if self.re_auth:
                    flats = self.__session.get(
                        "https://api.saures.ru/1.0/user/objects",
                        params={"sid": self._sid},
                    ).json()["data"]["objects"]
                    self._flats.clear()
                    for val in flats:
                        self._flats.append(val.get("id"))
                        _LOGGER.warning(
                            "ID flat: %s : %s",
                            str(val.get("house")),
                            str(val.get("id")),
                        )
            except Exception as e:
                if self._debug:
                    _LOGGER.warning(str(e))
        else:
            filter_flats = str(self.userflats).split(",")
            self._flats.clear()
            for val in filter_flats:
                self._flats.append(int(val))

        return self._flats

    def checkdict(self, data, value):
        for i in data.keys():
            try:
                if i == value:
                    return True
            except:
                pass
        return False

    def set_command(self, meter_id, command_text):
        bln_return = False
        try:
            if self.re_auth:
                self._last_login_time = datetime.datetime.now()
                res_data = self.__session.post(
                    "https://api.saures.ru/1.0/meter/control",
                    data={"sid": self._sid, "id": meter_id, "command": command_text},
                ).json()
                if not res_data:
                    raise Exception("Ошибка выполнения комманды.")

                bln_return = res_data["status"] != "bad"
                if not bln_return:
                    msg = f'Ошибка выполнения комманды -  command: {command_text} ,meter_id: {meter_id}, ошибка: {res_data["errors"][0]["msg"]}.'
                    _LOGGER.error(msg)

        except Exception as e:  # catch *all* exceptions
            if self._debug:
                _LOGGER.warning(str(e))

        return bln_return

    def get_data(self, flat_id, reload=False):
        now = datetime.datetime.now()
        if not self.checkdict(self._last_getsensors_time_dict, flat_id):
            self._last_getsensors_time_dict[flat_id] = datetime.datetime(
                2000, 1, 1, 1, 1, 1
            )
        period = now - self._last_getsensors_time_dict[flat_id]
        if (period.total_seconds() / 60) > 5 or reload:
            self._last_getsensors_time_dict[flat_id] = datetime.datetime.now()
            try:
                if self.re_auth:
                    controllers = self.__session.get(
                        "https://api.saures.ru/1.0/object/meters",
                        params={"id": str(flat_id), "sid": self._sid},
                    ).json()["data"]["sensors"]
                    self._data[flat_id] = controllers
            except Exception as e:
                if self._debug:
                    _LOGGER.warning(str(e))

        return self._data[flat_id]

    def get_controllers(self, flat_id):
        controllers = self.get_data(flat_id)
        self._controllers[flat_id] = controllers
        return self._controllers[flat_id]

    def get_controller(self, flat_id, sn):
        if not self.checkdict(self._last_getsensors_time_dict, flat_id):
            controllers = self.get_controllers(flat_id)
        else:
            controllers = self._controllers[flat_id]
        return next(
            (
                SauresController(controller)
                for controller in controllers
                if controller["sn"] == sn
            ),
            SauresController(dict()),
        )

    def get_binary_sensors(self, flat_id):
        results = list()
        meters = self.get_data(flat_id)
        res = functools.reduce(
            list.__add__, map(lambda sensor: sensor["meters"], meters)
        )
        for obj in res:
            objtype = obj.get("type", {}).get("number")
            if objtype in CONF_BINARY_SENSORS_DEF:
                results.append(obj)

        self._binarysensors[flat_id] = results

        return self._binarysensors[flat_id]

    def get_sensors(self, flat_id):
        results = list()
        meters = self.get_data(flat_id)
        res = functools.reduce(
            list.__add__, map(lambda sensor: sensor["meters"], meters)
        )
        for obj in res:
            objtype = obj.get("type", {}).get("number")
            if (
                objtype not in CONF_BINARY_SENSORS_DEF
                and objtype not in CONF_SWITCH_DEF
            ):
                results.append(obj)

        self._sensors[flat_id] = results

        return self._sensors[flat_id]

    def get_sensor(self, flat_id, sensor_id):
        if flat_id in self._sensors:
            meters = self._sensors[flat_id]
            for obj in meters:
                if obj["meter_id"] == sensor_id:
                    return SauresSensor(obj)
        return SauresSensor(dict())

    def get_binarysensor(self, flat_id, sensor_id):
        if flat_id in self._binarysensors:
            meters = self._binarysensors[flat_id]
            for obj in meters:
                if obj["meter_id"] == sensor_id:
                    return SauresSensor(obj)

        return SauresSensor(dict())

    def get_switches(self, flat_id, reload):
        results = list()
        meters = self.get_data(flat_id, reload)
        res = functools.reduce(
            list.__add__, map(lambda sensor: sensor["meters"], meters)
        )
        for obj in res:
            if obj.get("type", {}).get("number") in CONF_SWITCH_DEF:
                results.append(obj)

        self._switches[flat_id] = results
        return self._switches[flat_id]

    def get_switch(self, flat_id, switch_id):
        if flat_id in self._switches:
            meters = self._switches[flat_id]
            for obj in meters:
                if obj["meter_id"] == switch_id:
                    return SauresSensor(obj)
        return SauresSensor(dict())

    def fetch_data(self):
        flats = self.get_flats()
        for curflat in flats:
            self.get_controllers(curflat)
            self.get_sensors(curflat)
            self.get_binary_sensors(curflat)
            self.get_switches(curflat, False)

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(10):
                return self.fetch_data()
        except Exception as e:
            _LOGGER.error(str(e))
