"""API for Saures"""
import logging
import datetime
import functools
import asyncio

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .classes import SauresController, SauresSensor
from .const import CONF_BINARY_SENSORS_DEF, CONF_SWITCH_DEF
from aiohttp import ClientTimeout, ClientError, ClientConnectorError

_LOGGER = logging.getLogger(__name__)


class SauresHA:
    _sid: str
    _debug: bool
    _last_login_time: datetime.datetime
    _binarysensors: dict
    _sensors: dict
    _switches: dict
    _data: dict
    _flats: dict
    _hass: object

    def __init__(self, hass, email, password, is_debug, userflats):
        self._email = email
        self._password = password
        self._debug = is_debug
        self._last_login_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
        self._last_update_time_dict = {}
        self._data = dict()
        self._sensors = dict()
        self._controllers = dict()
        self._binarysensors = dict()
        self._switches = dict()
        self._flats = dict()
        self.userflats = userflats
        self._hass = hass
        self._sid_renewal = False
        self._sid = ""

    def checkflatsfilter(self, filter_flats, flat_id):
        if not filter_flats:
            return True
        return str(flat_id) in filter_flats

    @property
    def flats(self):
        return self._flats

    async def auth(self) -> bool:
        bln_return = False
        try:
            now = datetime.datetime.now()
            period = now - self._last_login_time
            
            if period.total_seconds() >= 300:
                clientsession = async_get_clientsession(self._hass)
                self._last_login_time = now
                
                if self._sid_renewal:
                    _LOGGER.debug("Authentication already in progress")
                    return False
                
                self._sid_renewal = True
                
                auth_data = await clientsession.post(
                    "https://api.saures.ru/1.0/login",
                    data={"email": self._email, "password": self._password},
                    headers={
                        "User-Agent": "HTTPie/0.9.8",
                        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
                    },
                    timeout=ClientTimeout(total=30)
                )
                
                result = await auth_data.json()
                
                if not result or result.get("status") == "bad":
                    errors = result.get("errors", [])
                    error_msg = errors[0].get("msg", "Unknown error") if errors else "Unknown error"
                    raise Exception(f"Authentication failed: {error_msg}")
                
                self._sid = result["data"]["sid"]
                bln_return = True
                _LOGGER.debug(f"Authentication successful, SID: {self._sid[:8]}...")
                
            else:
                bln_return = bool(self._sid)
                if not bln_return:
                    _LOGGER.warning("No valid session available, forcing re-auth")
                    self._last_login_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
                    return await self.auth()
                    
        except (ClientConnectorError, ClientError) as conn_err:
            _LOGGER.error(f"Connection error during auth: {conn_err}")
            self._sid = ""
            bln_return = False
        except Exception as err:
            _LOGGER.error(f"Auth error: {str(err)}")
            self._sid = ""
            bln_return = False
        finally:
            self._sid_renewal = False
        
        return bln_return

    async def async_get_flats(self, hass):
        self._flats = dict()
        clientsession = async_get_clientsession(hass)
        
        if not self.userflats:
            try:
                lock = asyncio.Lock()
                async with lock:
                    if not await self.auth():
                        _LOGGER.error("Failed to authenticate for flats request")
                        return self._flats
                    
                    flats_data = await clientsession.get(
                        "https://api.saures.ru/1.0/user/objects",
                        params={"sid": self._sid},
                        headers={"User-Agent": "HTTPie/0.9.8"},
                        timeout=ClientTimeout(total=30)
                    )
                    
                    if flats_data.status != 200:
                        raise Exception(f"HTTP {flats_data.status}: {await flats_data.text()}")
                    
                    result = await flats_data.json()
                    result_data = result["data"]["objects"]
                    
                    for val in result_data:
                        flat_id = val.get("id")
                        if flat_id:
                            self._flats[flat_id] = f"{val.get('label', '')}:{val.get('house', '')}:{val.get('number', '')}"
                    
                    _LOGGER.debug(f"Loaded {len(self._flats)} flats")
                    
            except (ClientConnectorError, ClientError) as conn_err:
                _LOGGER.error(f"Connection error fetching flats: {conn_err}")
            except Exception as err:
                _LOGGER.error(f"Error fetching flats: {str(err)}")
                if self._debug:
                    _LOGGER.exception(err)
        else:
            self._flats = self.userflats
        
        return self._flats

    def checkdict(self, data, value):
        return value in data

    def get_controller_name(self, version_id):
        if version_id in ["1.3", "1.4", "1.5"]:
            return "счетчик C1"
        elif version_id in ["3.1", "3.2"]:
            return "контроллер R1(до 2017)"
        elif version_id == "3.4":
            return "контроллер R1 8 (2017-2018)"
        elif version_id == "3.5":
            return "контроллер R1 4 (после 2018)"
        elif version_id == "4.0":
            return "контроллер R2 (4.0) 8 аналоговых каналов"
        elif version_id == "4.5":
            return "контроллер R2 (4.5) 8 аналоговых каналов с клеммами для подключения внешнего питания"
        elif version_id == "4.1":
            return "контроллер R4"
        elif version_id == "6.3":
            return "контроллер R5"
        elif version_id == "7.2":
            return "контроллер R6"
        elif version_id == "8.2":
            return "контроллер R7(до 2020)"
        elif version_id == "8.3":
            return "контроллер R7(после 2020)"
        elif version_id == "9.1":
            return "контроллер R8(после 2022)"
        else:
            return f"неизвестный контроллер ({version_id})"

    async def set_command(self, meter_id, command_text):
        bln_return = False
        try:
            clientsession = async_get_clientsession(self._hass)
            lock = asyncio.Lock()
            async with lock:
                if not await self.auth():
                    _LOGGER.error("Authentication failed before sending command")
                    return False
                
                self._last_login_time = datetime.datetime.now()
                
                res_data = await clientsession.post(
                    "https://api.saures.ru/1.0/meter/control",
                    data={"sid": self._sid, "id": meter_id, "command": command_text},
                    headers={
                        "User-Agent": "HTTPie/0.9.8",
                        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
                    },
                    timeout=ClientTimeout(total=30)
                )
                
                result = await res_data.json()
                if not result or result.get("status") == "bad":
                    errors = result.get("errors", [])
                    error_msg = errors[0].get("msg", "Unknown error") if errors else "Unknown error"
                    _LOGGER.warning(f"Command failed for meter {meter_id}: {error_msg}")
                    return False
                
                bln_return = True
                _LOGGER.debug(f"Command successful for meter {meter_id}")
                
        except (ClientConnectorError, ClientError) as conn_err:
            _LOGGER.error(f"Connection error sending command: {conn_err}")
        except Exception as err:
            if self._debug:
                _LOGGER.error(f"Command error: {str(err)}")
                _LOGGER.exception(err)
        
        return bln_return

    async def async_get_data(self, flat_id, reload=False):
        now = datetime.datetime.now()
        
        if flat_id not in self._last_update_time_dict:
            self._last_update_time_dict[flat_id] = datetime.datetime(2000, 1, 1, 1, 1, 1)
        
        period = now - self._last_update_time_dict[flat_id]
        
        if period.total_seconds() >= 300 or reload:
            self._last_update_time_dict[flat_id] = now
            lock = asyncio.Lock()
            async with lock:
                if not await self.auth():
                    _LOGGER.error(f"Authentication failed for flat {flat_id} data request")
                    return self._data.get(flat_id, [])
                
                try:
                    clientsession = async_get_clientsession(self._hass)
                    controllers = await clientsession.get(
                        "https://api.saures.ru/1.0/object/meters",
                        params={"id": str(flat_id), "sid": self._sid},
                        headers={"User-Agent": "HTTPie/0.9.8"},
                        timeout=ClientTimeout(total=30)
                    )
                    
                    if controllers.status == 200:
                        data = await controllers.json(content_type=None)
                        self._data[flat_id] = data["data"]["sensors"]
                        _LOGGER.debug(f"Loaded {len(self._data[flat_id])} sensors for flat {flat_id}")
                    else:
                        _LOGGER.warning(f"HTTP {controllers.status} for flat {flat_id} sensors")
                        
                except (ClientConnectorError, ClientError) as conn_err:
                    _LOGGER.error(f"Connection error fetching data for flat {flat_id}: {conn_err}")
                except Exception as err:
                    if self._debug:
                        _LOGGER.error(f"Error fetching data for flat {flat_id}: {str(err)}")
                        _LOGGER.exception(err)
        
        return self._data.get(flat_id, [])

    async def async_get_controllers(self, flat_id):
        lock = asyncio.Lock()
        async with lock:
            controllers = await self.async_get_data(flat_id)

        self._controllers[flat_id] = controllers
        return self._controllers[flat_id]

    def get_controller(self, flat_id, sn):
        controllers = self._controllers[flat_id]
        return next(
            (
                SauresController(controller)
                for controller in controllers
                if controller["sn"] == sn
            ),
            SauresController(dict()),
        )

    async def async_get_binary_sensors(self, flat_id):
        results = list()
        lock = asyncio.Lock()
        async with lock:
            meters = await self.async_get_data(flat_id)
        res = functools.reduce(
            list.__add__, map(lambda sensor: sensor["meters"], meters)
        )
        for obj in res:
            objtype = obj.get("type", {}).get("number")
            if objtype in CONF_BINARY_SENSORS_DEF:
                results.append(obj)

        self._binarysensors[flat_id] = results

        return self._binarysensors[flat_id]

    async def async_get_sensors(self, flat_id):
        results = list()
        lock = asyncio.Lock()
        async with lock:
            meters = await self.async_get_data(flat_id)

        if meters:
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

    async def async_get_switches(self, flat_id, reload):
        results = list()
        lock = asyncio.Lock()
        async with lock:
            meters = await self.async_get_data(flat_id)
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

    async def async_fetch_data(self):
        try:
            if not await self.auth():
                _LOGGER.error("Initial authentication failed")
                return
            
            flats = await self.async_get_flats(self._hass)
            self._flats = flats
            
            for curflat in flats:
                try:
                    await self.async_get_controllers(curflat)
                    await self.async_get_sensors(curflat)
                    await self.async_get_binary_sensors(curflat)
                    await self.async_get_switches(curflat, False)
                    await asyncio.sleep(5)
                except Exception as e:
                    _LOGGER.error(f"Error loading data for flat {curflat}: {str(e)}")
                    if self._debug:
                        _LOGGER.exception(e)
        except Exception as e:
            _LOGGER.error(f"Critical error in async_fetch_data: {str(e)}")
            if self._debug:
                _LOGGER.exception(e)