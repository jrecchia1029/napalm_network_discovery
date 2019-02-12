Value LOCAL_PORT (.*)
Value REMOTE_SYSTEM_NAME (.*)
Value REMOTE_PORT (.+)
Value REMOTE_MANAGEMENT_IP_ADDRESS (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
Value REMOTE_SYSTEM_ENABLED_CAPAB (.*)
Value REMOTE_PLATFORM (.+)
Value REMOTE_SYSTEM_OS (.+)

Start
  ^Device ID\s*?[:-]\s+${REMOTE_SYSTEM_NAME}
  ^Platform\s*?[:-]\s+${REMOTE_PLATFORM},\s+Capabilities\s*?[:-]\s+${REMOTE_SYSTEM_ENABLED_CAPAB}
  ^Interface\s*?[:-]\s+${LOCAL_PORT},\s+Port\sID\s\(outgoing\sport\)\s*?[:-]\s+${REMOTE_PORT}
  ^Version\s*?[:-]\s* -> REMOTE_SYSTEM_OS 
  ^Management address\(es\)\s*?[:-]\s* -> REMOTE_MANAGEMENT_IP_ADDRESS

REMOTE_SYSTEM_OS
  ^${REMOTE_SYSTEM_OS} -> Start

REMOTE_MANAGEMENT_IP_ADDRESS
  ^\s+IP address[:-]\s+${REMOTE_MANAGEMENT_IP_ADDRESS}
  ^.* -> Record Start