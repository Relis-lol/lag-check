$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$interfaces = @(Get-NetIPInterface -AddressFamily IPv4)
$routes = @(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Where-Object { $_.NextHop -ne '0.0.0.0' } | ForEach-Object {
    $r = $_
    $i = $interfaces | Where-Object { $_.InterfaceIndex -eq $r.InterfaceIndex -and $_.ConnectionState -eq 'Connected' } | Select-Object -First 1
    if ($i) { [pscustomobject]@{ gateway=$r.NextHop; index=$r.InterfaceIndex; alias=$r.InterfaceAlias; metric=([int]$r.RouteMetric+[int]$i.InterfaceMetric) } }
} | Sort-Object metric)
[pscustomobject]@{ gateway=($routes | Select-Object -First 1); routes=$routes } | ConvertTo-Json -Depth 5 -Compress
