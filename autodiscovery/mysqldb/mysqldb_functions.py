import mysql.connector
from mysql.connector import errorcode

config = { 
  'user': 'root',
  'password': 'password',
  'host': '127.0.0.1',
  'database': 'autodiscovery',
  'raise_on_warnings': True
}


class sqlDeviceStructure():
    def __init__(self, HostObject):
        self.host_name = HostObject.hostname
        self.description = HostObject.description
        self.subtype = HostObject.device_type
        self.ip_address = HostObject.ip_address
        self.mac_address = HostObject.mac_address
        self.vendor = HostObject.vendor
        self.model = HostObject.model
        self.operating_system = HostObject.os_type 
        self.os_version = HostObject.os_version
        self.serial_number = HostObject.serial_number
        self.napalm_driver = HostObject.napalm_driver
        self.netmiko_driver = HostObject.netmiko_driver
        # self.username = HostObject.username
        # self.password = HostObject.password
        # self.enable_password = HostObject.enable_password
        self.fqdn = HostObject.fqdn
        self.id = get_device_id(HostObject.hostname)
    
    def update(self):
        device_info = self.__dict__
        print(self.host_name)
        print(self.id)
        if self.id is None:
            #INSERT
            del device_info["id"]
        placeholder = ", ".join(["%s"] * len(device_info))
        sql_statement = "insert into `{table}` ({columns}) values ({values});".format(table='device_inventory', columns=",".join(device_info.keys()), values=placeholder)
        print(sql_statement)
        print(list(device_info.values()))
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute(sql_statement, list(device_info.values()))
        connection.commit()
        connection.close()

    
    def delete(self):
        sql_statement = "DELETE FROM device_inventory where id = {}".format(self.id)
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute(sql_statement)
        connection.commit()
        connection.close()

class sqlLinkStructure():
    def __init__(self, InterfaceObject):
        self.name = "{}-{} to {}-{}".format(
            InterfaceObject.source_device, InterfaceObject.name, InterfaceObject.destination_device, InterfaceObject.destination_port
            )
        self.source_device_id = get_device_id(InterfaceObject.source_device)
        self.destination_device_id = get_device_id(InterfaceObject.destination_device)
        self.source_device_port = InterfaceObject.name
        self.destination_device_port = InterfaceObject.destination_port
        self.speed = InterfaceObject.speed
        self.description = InterfaceObject.description
        self.id = get_interface_id(self.source_device_id, self.source_device_port)

    def update(self):
        link_info = self.__dict__
        if self.id is None:
            #INSERT
            del link_info["id"]
        placeholder = ", ".join(["%s"] * len(link_info))
        sql_statement = "insert into `{table}` ({columns}) values ({values});".format(table='link_inventory', columns=",".join(link_info.keys()), values=placeholder)
        print(sql_statement)
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute(sql_statement, list(link_info.values()))
        connection.commit()
        connection.close()

    def delete(self):
        sql_statement = "DELETE FROM link_inventory where id = {}".format(self.id)
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute(sql_statement) 
        connection.commit()
        connection.close()

class sqlLayer2NeighborsStructure():
    def __init__(self, subject, neighbor):
        self.subject_device_id = get_device_id(subject.hostname)
        self.neighbor_device_id = get_device_id(neighbor.hostname)

    def update(self):
        neighbor_info = self.__dict__
        placeholder = ", ".join(["%s"] * len(neighbor_info))
        sql_statement = "insert into `{table}` ({columns}) values ({values});".format(table='layer_2_neighbors', columns=",".join(neighbor_info.keys()), values=placeholder)
        print(sql_statement)
        connection = create_connection()
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute(sql_statement, list(neighbor_info.values()))
        connection.commit()
        connection.close()

    def delete(self):
        sql_statement = "DELETE FROM layer_2_neighbors WHERE subject_device_id = {} AND neighbor_device_id={};".format(
            self.subject_device_id, self.neighbor_device_id
        )
        execute_query(sql_statement)
        
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    return connection

def get_device_id(device_name):
    sql_statement = "SELECT id FROM device_inventory WHERE host_name = '%s';" % (device_name)
    results = execute_query(sql_statement)
    try:
        result = results.fetchone()
    except:
        result = None
    return result

def get_interface_id(device_id, port):
    sql_statement = "SELECT id FROM link_inventory WHERE source_device_id = %s AND source_device_port='%s';" % (device_id, port)
    results = execute_query(sql_statement)
    try:
        result = results.fetchone()
    except:
        result = None
    return result

def check_if_device_in_db(host):
    results = get_device_id(host.hostname)
    try:
        result = results.fetchone()
        return True
    except:
        result = None
        return False
        
def execute_query(query):
    print(query)
    connection = None
    try:
        connection = mysql.connector.connect(**config)
        cur = connection.cursor()
        cur.execute(query)
        results = cur.fetchall()
        return results
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    finally:
        if connection is not None:
            connection.close()
