import re, json
import InterfaceObject
import pysnmp.hlapi
from pysnmp.entity.rfc3413.oneliner import cmdgen
from ipsoft_napalm import get_network_driver

# from napalm import get_network_driver


class Host():
    def __init__(self, **kwargs):
        """
        all keyword arguments will be lower case
        underscores, "_", will take the place of spaces
        """
        self.fqdn = kwargs.get("fqdn", None)
        self.ip_address = kwargs.get("ip_address", None)
        self.network = kwargs.get("network", None)
        self.hostname = kwargs.get("hostname", None)
        self.mac_address = kwargs.get("mac_address", None)
        self.vendor = kwargs.get("vendor", None)
        self.device_type = kwargs.get("device_type", None)
        self.model = kwargs.get("model", None)
        self.os_family = kwargs.get("os_family", None)
        self.os_type = kwargs.get("os_type", None)
        self.os_version = kwargs.get("os_version", None)
        self.serial_number = kwargs.get("serial_number", None)
        self.username = kwargs.get("username", None)
        self.password = kwargs.get("password", None)
        self.enable_password = kwargs.get("enable_password", None)
        self.network_device = kwargs.get("network_device", None)
        self.napalm_driver = kwargs.get("napalm_driver", None)
        self.netmiko_driver = kwargs.get("netmiko_driver", None)
        self.capabilities = kwargs.get("capabilities", None)
        self.description = kwargs.get("description", None)
        self._id = kwargs.get("_id", None)
        self.interfaces = kwargs.get("interfaces", None)
        self.layer_2_neighbors = None
        self.snmp_info = None

    def __str__(self):
        output = "FQDN: {}\nHostname: {}\nIP Address: {}\nMAC Address: {}\nVendor: {}\nDevice Type: {}\nModel: {}\nOS Family: {}\
                 \nOS Version: {}\nSerial Number: {}\nNetwork Device: {}\nNapalm Driver: {}\n"\
                 .format(self.fqdn, self.hostname, self.ip_address, self.mac_address, self.vendor, 
                            self.device_type, self.model, self.os_family, self.os_version, self.serial_number, self.network_device,
                                self.napalm_driver)
        return output

    def discover_self(self):
        if self.napalm_driver is None:
            print("Napalm Driver is not set")
            return False
        try:
            print("Starting discovery process for {}".format(self.ip_address))
            driver = get_network_driver(self.napalm_driver)
            print("Got driver for {}".format(self.ip_address))
            if self.ip_address is not None:
                device = driver(self.ip_address, self.username, self.password, 
                                    optional_args={"secret": self.password})
            elif self.hostname is not None:
                device = driver(self.hostname, self.username, self.password, 
                                    optional_args={"secret": self.password})
            else:
                return False

            #Open connection to device
            device.open()
            print("Successfully in device", self.ip_address)

            #Get and set self attributes with newly acquired info
            self_info = device.get_facts()
            self.set_attributes(self_info)
            print("Got basic facts for {}".format(self.ip_address))

            #Set subtype
            self.set_device_type()
            print("Set device type for {}".format(self.ip_address))

            #Set snmp_info
            snmp_info = device.get_snmp_information()
            self.set_snmp_info(snmp_info)
            print("Set snmp info for {}".format(self.ip_address))

            #Get layer2 neighbor information
            neighbor_info = device.get_layer2_neighbor_discovery_details()
            self.layer_2_neighbors = create_host_objects_from_layer2_neighbor_info(neighbor_info)
            print("Got layer 2 neighbor details for {}".format(self.ip_address))

            #Get interface information
            basic_interface_info = device.get_interfaces()
            ip_interface_info = device.get_interfaces_ip()
            #Combine basic interface info and  ip interface info into 1 JSON object
            local_interface_info = combine_interface_info(basic_interface_info, ip_interface_info)
            del(basic_interface_info, ip_interface_info)

            #Combine local interface info and neighbor into 1 JSON object
            complete_interface_info = combine_interface_and_neighbor_info(local_interface_info, neighbor_info)
            del(local_interface_info, neighbor_info)

            #Create interface objects
            self.interfaces = create_interface_objects_from_interface_info(device.hostname, complete_interface_info)
            del(complete_interface_info)
            print("Got interface objects for {}".format(self.ip_address))

            #Close connection
            device.close()
            print("Discovery process complete for {}".format(self.ip_address))
            return True
        except RuntimeError:
            print("Error occured during discovery for {}".format(self.ip_address))
            print(RuntimeError)
            return False


    def set_attributes(self, info):
        for k, v in info.items():
            if hasattr(self, k):
                try:
                    setattr(self, k, v)
                except:
                    continue

    def set_device_type(self):
        if self.capabilities is None:
            return
        if self.netmiko_driver and self.netmiko_driver == 'cisco_asa' or self.netmiko_driver == 'paloalto_panos':
            self.device_type = 'firewall'
            return
        # enms_subtypes = ['router', 'switch', 'firewall', 'server', 'host', 'antenna', 'optical switch']
        enms_mapper = {
            "R": 'router',
            'B': 'switch',
            'T': None, #Telephone
            'C': None, #DOCSIS Cable Device
            'W': None, #Want to add WLC option
            'P': None, #Want to add Repeater option
            'S': None, #Station
            'O': None, #other
            'Router': 'router',
            'Trans-Bridge': 'switch',
            'Source-Route-Bridge': 'switch',
            'Host': None, #Want to add a Host option
            'IGMP': None, #Don't know what that is
            'Repeater': None
        }
        if "," in self.capabilities:
            capabilities = [x.strip() for x in self.capabilities.split(",")]
        else:
            capabilities = self.capabilities.strip(" ")
        for capability in capabilities:
            if enms_mapper[capability] is not None:
                self.device_type = enms_mapper[capability]
                return 
        return None

    def set_snmp_info(self, snmp_info):
        community_strings = []
        if 'community' in snmp_info:
            for k in snmp_info["community"].keys():
                community_string = {
                    "community string": k,
                    "mode": snmp_info["community"][k]["mode"],
                    "acl": snmp_info["community"][k]["acl"]
                }
                community_strings.append(community_string)
        self.snmp_info = community_strings


    def get_napalm_driver(self):
        #Should be able to tell cisco from os_version
        if self.napalm_driver is None:
            if self.os_version and re.match(r'Cisco IOS XR', self.os_version):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'iosxr', 'IOS', 'IOS-XR', 'cisco_xr'
                return
            if self.os_version and re.match(r'Cisco Nexus', self.os_version):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'nxos', 'IOS', 'NX-OS', 'cisco_nxos'
                return
            if self.os_version and re.match(r'Cisco Adaptive Security Appliance', self.os_version):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'asa', 'IOS', 'ASA', 'cisco_asa'
                return
            if self.os_version and re.match(r'Cisco IOS XE', self.os_version):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'ios', 'IOS', 'IOS-XE', 'cisco_xe'
                return
            if (self.os_version and re.match(r'Cisco IOS', self.os_version)):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'ios', 'IOS', 'IOS', 'cisco_ios'
                return
            #Last ditch effort to identify as Cisco
            if self.os_family and re.match(r'(?i)(Cisco|^IOS|\sIOS\s|\sIOS$)', self.os_family):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'ios', 'IOS', 'IOS', 'cisco_ios'
                return
            #need remote_sys info to know that device is Juniper
            if self.os_family and re.search(r'(?i)(Juniper|JunOS)', self.os_family):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'junos', 'JunOS', 'JunOS', 'juniper_junos'
                return
            if self.os_family and re.search(r'(?i)(Arista|EOS)', self.os_family):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'eos', 'EOS', 'EOS', 'arista_eos'
                return
            if self.os_family and re.search(r'(?i)(Palo Alto|PAN-*OS)', self.os_family):
                self.napalm_driver, self.os_family, self.os_type, self.netmiko_driver = 'panos', 'PAN-OS', 'PAN-OS', 'paloalto_panos'
                return

