#     Copyright 2025. ThingsBoard
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

from threading import Thread
from platform import system
from time import time, sleep
import asyncio
from typing import Optional, Any, List, Dict
import json
import os

from bleak import BleakClient, BleakScanner

# 添加类型忽略注释，因为这些是ThingsBoard Gateway的依赖
try:
    from thingsboard_gateway.gateway.statistics.decorators import CollectStatistics  # type: ignore
    from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader  # type: ignore
    from thingsboard_gateway.connectors.ble.error_handler import ErrorHandler  # type: ignore
except ImportError:
    # 如果导入失败，创建占位符类
    class CollectStatistics:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
    
    class TBModuleLoader:
        @staticmethod
        def import_module(*args, **kwargs):
            return None
    
    class ErrorHandler:
        def __init__(self, error):
            self.error = error
        def is_char_not_found(self):
            return False
        def is_operation_not_supported(self):
            return False


class AutoDeviceScanner:
    """自动扫描并添加ESP32C3_BLE设备的扫描器"""
    
    def __init__(self, logger, config_path: str = "auto_devices.json"):
        self._log = logger
        self.config_path = config_path
        self.scan_interval = 30  # 扫描间隔（秒）
        self.device_name_pattern = "ESP32C3_BLE"
        self.discovered_devices: Dict[str, Dict] = {}
        self.stopped = False
        
    async def scan_for_devices(self) -> List[Dict]:
        """扫描包含ESP32C3_BLE的设备"""
        try:
            self._log.info("Starting auto scan for ESP32C3_BLE devices...")
            devices = await BleakScanner(scanning_mode="active").discover(timeout=10)
            
            found_devices = []
            for device in devices:
                if device.name and self.device_name_pattern in device.name:
                    device_info = {
                        'name': device.name,
                        'address': device.address,
                        'rssi': device.rssi,
                        'metadata': device.metadata
                    }
                    found_devices.append(device_info)
                    self._log.info(f"Found device: {device.name} ({device.address})")
            
            return found_devices
        except Exception as e:
            self._log.error(f"Error during auto scan: {e}")
            return []
    
    def create_device_config(self, device_info: Dict) -> Dict:
        """为发现的设备创建配置"""
        device_name = device_info['name']
        mac_address = device_info['address']
        
        # 基础配置模板
        config = {
            'name': device_name,
            'MACAddress': mac_address,
            'deviceType': 'default',
            'timeout': 10000,
            'connectRetry': 5,
            'connectRetryInSeconds': 2,
            'waitAfterConnectRetries': 10,
            'pollPeriod': 5000,
            'showMap': False,
            'type': 'bytes',
            'extension': 'BytesBLEUplinkConverter',
            'telemetry': [
                {
                    'characteristicUUID': '0000FFE1-0000-1000-8000-00805F9B34FB',
                    'method': 'read',
                    'dataSourceType': 'characteristic',
                    'key': 'temperature',
                    'pollPeriod': 5000
                },
                {
                    'characteristicUUID': '0000FFE1-0000-1000-8000-00805F9B34FB',
                    'method': 'read',
                    'dataSourceType': 'characteristic',
                    'key': 'humidity',
                    'pollPeriod': 5000
                },
                {
                    'characteristicUUID': '0000FFE1-0000-1000-8000-00805F9B34FB',
                    'method': 'read',
                    'dataSourceType': 'characteristic',
                    'key': 'battery',
                    'pollPeriod': 5000
                }
            ],
            'attributes': [
                {
                    'characteristicUUID': '0000FFE1-0000-1000-8000-00805F9B34FB',
                    'method': 'read',
                    'dataSourceType': 'characteristic',
                    'key': 'manufacturer'
                },
                {
                    'characteristicUUID': '0000FFE1-0000-1000-8000-00805F9B34FB',
                    'method': 'read',
                    'dataSourceType': 'characteristic',
                    'key': 'model_number'
                }
            ],
            'attributeUpdates': [],
            'serverSideRpc': []
        }
        
        return config
    
    def save_discovered_devices(self, devices: List[Dict]):
        """保存发现的设备到配置文件"""
        try:
            device_configs = []
            for device_info in devices:
                config = self.create_device_config(device_info)
                device_configs.append(config)
            
            config_data = {
                'auto_discovered': True,
                'devices': device_configs,
                'last_scan': time()
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self._log.info(f"Saved {len(device_configs)} auto-discovered devices to {self.config_path}")
            
        except Exception as e:
            self._log.error(f"Error saving discovered devices: {e}")
    
    def load_discovered_devices(self) -> List[Dict]:
        """从配置文件加载自动发现的设备"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                
                if config_data.get('auto_discovered'):
                    devices = config_data.get('devices', [])
                    self._log.info(f"Loaded {len(devices)} auto-discovered devices from {self.config_path}")
                    return devices
        except Exception as e:
            self._log.error(f"Error loading discovered devices: {e}")
        
        return []
    
    async def auto_scan_loop(self):
        """自动扫描循环"""
        while not self.stopped:
            try:
                # 扫描设备
                found_devices = await self.scan_for_devices()
                
                if found_devices:
                    # 保存发现的设备
                    self.save_discovered_devices(found_devices)
                    self.discovered_devices = {d['address']: d for d in found_devices}
                
                # 等待下次扫描
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self._log.error(f"Error in auto scan loop: {e}")
                await asyncio.sleep(5)
    
    def start_auto_scan(self):
        """启动自动扫描"""
        self.stopped = False
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.auto_scan_loop())
    
    def stop_auto_scan(self):
        """停止自动扫描"""
        self.stopped = True

MAC_ADDRESS_FORMAT = {
    'Darwin': '-',
    'other': ':'
}
DEFAULT_CONVERTER_CLASS_NAME = 'BytesBLEUplinkConverter'


class Device(Thread):
    def __init__(self, config, logger):
        super().__init__()
        self._log = logger
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.stopped = False
        self.name = config['name']
        self.device_type = config.get('deviceType', 'default')
        self.timeout = config.get('timeout', 10000) / 1000
        self.connect_retry = config.get('connectRetry', 5)
        self.connect_retry_in_seconds = config.get('connectRetryInSeconds', 0)
        self.wait_after_connect_retries = config.get('waitAfterConnectRetries', 0)
        self.show_map = config.get('showMap', False)
        self.__connector_type = config['connector_type']

        self.daemon = True

        try:
            self.mac_address = self.validate_mac_address(config['MACAddress'])
            self.client: Optional[BleakClient] = BleakClient(self.mac_address)
        except ValueError as e:
            self.client = None
            self.stopped = True
            self._log.error(e)

        self.poll_period = config.get('pollPeriod', 5000) / 1000
        self.config = self._generate_config(config)
        self.adv_only = self._check_adv_mode()
        self.callback = config['callback']
        self.last_polled_time = self.poll_period + 1

        self.notifying_chars = []

        # 添加启动延迟，避免所有设备同时启动
        import random
        startup_delay = random.uniform(0, 3)  # 0-3秒随机延迟
        sleep(startup_delay)
        
        self.start()

    def _check_adv_mode(self):
        if len(self.config['characteristic']['telemetry']) or len(self.config['characteristic']['attributes']):
            return False

        return True

    def _generate_config(self, config):
        new_config = {
            'characteristic': {
                'extension': self.__load_converter(config.get('extension', DEFAULT_CONVERTER_CLASS_NAME if config.get(
                    'type', 'bytes') == 'bytes' else 'HexBytesBLEUplinkConverter')),
                'telemetry': [],
                'attributes': []
            },
            'advertisement': {
                'extension': self.__load_converter(config.get('extension', 'HexBytesBLEUplinkConverter' if config.get(
                    'type', 'hex') == 'hex' else DEFAULT_CONVERTER_CLASS_NAME)),
                'telemetry': [],
                'attributes': []
            },
            'reportStrategy': config.get('reportStrategy', None),
            'attributeUpdates': config.get('attributeUpdates', []),
            'serverSideRpc': config.get('serverSideRpc', [])
        }

        for section in ('telemetry', 'attributes'):
            for section_config in config[section]:
                if section_config.get('dataSourceType', 'characteristic') == 'characteristic':
                    new_config['characteristic'][section].append(section_config)
                else:
                    new_config['advertisement'][section].append(section_config)

        return new_config

    @staticmethod
    def validate_mac_address(mac_address):
        os_name = system()

        if MAC_ADDRESS_FORMAT[os_name if os_name == 'Darwin' else 'other'] not in mac_address:
            raise ValueError(f'Mac-address is invalid for {os_name} os')

        return mac_address.upper()

    def __load_converter(self, name):
        module = TBModuleLoader.import_module(self.__connector_type, name)

        if module:
            self._log.debug('Converter %s for device %s - found!', name, self.name)
            return module
        else:
            self._log.error("Cannot find converter for %s device", self.name)
            self.stopped = True

    async def timer(self):
        while True:
            try:
                if time() - self.last_polled_time >= self.poll_period:
                    self.last_polled_time = time()
                    await self.__process_self()
                    
                    # 只在设备未连接时才处理广播数据
                    if self.client is None or not self.client.is_connected:
                        await self._process_adv_data()
                else:
                    await asyncio.sleep(.2)
            except Exception as e:
                self._log.exception('Problem with connection: \n %s', e)

                if self.client is not None:
                    try:
                        await self.client.disconnect()
                    except Exception as err:
                        self._log.exception(err)

                connect_try = 0
                while not self.stopped and (self.client is None or not self.client.is_connected):
                    await self.connect_to_device()

                    connect_try += 1
                    if connect_try == self.connect_retry:
                        sleep(self.wait_after_connect_retries)

                    sleep(self.connect_retry_in_seconds)
                    sleep(1.0)  # 增加重试间隔到1秒

    async def notify_callback(self, sender, data: bytearray):
        not_converted_data = {'telemetry': [], 'attributes': []}
        for section in ('telemetry', 'attributes'):
            for item in self.config['characteristic'][section]:
                if item.get('handle') and item['handle'] == sender:
                    not_converted_data[section].append({'data': data, **item})

                    data_for_converter = {
                        'deviceName': self.name,
                        'deviceType': self.device_type,
                        'converter': self.config['characteristic']['extension'],
                        'config': {
                            **self.config['characteristic']
                        },
                        'data': not_converted_data
                    }

                    self.callback(data_for_converter)

    async def notify(self, char_id):
        if self.client is not None:
            await self.client.start_notify(char_id, self.notify_callback)

    async def __process_self(self):
        if self.client is None:
            return
            
        not_converted_data = {'telemetry': [], 'attributes': []}
        for section in ('telemetry', 'attributes'):
            for item in self.config['characteristic'][section]:
                char_id = item['characteristicUUID']

                if item['method'] == 'read':
                    try:
                        data = await self.client.read_gatt_char(char_id)
                        not_converted_data[section].append({'data': data, **item})
                    except Exception as e:
                        error = ErrorHandler(e)
                        if error.is_char_not_found() or error.is_operation_not_supported():
                            self._log.error(e)
                            pass
                        else:
                            raise e
                elif item['method'] == 'notify' and char_id not in self.notifying_chars:
                    try:
                        self.__set_char_handle(item, char_id)
                        self.notifying_chars.append(char_id)
                        await self.notify(char_id)
                    except Exception as e:
                        error = ErrorHandler(e)
                        if error.is_char_not_found() or error.is_operation_not_supported():
                            self._log.error(e)
                            pass
                        else:
                            raise e

        if len(not_converted_data['telemetry']) > 0 or len(not_converted_data['attributes']) > 0:
            data_for_converter = {
                'deviceName': self.name,
                'deviceType': self.device_type,
                'reportStrategy': self.config.get('reportStrategy', None),
                'converter': self.config['characteristic']['extension'],
                'config': {
                    **self.config['characteristic']
                },
                'data': not_converted_data
            }
            self.callback(data_for_converter)

    def __set_char_handle(self, item, char_id):
        if self.client is None:
            return
            
        for serv in self.client.services:
            for char in serv.characteristics:
                if char.uuid == char_id:
                    item['handle'] = char.handle
                    return

    async def _connect_to_device(self):
        if self.client is None:
            self._log.error('Client is None, cannot connect')
            return
            
        try:
            self._log.info('Trying to connect to %s with %s MAC address', self.name, self.mac_address)
            await self.client.connect(timeout=self.timeout)
        except Exception as e:
            self._log.error(e)

    def filter_macaddress(self, device):
        macaddress, device = device
        if macaddress == self.mac_address:
            return True

        return False

    async def _process_adv_data(self):
        devices = await BleakScanner(scanning_mode="active").discover(timeout=self.timeout, return_adv=True)

        try:
            device = tuple(filter(self.filter_macaddress, devices.items()))[0][-1]
        except IndexError:
            self._log.error('Device with MAC address %s not found!', self.mac_address)
            return

        try:
            advertisement_data = list(device[-1].manufacturer_data.values())[0]
        except (IndexError, AttributeError):
            self._log.error('Device %s haven\'t advertisement data', self.name)
            return

        data_for_converter = {
            'deviceName': self.name,
            'deviceType': self.device_type,
            'converter': self.config['advertisement']['extension'],
            'config': {
                **self.config['advertisement']
            },
            'data': advertisement_data
        }

        self.callback(data_for_converter)

    async def connect_to_device(self):
        while not self.stopped and (self.client is None or not self.client.is_connected):
            await self._connect_to_device()

            sleep(5)  # 增加到5秒间隔

    async def run_client(self):
        if not self.adv_only or self.show_map:
            # default mode
            await self.connect_to_device()

            if self.client and self.client.is_connected:
                self._log.info('Connected to %s device', self.name)

                if self.show_map:
                    await self.__show_map()

                await self.timer()
        else:
            while not self.stopped:
                await self._process_adv_data()
                sleep(self.poll_period)

    def run(self):
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.run_client())

    async def __show_map(self, return_result=False):
        if self.client is None:
            return "Client is None, cannot show map"
            
        result = f'MAP FOR {self.name.upper()}'

        for service in self.client.services:
            result += f'\n| [Service] {service}'
            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = bytes(await self.client.read_gatt_char(char.uuid))
                        result += f"\n| \t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"
                    except Exception as e:
                        result += f"\n| \t[Characteristic] {char} ({','.join(char.properties)}), Value: {e}"

                else:
                    value = None
                    result += f"\n| \t[Characteristic] {char} ({','.join(char.properties)}), Value: {value}"

                for descriptor in char.descriptors:
                    try:
                        value = bytes(
                            await self.client.read_gatt_descriptor(descriptor.handle)
                        )
                        result += f"\n| \t\t[Descriptor] {descriptor}) | Value: {value}"
                    except Exception as e:
                        result += f"| \t\t[Descriptor] {descriptor}) | Value: {e}"

        if return_result:
            return result
        else:
            self._log.info(result)

    def scan_self(self, return_result):
        if self.loop is None:
            return "Loop is None, cannot scan"
            
        task = self.loop.create_task(self.__show_map(return_result))

        while not task.done():
            sleep(.2)

        return task.result()

    async def __write_char(self, char_id, data):
        if self.client is None:
            return "Client is None, cannot write"
            
        try:
            await self.client.write_gatt_char(char_id, data, response=True)
            await asyncio.sleep(1.0)
            return 'Ok'
        except Exception as e:
            self._log.exception('Can\'t write data to device: \n %s', e)
            return e

    @CollectStatistics(start_stat_type='allBytesSentToDevices')
    def write_char(self, char_id, data):
        if self.loop is None:
            return "Loop is None, cannot write"
            
        task = self.loop.create_task(self.__write_char(char_id, data))

        while not task.done():
            sleep(.2)

        return task.result()

    async def __read_char(self, char_id):
        if self.client is None:
            return None
            
        try:
            return await self.client.read_gatt_char(char_id)
        except Exception as e:
            self._log.exception(e)
            return None

    def read_char(self, char_id):
        if self.loop is None:
            return "Loop is None, cannot read"
            
        task = self.loop.create_task(self.__read_char(char_id))

        while not task.done():
            sleep(.2)

        result = task.result()
        if result is None:
            return "Failed to read characteristic"
        return result.decode('UTF-8')

    def __str__(self):
        return f'{self.name}'

    def stop(self):
        self.stopped = True
