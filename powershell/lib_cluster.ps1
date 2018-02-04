$ErrorActionPreference = "Stop"

$LogID = $MyInvocation.MyCommand.Name.Substring(0, $MyInvocation.MyCommand.Name.Length - 4)
function DiskToClusterDiskResource ($Disk) {
    # $Disk object is return of Get-Disk
    # based on idea from http://blog.powershell.no/tag/rename-cluster-diskscim-cmdlets/
    $ClusterDisks =  Get-CimInstance -ClassName MSCluster_Resource -Namespace root/mscluster -Filter "type = 'Physical Disk'"
    $DiskPartition = $Disk | Get-Partition -PartitionNumber 2
    foreach ($ClusterDisk in $ClusterDisks) {
        $DiskResource = Get-CimAssociatedInstance -InputObject $ClusterDisk -ResultClass MSCluster_DiskPartition
        if ( $DiskResource.VolumeGuid -eq $DiskPartition.Guid.Trim('{','}')) {
            return $DiskResource, $ClusterDisk
        }
    }
}


function RenameClusterDisks ($Disk) {
    # $Disk object type of Get-Disk
    $DiskResource, $ClusterDisk = DiskToClusterDiskResource -Disk $Disk
    if ( $DiskResource ) {
        Invoke-CimMethod -InputObject $ClusterDisk -MethodName Rename -Arguments @{newName = $DiskResource.VolumeLabel}
        return $DiskResource.VolumeLabel     # returns array with the new volume label
    }
}
