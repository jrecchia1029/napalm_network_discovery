from __future__ import unicode_literals

# import stdlib
import re
import json
import logging
import collections
from copy import deepcopy
from collections import OrderedDict

# import third party lib
from lxml.builder import E
from lxml import etree

from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import RpcError
from jnpr.junos.exception import ConfigLoadError
from jnpr.junos.exception import RpcTimeoutError
from jnpr.junos.exception import ConnectTimeoutError
from jnpr.junos.exception import LockError as JnprLockError
from jnpr.junos.exception import UnlockError as JnrpUnlockError

# import NAPALM Base
import napalm.base.helpers
from napalm.base.base import NetworkDriver
from napalm.base.utils import py23_compat
from napalm.junos import constants as C
from napalm.base.exceptions import ConnectionException
from napalm.base.exceptions import MergeConfigException
from napalm.base.exceptions import CommandErrorException
from napalm.base.exceptions import ReplaceConfigException
from napalm.base.exceptions import CommandTimeoutException
from napalm.base.exceptions import LockError
from napalm.base.exceptions import UnlockError

# import local modules
from custom_napalm.junos.utils import junos_views


log = logging.getLogger(__file__)

from napalm.junos import JunOSDriver



class CustomJunOSDriver(JunOSDriver):
    """Custom NAPALM Cisco IOS Handler."""
    def say_hi(self):
        print("Hi")

    def get_layer2_neighbor_discovery_details(self, interface=''):
            """Detailed view of the LLDP neighbors."""
            lldp_neighbors = {}

            lldp_table = junos_views.junos_lldp_neighbors_detail_table(self.device)
            try:
                lldp_table.get()
            except RpcError as rpcerr:
                # this assumes the library runs in an environment
                # able to handle logs
                # otherwise, the user just won't see this happening
                log.error('Unable to retrieve the LLDP neighbors information:')
                log.error(py23_compat.text_type(rpcerr))
                return {}
            interfaces = lldp_table.get().keys()
            rpc_call_without_information = {
                'get_rpc': 'get-lldp-interface-neighbors',
                'interface_rpc': 'interface_device'
            }
            rpc_call_with_information = {
                'get_rpc': 'get-lldp-interface-neighbors-information',
                'interface_rpc': 'interface_name'
            }
            # get lldp neighbor by interface rpc for EX Series, QFX Series, J Series
            # and SRX Series is get-lldp-interface-neighbors-information,
            # and rpc for M, MX, and T Series is get-lldp-interface-neighbors
            # ref1: https://apps.juniper.net/xmlapi/operTags.jsp  (Junos 13.1 and later)
            # ref2: https://www.juniper.net/documentation/en_US/junos12.3/information-products/topic-collections/junos-xml-ref-oper/index.html  (Junos 12.3) # noqa
            # Exceptions:
            # EX9208    personality = SWITCH    RPC: <get-lldp-interface-neighbors><interface-device>
            # QFX10008  personality = SWITCH    RPC: <get-lldp-interface-neighbors><interface-device>
            # QFX5110-48S-4C personality = SWITCH RPC: <get-lldp-interface-neighbors><interface-device>
            # EX3400    personality = SWITCH    RPC: <get-lldp-interface-neighbors><interface-device>
            # SRX4100   personality = SRX_HIGHEND  RPC: <get-lldp-interface-neighbors><interface-device>
            #
            # This is very inconsistent and diverges from the documented behaviour.
            # The following object permits a per personality (a junos-pyEZ library feature) and per
            # model mapping to the correct rpc call
            rpc_call_map = {
                'default': rpc_call_with_information,
                'MX': {
                    'default': rpc_call_without_information
                },
                'M': {
                    'default': rpc_call_without_information
                },
                'T': {
                    'default': rpc_call_without_information
                },
                'PTX': {
                    'default': rpc_call_without_information
                },
                'SWITCH': {
                    'default': rpc_call_with_information,
                    'EX9208': rpc_call_without_information,
                    'EX3400': rpc_call_without_information,
                    'EX4300-48P': rpc_call_without_information,
                    'EX4600-40F': rpc_call_without_information,
                    'QFX5100-48S-6Q': rpc_call_without_information,
                    'QFX5110-48S-4C': rpc_call_without_information,
                    'QFX10002-36Q': rpc_call_without_information,
                    'QFX10008': rpc_call_without_information,
                    'EX2300-24P': rpc_call_without_information,
                    'EX2300-C-12P': rpc_call_without_information
                },
                'SRX_BRANCH': {
                    'default': rpc_call_with_information,
                    'SRX300': rpc_call_without_information
                },
                'SRX_HIGHEND': {
                    'default': rpc_call_without_information
                }
            }

            personality = self.device.facts.get('personality')
            model = self.device.facts.get('model')

            if rpc_call_map.get(personality) is not None:
                if rpc_call_map.get(personality).get(model) is not None:
                    lldp_table.GET_RPC = rpc_call_map.get(personality).get(model).get('get_rpc')
                    interface_variable = rpc_call_map.get(personality).get(model).get('interface_rpc')
                else:
                    lldp_table.GET_RPC = rpc_call_map.get(personality).get('default').get('get_rpc')
                    interface_variable = rpc_call_map.get(personality).get('default').get(
                        'interface_rpc')
            else:
                lldp_table.GET_RPC = rpc_call_map.get('default').get('get_rpc')
                interface_variable = rpc_call_map.get('default').get('interface_rpc')

            for interface in interfaces:
                interface_args = {interface_variable: interface}
                lldp_table.get(**interface_args)
                for item in lldp_table:
                    if interface not in lldp_neighbors.keys():
                        lldp_neighbors[interface] = []
                    lldp_neighbors[interface].append({  
                        'remote_system_name': item.remote_system_name,
                        'remote_port': item.remote_port,
                        'remote_management_ip_address': item.remote_management_ip_address,
                        'remote_system_enabled_capab': item.remote_system_enable_capab,
                        'remote_system_description': item.remote_system_description
                    })

            return lldp_neighbors