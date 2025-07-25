from pprint import pformat
from re import findall

from thingsboard_gateway.connectors.ble.ble_uplink_converter import BLEUplinkConverter
from thingsboard_gateway.gateway.constants import REPORT_STRATEGY_PARAMETER
from thingsboard_gateway.gateway.entities.converted_data import ConvertedData
from thingsboard_gateway.gateway.entities.report_strategy_config import ReportStrategyConfig
from thingsboard_gateway.gateway.entities.telemetry_entry import TelemetryEntry
from thingsboard_gateway.gateway.statistics.decorators import CollectStatistics
from thingsboard_gateway.gateway.statistics.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_utility import TBUtility


class BytesBLEUplinkConverter(BLEUplinkConverter):
    def __init__(self, config, logger):
        self._log = logger
        self.__config = config

    @CollectStatistics(start_stat_type='receivedBytesFromDevices',
                       end_stat_type='convertedBytesFromDevice')
    def convert(self, config, data):
        converted_data = ConvertedData(device_name=self.__config['deviceName'],
                                       device_type=self.__config['deviceType'])

        if data is None:
            return converted_data

        device_report_strategy = None
        try:
            device_report_strategy = ReportStrategyConfig(self.__config.get(REPORT_STRATEGY_PARAMETER))
        except ValueError as e:
            self._log.trace("Report strategy config is not specified for device %s: %s", self.__config['deviceName'], e)

        try:
            for section in ('telemetry', 'attributes'):
                for item in data[section]:
                    try:
                        if 'valueExpression' in item and item['valueExpression']:
                            try:
                                decoded_data = eval(item['valueExpression'], {}, {'data': item['data']})
                            except Exception as eval_error:
                                self._log.warning("Failed to eval valueExpression for key %s: %s", item.get('key'), eval_error)
                                decoded_data = item['data']
                        else:
                            decoded_data = item['data']

                        if item.get('key') is not None:
                            datapoint_key = TBUtility.convert_key_to_datapoint_key(
                                item['key'], device_report_strategy, item, self._log
                            )
                            if section == 'attributes':
                                converted_data.add_to_attributes(datapoint_key, decoded_data)
                            else:
                                telemetry_entry = TelemetryEntry({datapoint_key: decoded_data})
                                converted_data.add_to_telemetry(telemetry_entry)
                        else:
                            self._log.error('Key for %s not found in config: %s', config['type'], config[section])
                    except Exception as e:
                        self._log.exception('\nException caught when processing data for %s\n\n%s', pformat(config), e)

        except Exception as e:
            StatisticsService.count_connector_message(self._log.name, 'convertersMsgDropped')
            self._log.exception(e)

        self._log.debug('Converted data: %s', converted_data)
        StatisticsService.count_connector_message(self._log.name, 'convertersAttrProduced',
                                                  count=converted_data.attributes_datapoints_count)
        StatisticsService.count_connector_message(self._log.name, 'convertersTsProduced',
                                                  count=converted_data.telemetry_datapoints_count)
        return converted_data

