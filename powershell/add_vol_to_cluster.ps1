Param([Parameter(Mandatory=$true)][int]$DiskNumber)

. 'C:\Program Files\INFINIDAT\smb.cli\powershell\lib.ps1'
. 'C:\Program Files\INFINIDAT\smb.cli\powershell\lib_cluster.ps1'
$LogID = $MyInvocation.MyCommand.Name.Substring(0, $MyInvocation.MyCommand.Name.Length - 4)
$ADD_VOL_TO_CLUSTER_RETRY_COUNT = 5
Update-HostStorageCache
# Pre-checks
$Disk = Get-Disk -Number $DiskNumber
$PartitionStyle =  $Disk | Select-Object -ExpandProperty PartitionStyle
if ( $PartitionStyle -ne 'GPT' ) {
    LogErrorAndExit ("Unexpected Partition type on Disk: "+ $DiskNumber )
}

$NumberofPartitions = Get-Partition -DiskNumber $DiskNumber |Measure-Object
if ( $NumberofPartitions.count -ne 2 ) {
    LogErrorAndExit ("Unexpected Partition type on Disk: "+ $DiskNumber )
}

$Partition = ExecAssertNLog ("Get-Partition -DiskNumber " + $DiskNumber + " -PartitionNumber 2" ) -from $LogID
# TODO: check if disk is already in the cluster

# Add-ClusterDisk fails once in a while due to slow servers so we are retrying
foreach ( $i in 1..$ADD_VOL_TO_CLUSTER_RETRY_COUNT ) {
    $cluster_avail_disks_before = Get-ClusterResource | where resourcetype -eq "Physical Disk" | where ownergroup -eq "Available Storage"
    $ErrorActionPreference = "SilentlyContinue"
    Get-Disk -Number $DiskNumber | Get-ClusterAvailableDisk | Add-ClusterDisk
    $ErrorActionPreference = "Stop"
    $cluster_avail_disks_after = Get-ClusterResource | where resourcetype -eq "Physical Disk" | where ownergroup -eq "Available Storage"
    LogWrite -logstring ("Before: " + $cluster_avail_disks_before.length + "After:" + $cluster_avail_disks_after.length) -from -$LogID
        if ( $cluster_avail_disks_before.length -lt $cluster_avail_disks_after.length ) {
            break
        else {
            sleep 2
        }
        }
}
$VolumeNameArray = RenameClusterDisks -Disk $Disk
$cluster_disk = Get-Disk -Number $DiskNumber| Get-ClusterResource
move-ClusterResource -Name $cluster_disk.Name  -Group $INFINIDAT_CONFIG.FSRoleName
$MountPath = Join-Path $INFINIDAT_CONFIG.MountRoot $VolumeNameArray[1]
$MountPath = $MountPath.ToLower() + '\'
$AccessPaths =  foreach ($Path in $Partition.AccessPaths) { $Path.ToLower() }
LogWrite ("MountPath: " + $MountPath + "len:" + $AccessPaths.Count + "AccessPaths: " + $AccessPaths) -from $LogID
if ( $MountPath -NotIn $AccessPaths) {
    # still Fails once in a while so we allow errors in this command and verify all is ok in python
    $Partition | Add-PartitionAccessPath -AccessPath $MountPath -PassThru -ErrorAction SilentlyContinue
}
LogWrite ("AccessPaths: " + $AccessPaths) -from $LogID
return $Partition
