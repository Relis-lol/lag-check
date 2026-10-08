param([string]$Session)
$ErrorActionPreference = 'Stop'
try {
    $info = Get-Content -LiteralPath (Join-Path $Session 'session_info.json') -Raw | ConvertFrom-Json
    $start = [datetimeoffset]::Parse($info.start).LocalDateTime
    $end = [datetimeoffset]::Parse($info.end).LocalDateTime
    $events = @(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=$start;EndTime=$end} -ErrorAction Stop | Where-Object {
        $_.Level -in @(1,2,3) -or $_.ProviderName -match 'WHEA|Display|nvlddmkm|amdwddmg|Disk|storahci|stornvme|storport|NDIS|Tcpip|Netwtw|e1.*express|rt640|Kernel-Power|Kernel-PnP|WLAN'
    } | Sort-Object TimeCreated | ForEach-Object {
        [pscustomobject]@{ timestamp=$_.TimeCreated.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ'); id=$_.Id; level=$_.LevelDisplayName; provider=$_.ProviderName; message=$_.Message }
    })
    if ($events.Count) { $events | Export-Csv -LiteralPath (Join-Path $Session 'windows_events.csv') -NoTypeInformation -Encoding UTF8 }
    @{status='ok';count=$events.Count} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Session 'events_status.json') -Encoding UTF8
} catch {
    $empty = $_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*'
    @{status=$(if($empty){'ok'}else{'unavailable'});detail=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Session 'events_status.json') -Encoding UTF8
}
