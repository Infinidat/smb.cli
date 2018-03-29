# Config File Explanation

## Summery
The parameters in the infinidat_config file are explained here with examples

## General guide lines

- The infinidat_config is a text file. Do not change its structure, prefixes, etc.
- The only values that are allowed to be changed are the text inside the ticks ("). For example, PoolName = "edit here"
- It is recommended to edit/configure the text file only after the installation completes.
  once you reached a working state with the config file it's recommanded not to modify it
- **If you messed up the file to much you can always delete it and the code would regenerate it**


## Config File Parameters

### TempDriveLetter
Doc: Default TEMPORARY mount volume.
This Volume has to be free before provisioning FS is used.
While FS provisioning takes place, all operations will be performed on TempDriveLetter then it would unmount itself ( freed ).

Examples for TempDriveLetter value:
"Z:\",
"X:\"

### MountRoot
Doc: The Root mount point for all InfiniBox Filesystem mounts.
When you create or attach a Filesystem it will be mounted to here. e.g.
You just created a new FS called new_fs and your MountRoot = "G:\"
Then it will be accessed via G:\new_fs

Examples for MountRoot value:
"D:\",
"G:\"

### PoolName
Doc: Pool name in the name of the Pool on the InfiniBox which all FileSystems and snapshots and users will be refereed to.
This means:
- The Username you are using will need access to this pool
- The pool should have enough space to create new Filesystems in it

Example for PoolName value:
"smb_pool"

### Cluster
Doc: The name of the cluster
Must be the same on the InfiniBox and on the MS cluster

Example for Cluster value:
"SMBCluster"

### IboxAddress
Doc: The InfiniBox resolvable DNS name or IP address

Example for IboxAddress values:
"172.16.1.1"
"InfiniBox-mgmt.some.company.int"

### FSRoleName
Doc: The name of the Microsoft FileServer role, created by the user.
All entities will be created under this Role name.
This means that all File Shares, File systems and Quotas will be linked to this Role.

Example for FSRoleName:
"smbfs"
