Param([Parameter(Mandatory=$true)]$Disk)
$ErrorActionPreference = "Stop"

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
