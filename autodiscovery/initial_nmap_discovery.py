import nmap
import netifaces
import ipaddress
from HostObject import Host

possible_network_devices = ["bridge", "broadband router", "firewall",  "hub", "load balancer", "PBX", "proxy server", "router", "switch", "WAP"]

def convert_ip_to_binary(ip_address):
    binary_string = ""
    octets = ip_address.split(".")
    for octet in octets:
        binary_octet = str(bin(int(octet))).replace("0b", "")
        if len(binary_octet) < 8:
            remaining_zeros = 8 - len(binary_octet)
            for i in range(remaining_zeros):
                binary_octet += "0"
        elif len(binary_octet) > 8:
            print("Invalid IP Address")
            return None
        binary_string += binary_octet
    return binary_string

def get_ip_interfaces():
    interfaces = netifaces.interfaces()
    ip_interfaces = []
    #get local layer 3 interface details
    for interface in interfaces:
        interface_info = netifaces.ifaddresses(interface)
        try:
            for iface in interface_info[2]:
                ip_interfaces.append(iface)
        except:
            pass
        try:
            for iface in interface_info[30]:
                ip_interfaces.append(iface)
        except:
            pass
    return ip_interfaces

def get_ip_interface_objects(ip_interfaces_info):
    interface_objects = []
    for interface_details in ip_interfaces_info:
        interface = ipaddress.IPv4Interface(interface_details["addr"] + "/" + str(convert_ip_to_binary(interface_details["netmask"]).count("1")))
        interface_objects.append(interface)
    return interface_objects

def get_hosts_on_network(ip_interfaces):
    nmScan = nmap.PortScanner()
    hosts_on_network = []
    #get other hosts on local networks
    for interface in ip_interfaces:
        if str(interface.ip) != "127.0.0.1":
            #scan ports 22 and 23 of network that interface is on
            results = nmScan.scan(str(interface.network), '22-23', arguments='-O')
            keys = [key for key in results["scan"].keys()]
            for key in keys:
                results["scan"][key]["network"] = str(interface.network)
                hosts_on_network.append(results["scan"][key])
    return hosts_on_network

def get_host_objects(host_details):
    hosts_on_network = []
    for host in host_details:
        # if host["status"]["state"] != "down":
        #     print("-------------------------------------")
        #     print(json.dumps(host, indent=4))
        try:
            hostname = host["hostnames"][0]["name"] if len(host["hostnames"][0]["name"]) > 0 else None
        except:
            hostname = None
        try:
            network = host["network"]
        except:
            network = None
        try:
            ip_address = host["addresses"]["ipv4"] if len(host["addresses"]["ipv4"]) > 0 else None
        except:
            ip_address = None
        try:
            mac = host["addresses"]["mac"]
        except:
            mac = None
        try:
            vendor = host["osmatch"][0]["osclass"][0]["vendor"]
        except:
            vendor = None
        try:
            os_family = host["osmatch"][0]["osclass"][0]["osfamily"]
        except:
            os_family = None
        try:
            dev_type = host["osmatch"][0]["osclass"][0]["type"]
            network_device = dev_type in possible_network_devices
        except:
            network_device = None
        new_host = Host(ip_address=ip_address, hostname=hostname, mac_address=mac, vendor=vendor, os_family=os_family, network=network, network_device=network_device)
        new_host.get_napalm_driver()
        hosts_on_network.append(new_host)
    return hosts_on_network

def initial_discovery():
    #get device's ip interfaces
    ip_interfaces = get_ip_interfaces()

    #convert ip interface information into interface object
    ip_interfaces = get_ip_interface_objects(ip_interfaces)
    
    #get hosts on interface networks
    hosts_on_network = get_hosts_on_network(ip_interfaces)

    #convert host information into Host object
    hosts_on_network = get_host_objects(hosts_on_network)
    #filter for network devices
    network_devices = []
    for host in hosts_on_network:
        if host.network_device == True:
            network_devices.append(host)
 
    return network_devices 
    