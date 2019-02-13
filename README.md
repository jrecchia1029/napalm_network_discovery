# napalm_network_discovery

Discovers devices at layer 2 and keeps track of connections in database.

The autodiscovery.py file uses default and custom napalm get methods to perform network discovery.  The script only requires a set of read-only credentials to discover devices via lldp and cdp neighbor information.

Supports JunOS, IOS, and EOS.
