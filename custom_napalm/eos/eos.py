from __future__ import print_function
from __future__ import unicode_literals

# std libs
import re
import time
import json

from datetime import datetime
from collections import defaultdict
from netaddr import IPAddress
from netaddr import IPNetwork

from netaddr.core import AddrFormatError

# third party libs
import pyeapi
from pyeapi.eapilib import ConnectionError

# NAPALM base
import napalm.base.helpers
from napalm.base.base import NetworkDriver
from napalm.base.utils import string_parsers
from napalm.base.utils import py23_compat
from napalm.base.exceptions import ConnectionException, MergeConfigException, \
                        ReplaceConfigException, SessionLockedException, CommandErrorException

import napalm.base.constants as c
# local modules
# here add local imports
from netmiko import ConnectHandler, NetMikoAuthenticationException, NetMikoTimeoutException
import pyeapi

from napalm.eos.eos import EOSDriver


class CustomEOSDriver(EOSDriver):
    """Custom NAPALM Arista EOS Handler."""
    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        super().__init__(hostname, username, password, timeout, optional_args)

    def open(self):
        """Implementation of NAPALM method open."""
        try:
            if self.transport in ('http', 'https'):
                connection = pyeapi.client.connect(
                    transport=self.transport,
                    host=self.hostname,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                    timeout=self.timeout
                )
            elif self.transport == 'socket':
                connection = pyeapi.client.connect(transport=self.transport)
            else:
                raise ConnectionException("Unknown transport: {}".format(self.transport))

            if self.device is None:
                self.device = pyeapi.client.Node(connection, enablepwd=self.enablepwd)
            # does not raise an Exception if unusable
            # let's try to run a very simple command
            #self.turn_on_management_api_http_cmds()
            self.device.run_commands(['show clock'], encoding='text')

        except ConnectionError as ce:
            # and this is raised either if device not avaiable
            # either if HTTP(S) agent is not enabled
            # show management api http-commands
            self.turn_on_management_api_http_cmds()
            raise ConnectionException(py23_compat.text_type(ce))


    def turn_on_management_api_http_cmds(self):
        try:
            connection = ConnectHandler(device_type="arista_eos", ip=self.hostname, username=self.username, password=self.password, secret=self.enablepwd)
            connection.enable()
            connection.config_mode()
            connection.send_command_timing('management api http-commands')
            connection.send_command('no shut')
            # connection.exit_config_mode()
            # connection.send_command_timing('write memory')
        except NetMikoAuthenticationException as autherr:
            print("Could not turn on management api http-cmds")
            print(autherr)
        except NetMikoTimeoutException as timeouterr:
            print("Could not turn on management api http-cmds")
            print(timeouterr)
        except:
            print("Could not turn on management api http-cmds")
        finally:
            connection.disconnect()


    def get_layer2_neighbor_discovery_details(self):
        lldp_neighbors_out = {}
        commands = [
            'show lldp neighbors detail'.format()
        ]

        lldp_neighbors_in = {}
        lldp_neighbors_in = self.device.run_commands(commands)[0].get('lldpNeighbors', {})


        for interface in lldp_neighbors_in:
            interface_neighbors = lldp_neighbors_in.get(interface).get('lldpNeighborInfo', {})
            if not interface_neighbors:
                # in case of empty infos
                continue

            # it is provided a list of neighbors per interface
            for neighbor in interface_neighbors:
                if interface not in lldp_neighbors_out.keys():
                    lldp_neighbors_out[interface] = []
                capabilities = neighbor.get('systemCapabilities', {})
                capabilities_list = list(capabilities.keys())
                capabilities_list.sort()
                neighbor_interface_info = neighbor.get('neighborInterfaceInfo', {})
                try:
                    management_address = neighbor.get('managementAddresses', None)
                    if management_address is not None and len(management_address) > 0:
                        management_address = management_address[0]['address']
                except:
                    management_address = None
                lldp_neighbors_out[interface].append(
                    {
                        'remote_system_name': neighbor.get('systemName', u''),
                        'remote_port': neighbor_interface_info.get('interfaceId', u'').strip('\\"'),
                        'remote_management_ip_address': management_address,
                        'remote_system_description': neighbor.get('systemDescription', u''),
                        'remote_system_enabled_capab': py23_compat.text_type(', '.join(
                            [capability for capability in capabilities_list
                             if capabilities[capability]]))
                    }
                )
        return lldp_neighbors_out

    