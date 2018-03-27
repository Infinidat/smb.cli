Param([Parameter(Mandatory=$true)][int]$DiskNumber,
      [Parameter(Mandatory=$true)][string]$MountPath)

# Map Volume to Mountpoint
<# Param has to be the in the first line if used.
   I couldn't make PowerShell map directly to mount point therefore,
   I create a regular drive then remove it's drive letter.
   Default drive letter is defined at $INFINIDAT_CONFIG.TempDriveLetter
#>

. 'C:\Program Files\INFINIDAT\smb.cli\src\smb\cli\powershell\lib.ps1'
. 'C:\Program Files\INFINIDAT\smb.cli\src\smb\cli\powershell\lib_cluster.ps1'

$ProgressPreference='SilentlyContinue'
$LogID = $MyInvocation.MyCommand.Name.Substring(0, $MyInvocation.MyCommand.Name.Length - 4)
Update-HostStorageCache

if ( Test-Path $INFINIDAT_CONFIG.TempDriveLetter ) {
    LogErrorAndExit ($INFINIDAT_CONFIG.TempDriveLetter + "Already exist, That's a problem" ) -from $LogID
}

function TestDiskIsValid {
    $disk = Get-Disk -Number $DiskNumber
    if ( $disk.PartitionStyle -ne 'RAW' ) {
        LogErrorAndExit ("Disk " + $DiskNumber + " has data on it") -from $LogID
    }
    if ( $disk.Manufacturer -ne 'NFINIDAT' ) {
        LogErrorAndExit ("Disk " + $DiskNumber + " is not an InfiniBox Disk") -from $LogID
    }
    return $disk
}


function PrepVolume {
    $MountName = Split-Path $MountPath -Leaf
    $disk = TestDiskIsValid
    ExecAssertNLog ("Initialize-Disk -Number " + $DiskNumber + " -PartitionStyle GPT -PassThru") -from $LogID
    $NewPartition = ExecAssertNLog ("New-Partition -DiskNumber " + $DiskNumber + " -UseMaximumSize  -DriveLetter " `
                    + $INFINIDAT_CONFIG.TempDriveLetter[0] ) -from $LogID
    ExecAssertNLog ("Remove-PartitionAccessPath -DiskNumber " + $DiskNumber + " -PartitionNumber 2 -AccessPath " `
                    + $INFINIDAT_CONFIG.TempDriveLetter.Substring(0,2)) -from $LogID
    $NewPartition | Format-Volume -FileSystem NTFS -NewFileSystemLabel $MountName  -AllocationUnitSize 65536 -Confirm:$false -ErrorAction Stop
}

# Inorder to prevent windows popup when a new volume partition is created we are disabling the ShellHWDetection service
ExecAssertNLog "Stop-Service -Name ShellHWDetection" -from $LogID
PrepVolume
ExecAssertNLog "Start-Service -Name ShellHWDetection" -from $LogID
