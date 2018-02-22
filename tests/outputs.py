not_active_node = '''INFO: Running Prechecks...\r\n\x1b[31mERROR: The Node you are running on is NOT the Active Cluster Node\x1b[39m\r\n'''

fs_query_empty = '''INFO: Running Prechecks...
No volumes are mapped'''

fs_query_header = 'Name               Mount              Size         Used Size    Snaps   Shares'

fs_delete = 'Volume {} was deleted'

share_query_header = 'ShareName      FSName         Path                     Quota       UsedQuota   FilesystemFree'

bad_share_resize = 'No use in limiting share to'

already_shared = "WARNING: '{}' is Already Shared, Lucky You ?!"

share_created = "INFO: '{}' Share Created"

share_deleted =  "INFO: {} Share Deleted"

no_shares = 'INFO: No Share Are Defined'
