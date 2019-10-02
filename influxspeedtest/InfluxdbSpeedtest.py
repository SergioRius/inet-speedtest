import sys
import time
import os

import speedtest
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests import ConnectTimeout, ConnectionError

from influxspeedtest.common import log

class InfluxdbSpeedtest():

    def __init__(self):

        # Setup configuration
        log.debug('Loading Configuration.')
        self.config_delay = int(os.getenv("DELAY", 300))

        # InfluxDB
        self.config_influx_address = os.getenv("INFLUXDB_HOST", "127.0.0.1")
        self.config_influx_port = os.getenv("INFLUXDB_PORT", 8086)
        self.config_influx_database = os.getenv("INFLUXDB_DATABASE", "speedtest")
        self.config_influx_measurement = os.getenv("INFLUXDB_MEASUREMENT", "speedtest")
        self.config_influx_user = os.getenv("INFLUXDB_USR", "")
        self.config_influx_password = os.getenv("INFLUXDB_PWD", "")
        self.config_influx_ssl = os.getenv("INFLUXDB_SSL", False)
        self.config_influx_verify_ssl = os.getenv("INFLUXDB_VERIFYSSL", True)

        # Speedtest
        self.config_servers = []
        test_server = os.getenv("SPEEDTEST_SERVER", "")
        if test_server:
            self.config_servers = test_server.split(',')
        
        log.debug('Configuration Successfully Loaded')

        self.influx_client = self._get_influx_connection()
        self.speedtest = None
        self.results = None

    def _get_influx_connection(self):
        """
        Create an InfluxDB connection and test to make sure it works.
        We test with the get all users command.  If the address is bad it fails
        with a 404.  If the user doesn't have permission it fails with 401
        :return:
        """

        influx = InfluxDBClient(
            self.config_influx_address,
            self.config_influx_port,
            database=self.config_influx_database,
            ssl=self.config_influx_ssl,
            verify_ssl=self.config_influx_verify_ssl,
            username=self.config_influx_user,
            password=self.config_influx_password,
            timeout=5
        )
        try:
            log.debug('Testing connection to InfluxDb using provided credentials')
            influx.get_list_users()  # TODO - Find better way to test connection and permissions
            log.debug('Successful connection to InfluxDb')
        except (ConnectTimeout, InfluxDBClientError, ConnectionError) as e:
            if isinstance(e, ConnectTimeout):
                log.critical('Unable to connect to InfluxDB at the provided address (%s)', self.config_influx_address)
            elif e.code == 401:
                log.critical('Unable to connect to InfluxDB with provided credentials')
            else:
                log.critical('Failed to connect to InfluxDB for unknown reason')

            sys.exit(1)

        return influx

    def setup_speedtest(self, server=None):
        """
        Initializes the Speed Test client with the provided server
        :param server: Int
        :return: None
        """
        speedtest.build_user_agent()

        log.debug('Setting up SpeedTest.net client')

        if server is None:
            server = []
        else:
            server = server.split() # Single server to list

        try:
            self.speedtest = speedtest.Speedtest()
        except speedtest.ConfigRetrievalError:
            log.critical('Failed to get speedtest.net configuration.  Aborting')
            sys.exit(1)

        self.speedtest.get_servers(server)

        log.debug('Picking the closest server')

        self.speedtest.get_best_server()

        log.info('Selected Server %s in %s', self.speedtest.best['id'], self.speedtest.best['name'])

        self.results = self.speedtest.results

    def send_results(self):
        """
        Formats the payload to send to InfluxDB
        :rtype: None
        """
        result_dict = self.results.dict()

        input_points = [
            {
                'measurement': self.config_influx_measurement,
                'fields': {
                    'download': result_dict['download'],
                    'upload': result_dict['upload'],
                    'ping': result_dict['server']['latency']
                },
                'tags': {
                    'server': result_dict['server']['id'],
                    'server_name': result_dict['server']['name'],
                    'server_country': result_dict['server']['country']
                }
            }
        ]

        self.write_influx_data(input_points)

    def run_speed_test(self, server=None):
        """
        Performs the speed test with the provided server
        :param server: Server to test against
        """
        log.info('Starting Speed Test For Server %s', server)

        try:
            self.setup_speedtest(server)
        except speedtest.NoMatchedServers:
            log.error('No matched servers: %s', server)
            return
        except speedtest.ServersRetrievalError:
            log.critical('Cannot retrieve speedtest.net server list. Aborting')
            return
        except speedtest.InvalidServerIDType:
            log.error('%s is an invalid server type, must be int', server)
            return

        log.info('Starting download test')
        self.speedtest.download()
        log.info('Starting upload test')
        self.speedtest.upload()
        self.send_results()

        results = self.results.dict()
        log.info('Download: %sMbps - Upload: %sMbps - Latency: %sms',
                 round(results['download'] / 1000000, 2),
                 round(results['upload'] / 1000000, 2),
                 results['server']['latency']
                 )



    def write_influx_data(self, json_data):
        """
        Writes the provided JSON to the database
        :param json_data:
        :return: None
        """
        log.debug(json_data)

        try:
            self.influx_client.write_points(json_data)
        except (InfluxDBClientError, ConnectionError, InfluxDBServerError) as e:
            if hasattr(e, 'code') and e.code == 404:
                log.error('Database %s Does Not Exist.  Attempting To Create', self.config_influx_database)
                self.influx_client.create_database(self.config_influx_database)
                self.influx_client.write_points(json_data)
                return

            log.error('Failed To Write To InfluxDB')
            print(e)

        log.debug('Data written to InfluxDB')

    def run(self):

        while True:
            if not self.config_servers:
                self.run_speed_test()
            else:
                for server in self.config_servers:
                    self.run_speed_test(server)
            log.info('Waiting %s seconds until next test', self.config_delay)
            time.sleep(self.config_delay)
