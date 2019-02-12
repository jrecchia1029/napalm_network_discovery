import json


class Interface():
    def __init__(self, name, **kwargs):
        self.name = name
        self.description = kwargs.get("description", None)
        self.speed = kwargs.get("speed", None)
        self.subtype = kwargs.get("subtype", None) #type of link (i.e. fa, gi, optical_link)
        self.source_device = kwargs.get("source", None) #fqdn of device interface is on
        self.source_ip_address = kwargs.get("source_ip_address", None) #ip address of device interface is on
        self.source_ip_address_prefix = kwargs.get("source_address_prefix", None)
        self.source_mac_address = kwargs.get("source_mac_address", None) #mac address of device interface is on
        self.destination_device = kwargs.get("destination_device", None) #fqdn of device the interface is connected to
        self.destination_port = kwargs.get("destination_port", None) #port the interface is connected to on the destination device
        self.destination_ip_address = kwargs.get("destination_ip_address", None) #ip address of the port on the destination device

    def __str__(self):
        output = "Source: {}-{}\nSrc IP Address: {}\nDestination: {}-{}\nDest IP Address: {}"\
                    .format(self.source_device, self.name, self.source_ip_address, self.destination_device,
                        self.destination_port, self.destination_ip_address)
        return output
    
    def set_fields(self, interface_details):
        for k, v in interface_details.items():
            if hasattr(self, k):
                try:
                    setattr(self, k, v)
                except:
                    continue

def create_interface_from_get_interface_details(name, interface_details, hostname):
    interface = Interface(name)
    interface_details['source_device'] = hostname
    if 'mac_address' in interface_details:
        interface_details['source_mac_address'] = interface_details.pop('mac_address')
    ip_protocols = ["ipv4", "ipv6"]
    for protocol in ip_protocols:
        if protocol in interface_details and interface_details[protocol] != {}:
            for k1, v1 in interface_details[protocol].items():
                ip_address = k1
                for k2, v2 in v1.items():
                    prefix_length = v2
            interface_details['source_ip_address'] = ip_address
            interface_details['source_ip_address_prefix'] = prefix_length
    interface.set_fields(interface_details)
    return interface