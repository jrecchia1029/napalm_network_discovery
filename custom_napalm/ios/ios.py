import re, json
import ipaddress


from napalm.ios.ios import IOSDriver

from napalm.base.helpers import (
    canonical_interface_name,
    transform_lldp_capab,
    textfsm_extractor, 
)

class CustomIOSDriver(IOSDriver):
    """Custom NAPALM Cisco IOS Handler."""
    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        super().__init__(hostname, username, password, timeout, optional_args)
        self.interface_map = {}

    def say_hi(self):
        print("Hi")

    def get_cdp_neighbor_discovery_details(self):
        cdp = {}
        cdp_interfaces = []
        command = 'show cdp neighbors detail'
        output = self._send_command(command)
        # Check if router supports the command
        if '% Invalid input' in output:
            return {}
        
        # Process the output to obtain just the CDP entries
        cdp_entries = textfsm_extractor(self, 'get_cdp_neighbor_discovery_details', output)
        if len(cdp_entries) == 0:
            return {}

        for idx, cdp_entry in enumerate(cdp_entries):
            local_intf = cdp_entry.pop('local_port')
            for field in cdp_entry:
                if 'not advertised' in cdp_entry[field]:
                    cdp_entry[field] = 'N/A'
            # Turn the interfaces into their long version
            local_intf = canonical_interface_name(local_intf)
            cdp.setdefault(local_intf, [])
            #create field remote_system_description from platform and version
            cdp_entry["remote_system_description"] = cdp_entry.pop("remote_platform").strip() + ", " + cdp_entry.pop("remote_system_os").strip()
            cdp[local_intf].append(cdp_entry)
        return cdp

    def get_lldp_neighbor_discovery_details(self):
        lldp = {}
        lldp_interfaces = []
        command = 'show lldp neighbors detail'
        output = self._send_command(command)
        # Check if router supports the command
        if '% Invalid input' in output:
            return {}
        # Process the output to obtain just the CDP entries
        lldp_entries = textfsm_extractor(self, 'get_lldp_neighbor_discovery_details', output)
        if len(lldp_entries) == 0:
            return {}

        for idx, cdp_entry in enumerate(lldp_entries):
            local_intf = cdp_entry.pop('local_port')
            for field in cdp_entry:
                if 'not advertised' in cdp_entry[field]:
                    cdp_entry[field] = 'N/A'
            # Turn the interfaces into their long version
            local_intf = canonical_interface_name(local_intf)
            lldp.setdefault(local_intf, [])
            lldp[local_intf].append(cdp_entry)
        return lldp

    def get_layer2_neighbor_discovery_details(self):
        layer2_neighbors = self.get_cdp_neighbor_discovery_details()
        lldp_neighbors = self.get_lldp_neighbor_discovery_details()
        for iface, neighbor_details in lldp_neighbors.items():
            if iface not in layer2_neighbors:
                layer2_neighbors[iface] = neighbor_details
        return layer2_neighbors
        

    def get_interface_broadcast_addresses(self):
        """
        Returns the broadcast ip addresses for each interface with an ip
        """
        broadcast_addresses = []
        ip_interfaces = self.get_interfaces_ip()
        for k, v in ip_interfaces.items():
            if 'ipv4' in v:
                ipv4_address_info = ip_interfaces[k]['ipv4']
                ip_addresses = ipv4_address_info.keys()
                for ip_address in ip_addresses:
                    netmask = ip_interfaces[k]['ipv4'][ip_address]['prefix_length']
                    ipv4_address = ipaddress.ip_interface("{}/{}".format(ip_address, netmask))
                    network = ipv4_address.network
                    broadcast_addresses.append(str(network.broadcast_address))
            if 'ipv6' in v:
                ipv4_address_info = ip_interfaces[k]['ipv6']
                ip_addresses = ipv4_address_info.keys()
                for ip_address in ip_addresses:
                    netmask = ip_interfaces[k]['ipv6'][ip_address]['prefix_length']
                    ipv4_address = ipaddress.ip_interface("{}/{}".format(ip_address, netmask))
                    network = ipv4_address.network
                    broadcast_addresses.append(str(network.broadcast_address))
        return broadcast_addresses