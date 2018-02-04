$ErrorActionPreference = "Stop"
$SmbRoot = "C:\Program Files\INFINIDAT\smb.cli"
$INFINIDAT_CONFIG = (Get-Content -raw 'C:\Program Files\INFINIDAT\smb.cli\config\infinidat_config' | iex)
$ROTATE_SIZE = 3000000  # 3MB
$LogDir = (Join-Path $SmbRoot "Logs")
$Logfile = (Join-Path $LogDir "smb_powershell.log")
$LogID = $MyInvocation.MyCommand.Name.Substring(0, $MyInvocation.MyCommand.Name.Length - 4)


function LogWrite([string]$logstring, [string]$from=$LogID, $level="INFO", $silent=$false)
{
    $AVAILABLE_LOG_LEVELS = @("DEBUG", "INFO", "WARN", "ERROR")
    if ($AVAILABLE_LOG_LEVELS -notcontains $level) {
        Write-Host "Bad use of LogWrite"
        exit 1
    }
    if ( -NOT $silent ) {
        Write-Host $logstring
    }
    $date = Get-Date -Format o
    Add-content $Logfile -value ($date + " - " + $level + ": " +"(" + $from + ")" + $logstring)
}


function LogErrorAndExit([string]$message, $from) {
    # not sure if works
    LogWrite $message -level "ERROR" -from $from
    exit 1
}


function ExecAssertNLog([string]$cmd, $from) {
    # logs the command we execute using and make stop is respected
    LogWrite ("executing: " + $cmd + " -ErrorAction Stop") -silent $true -from $from
    try {
        $return_object = iex ( $cmd + " -ErrorAction Stop")
        if ( $? ) {
            return $return_object
        }
        else {
            LogErrorAndExit ($cmd + " Failed with exit status False") -from $from
        }
    }

    catch {
        LogErrorAndExit $_ -from $from
    }
}

function CreateOrRotateLogs {
    if ( -NOT (Test-Path $LogDir)) {
        mkdir $LogDir
    }
    if (Test-Path $Logfile) {
        $log_obj = Get-Item $Logfile
        if ( $log_obj.Length -gt $ROTATE_SIZE ) {
            LogWrite ( "log size is: " + $log_obj.Length + "KB, Rotating logs.") -level "DEBUG"
            Rename-Item -Path (Join-Path $LogDir "old_smb_powershell.log") -NewName "to_be_deleted_smb.log"
            Rename-Item -Path $Logfile -NewName "old_smb_powershell.log"
            Remove-Item (Join-Path $LogDir "to_be_deleted_smb.log")
        }
    }
}

CreateOrRotateLogs