def combine_interface_info(basic_interface_info, ip_interface_info):
    keys = ip_interface_info.keys()
    #Combine ip interface info with basic info
    for key in keys:
        interface_info = basic_interface_info[key]
        ip_interface_details = ip_interface_info[key]
        for ip_key in ip_interface_details.keys():
            interface_info[ip_key] = ip_interface_details[ip_key]
        basic_interface_info[key] = interface_info
    return basic_interface_info

def combine_interface_and_neighbor_info(interface_info, neighbor_info):
    """
    Takes the json neighbor info and merges it with the interface info to create one json object that can be used to create an Interface Object.
    """
    for iface, entry in neighbor_info.items():
        for info in entry:
            interface_info[iface]["destination_device"] = info["remote_system_name"]
            interface_info[iface]["destination_ip_address"] = info["remote_management_ip_address"]
            interface_info[iface]["destination_port"] = info["remote_port"]
    return interface_info

def create_host_objects_from_layer2_neighbor_info(neighbors_info):
    layer2_neighbors = []
    for iface, neighbor_info in neighbors_info.items():
        neighbor_info = neighbor_info[0]
        napalm_driver, os_family, os_type, netmiko_driver = get_os_details_from_system_description(
            neighbor_info["remote_system_description"])
        host_info = {}
        host_info["fqdn"] = neighbor_info["remote_system_name"]
        host_info["ip_address"] = neighbor_info["remote_management_ip_address"]
        host_info["capabilities"] = neighbor_info["remote_system_enabled_capab"]
        host_info["description"] = neighbor_info["remote_system_description"].strip()
        host_info["os_family"] = os_family
        host_info["os_type"] = os_type
        host_info["napalm_driver"] = napalm_driver
        host_info["netmiko_driver"] = netmiko_driver
        host_info["hostname"] = neighbor_info["remote_system_name"].split(".")[0]
        host = Host(**host_info)
        host.get_napalm_driver()
        layer2_neighbors.append(host)
    return layer2_neighbors

