Param([Parameter(Mandatory=$true)][int]$DiskNumber)

. 'C:\Program Files\INFINIDAT\smb.cli\powershell\lib.ps1'
. 'C:\Program Files\INFINIDAT\smb.cli\powershell\lib_cluster.ps1'
$LogID = $MyInvocation.MyCommand.Name.Substring(0, $MyInvocation.MyCommand.Name.Length - 4)

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
# check if disk is already in the cluster
# check mountpoint
ExecAssertNLog ("Get-Disk -Number " + $Disknumber + "| Get-ClusterAvailableDisk | Add-ClusterDisk") -from $LogID
$VolumeNameArray = RenameClusterDisks -Disk $Disk
$cluster_disk = Get-ClusterResource | where resourcetype -eq "Physical Disk" | where ownergroup -eq "Available Storage"
if ( $cluster_disk.length -ne 1 ) {
    LogErrorAndExit "Something not right" -from $LogID
}
# Need to add back ExecAssertNLog not working because $cluster_disk has spaces
move-ClusterResource -Name $cluster_disk  -Group $INFINIDAT_CONFIG.FSRoleName
$MountPath = Join-Path $INFINIDAT_CONFIG.MountRoot $VolumeNameArray[1]
$Partition | Add-PartitionAccessPath -AccessPath $MountPath -PassThru -ErrorAction Stop
return $Partition
