Value LOCAL_PORT (.*)
Value REMOTE_SYSTEM_NAME (.*)
Value REMOTE_PORT (.*)
Value REMOTE_MANAGEMENT_IP_ADDRESS (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
Value REMOTE_SYSTEM_ENABLED_CAPAB (.*)
Value REMOTE_SYSTEM_DESCRIPTION (.+)

Start
  ^Local Intf\s*?[:-]\s+${LOCAL_PORT}
  ^Port id\s*?[:-]\s+${REMOTE_PORT}
  ^System Name\s*?[:-]\s+${REMOTE_SYSTEM_NAME}
  # We need to change state to capture the entire next line
  ^System Description: -> Description
  ^Enabled Capabilities\s*?[:-]\s+${REMOTE_SYSTEM_ENABLED_CAPAB}
  ^Management Addresses\s*?[:-]\s* -> REMOTE_MANAGEMENT_IP_ADDRESS

Description
  # Capture the entire line and go back to Neighbor state
  ^${REMOTE_SYSTEM_DESCRIPTION} -> Start

REMOTE_MANAGEMENT_IP_ADDRESS
  ^\s+IP\s*?[:-]\s+${REMOTE_MANAGEMENT_IP_ADDRESS} -> Record Start