def create_interface_objects_from_interface_info(hostname, basic_interface_info):
    #turn complete interface info into list of interface objects
    interface_objects = []
    for k, v in basic_interface_info.items():
        interface = InterfaceObject.create_interface_from_get_interface_details(k, v, hostname) 
        interface_objects.append(interface)
    return interface_objects


def get_os_details_from_system_description(description):
    vendor_regexes = {
        r'(?i)IOS[-\s]*XR': {
            "napalm_driver": 'iosxr',
            "os_family": 'IOS',
            "os_type": 'IOS-XR',
            "netmiko_driver": 'cisco_xr'
        },
        r'(?i)NX[-\s]*OS': {
            "napalm_driver": 'nxos',
            "os_family": 'IOS',
            "os_type": 'NX-OS',
            "netmiko_driver": 'cisco_nxos'
        },
        r'Cisco ASA': {
            "napalm_driver": 'asa',
            "os_family": 'IOS',
            "os_type": 'ASA',
            "netmiko_driver": 'cisco_asa'
        },
        r'(?i)IOS[-\s]*XE': {
            "napalm_driver": 'ios',
            "os_family": 'IOS',
            "os_type": 'IOS-XE',
            "netmiko_driver": 'cisco_xe'
        },
        r'(?i)Cisco': {
            "napalm_driver": 'ios',
            "os_family": 'IOS',
            "os_type": 'IOS',
            "netmiko_driver": 'cisco_ios'
        },
        r'(?i)(Juniper|JunOS)': {
            "napalm_driver": 'junos',
            "os_family": 'JunOS',
            "os_type": 'JunOS',
            "netmiko_driver": 'juniper_junos'
        },
        r'(?i)(Arista|EOS)': {
            "napalm_driver": 'eos',
            "os_family": 'EOS',
            "os_type": 'EOS',
            "netmiko_driver": 'arista_eos'
        },
        r'(?i)(Palo Alto|PAN-*OS)': {
            "napalm_driver": "panos",
            "os_family": 'PAN-OS',
            "os_type": 'PAN-OS',
            "netmiko_driver": 'paloalto_panos'
        }
    }

    for vendor_re, info in vendor_regexes.items():
        if re.search(vendor_re, description):
            return info["napalm_driver"], info["os_family"], info["os_type"], info["netmiko_driver"]
        

def get_os_family(system_description):
    #Should be able to tell cisco from os_version
    if re.search(r'(?i)(Cisco|^IOS|\sIOS\s|\sIOS$)', system_description):
        return "IOS"
    elif re.search(r'(?i)(Juniper|^JunOS|\sJunOS\s|\sJunOS$)', system_description):
        return 'JunOS'
    elif re.search(r'(?i)(Arista|^EOS|\sEOS\s|\sEOS$)', system_description):
        return 'EOS'
    elif re.search(r'(?i)(Palo Alto|PAN-*OS)', system_description):
        return 'PAN-OS'
    else:
        return None