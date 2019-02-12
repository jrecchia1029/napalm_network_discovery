#!/home/jrecchia/.pyenv/shims/python
import json
import re
import mysqldb.mysqldb_functions as mysqldb
from queue import Queue
from threading import Thread
from initial_nmap_discovery import initial_discovery
from HostObject import Host

devices_to_check = [] #list of devices added from discover neighbors
checked_devices = [] #list of devices already investigated


def add_neighbors_to_check_list(network_device, hosts_to_check, working_list):
    layer_2_neighbors = network_device.layer_2_neighbors
    found_neighbor_flag = False
    if layer_2_neighbors is not None:
        for host in layer_2_neighbors:
            #Check if host is already in Database
            if mysqldb.check_if_device_in_db(host) == False:
                #Check if host is in the working list (already in the process of being discovered)
                for device in working_list:
                    if host.ip_address == device.ip_address:
                        found_neighbor_flag = True
            if found_neighbor_flag == False:
                print("Adding {} to hosts to check list".format(host.ip_address))
                hosts_to_check.put(host)
            else:
                #reset found_neighbor flag
                found_neighbor_flag = False

def remove_device_from_working_list(network_device, working_list):
    for i, device in enumerate(working_list):
        if device.fqdn and network_device.fqdn and device.fqdn == network_device.fqdn:
            del working_list[i]
            break
        elif device.ip_address and network_device.ip_address and device.ip_address == network_device.ip_address:
            del working_list[i]
            break

def check_if_device_is_in_list(network_device, list_to_check):
    found_neighbor_flag = False
    for host in list_to_check:
        if (host.ip_address == network_device.ip_address and host.ip_address is not None) or (host.fqdn == network_device.fqdn and host.fqdn is not None):
            found_neighbor_flag = True
    if found_neighbor_flag == False:
        return False
    else:
        return True

def threader(q):
    while True:
        worker = q.get()
        #Get more information on device
        get_device_info(worker, q)
        q.task_done()

def get_device_info(network_device, q):
    network_device.username = 'jrecchia'
    #For testing
    if network_device.napalm_driver == 'junos':
        network_device.password = 'password!'
    else:
        network_device.password = 'password'

    try:
        ##check if device is in seen list or working list
        if check_if_device_is_in_list(network_device, seen_list) == True:
            print("{} is already present in the list of seen devices".format(network_device.ip_address))
            return
        if check_if_device_is_in_list(network_device, working_list) == True:
            print("{} is already present in the list of devices currently being discovered".format(network_device.ip_address))
            return

        #Add device to working list
        working_list.append(network_device)

        #Get napalm_driver if necessary
        network_device.get_napalm_driver()

        #discover device details
        successful_discovery_flag = network_device.discover_self()
        seen_list.append(network_device)
        if successful_discovery_flag == False:
            return

        #Add neighbors to check list and remove this device from working list
        add_neighbors_to_check_list(network_device, q, working_list)
        
        #Add host and neighbors to database
        sql_device_data = mysqldb.sqlDeviceStructure(network_device)
        sql_device_data.update()
        for host in network_device.layer_2_neighbors:
            sql_device_data = mysqldb.sqlDeviceStructure(host)
            sql_device_data.update()
            sql_neighbor_data = mysqldb.sqlLayer2NeighborsStructure(network_device, host)
            sql_neighbor_data.update()
        for iface in network_device.interfaces:
            sql_interface_data = mysqldb.sqlLinkStructure(iface)
            sql_interface_data.update()


    except:
        print("Couldn't get device info for {}".format(network_device.ip_address))
        return
    finally:
        #Clean up working list and seen list
        remove_device_from_working_list(network_device, working_list)
        print("Working list length:", len(working_list))
        print("Seen list length:", len(seen_list))


working_list = []
seen_list = []

def main():
    # perform initial LAN discovery and update/insert device info into database
    global working_list
    hosts_to_check = Queue(maxsize=0)

    for x in range(50): #Create 50 threads
        #Get more information on device
        t = Thread(target=threader, args=(hosts_to_check,))
        t.daemon = True
        t.start()
    
    hosts_discovered = initial_discovery()

    for host in hosts_discovered:
        hosts_to_check.put(host)

    hosts_to_check.join()


if __name__ == "__main__":
    main()