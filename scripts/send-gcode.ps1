[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,

    [string]$Port = "COM3",
    [int]$Baud = 115200,
    [int]$StartupDelayMs = 2000,
    [int]$ReadTimeoutMs = 3000,
    [switch]$ContinueOnArduinoError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $FilePath)) {
    throw "GCode file not found: $FilePath"
}

$resolvedPath = (Resolve-Path -Path $FilePath).Path

$port = New-Object System.IO.Ports.SerialPort $Port, $Baud, "None", 8, "One"
$port.NewLine = "`n"
$port.ReadTimeout = $ReadTimeoutMs
$port.WriteTimeout = $ReadTimeoutMs

$sentCount = 0
$lineNumber = 0

try {
    $port.Open()

    # Arduino Uno resets when serial opens; wait for firmware startup text.
    Start-Sleep -Milliseconds $StartupDelayMs
    $port.DiscardInBuffer()

    Write-Host "Streaming '$resolvedPath' to $Port at $Baud baud..."

    foreach ($rawLine in Get-Content -Path $resolvedPath -Encoding UTF8) {
        $lineNumber += 1
        $line = $rawLine.Trim()

        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        if ($line.StartsWith(";") -or $line.StartsWith("#")) {
            continue
        }

        $port.WriteLine($line)
        $sentCount += 1

        try {
            $response = $port.ReadLine().Trim()
        }
        catch [System.TimeoutException] {
            throw "Timeout waiting for Arduino response after line $lineNumber: $line"
        }

        if ($response -match "^(?i)err") {
            $message = "Arduino error at line $lineNumber: $line`nResponse: $response"
            if ($ContinueOnArduinoError) {
                Write-Warning $message
                continue
            }
            throw $message
        }
    }

    Write-Host "Done. Sent $sentCount commands from $lineNumber input lines."
}
finally {
    if ($port -and $port.IsOpen) {
        $port.Close()
    }
    if ($port) {
        $port.Dispose()
    }
}
