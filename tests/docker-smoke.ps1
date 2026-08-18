[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8080',
    [string]$ComposeOverride = 'docker-compose.local.yml'
)

$ErrorActionPreference = 'Stop'

function Test-ActualHostPublisher {
    param(
        [AllowNull()]
        [object]$Publisher
    )

    if ($null -eq $Publisher) {
        return $false
    }

    $url = ''
    $urlProperty = $Publisher.PSObject.Properties['URL']
    if ($null -ne $urlProperty) {
        $url = [string]$urlProperty.Value
    }

    $publishedPort = 0
    $publishedPortProperty = $Publisher.PSObject.Properties['PublishedPort']
    if ($null -ne $publishedPortProperty) {
        $parsedPort = 0
        if ([int]::TryParse([string]$publishedPortProperty.Value, [ref]$parsedPort)) {
            $publishedPort = $parsedPort
        }
    }

    return -not [string]::IsNullOrWhiteSpace($url) -or $publishedPort -gt 0
}

function Get-ComposeServices {
    $composeOutput = & docker compose -f docker-compose.yml -f $ComposeOverride ps --format json
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose ps failed with exit code $LASTEXITCODE."
    }

    $json = ($composeOutput -join [Environment]::NewLine).Trim()
    if ([string]::IsNullOrWhiteSpace($json)) {
        throw 'docker compose ps returned no service data.'
    }

    try {
        return @(ConvertFrom-Json -InputObject $json)
    }
    catch {
        $services = @()
        foreach ($line in ($json -split "`r?`n")) {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                $services += ConvertFrom-Json -InputObject $line
            }
        }
        return $services
    }
}

$root = Invoke-WebRequest -UseBasicParsing -Uri $BaseUrl
if ($root.StatusCode -ne 200) {
    throw "Root request returned HTTP $($root.StatusCode); expected 200."
}

$health = Invoke-RestMethod -Uri "$($BaseUrl.TrimEnd('/'))/api/health"
foreach ($property in @('ranges', 'warnings')) {
    if ($null -eq $health.PSObject.Properties[$property]) {
        throw "Health response does not contain its required '$property' property."
    }
}

$services = Get-ComposeServices
foreach ($serviceName in @('gateway', 'api', 'postgres')) {
    $service = @($services | Where-Object { $_.Service -eq $serviceName }) | Select-Object -First 1
    if ($null -eq $service) {
        throw "Required Compose service '$serviceName' is missing from docker compose ps."
    }
    if ($service.State -ne 'running') {
        throw "Compose service '$serviceName' is '$($service.State)'; expected running."
    }
    if ($service.Health -ne 'healthy') {
        throw "Compose service '$serviceName' is '$($service.Health)'; expected healthy."
    }

    if ($serviceName -in @('api', 'postgres')) {
        $hostPublishers = @($service.Publishers | Where-Object {
            Test-ActualHostPublisher -Publisher $_
        })
        if ($hostPublishers.Count -gt 0) {
            $publisherDetails = $hostPublishers | ConvertTo-Json -Compress
            throw "Compose service '$serviceName' unexpectedly has host publisher bindings: $publisherDetails"
        }
    }
}

Write-Host ("Smoke OK: {0} ({1})" -f $BaseUrl, ((@('gateway', 'api', 'postgres')) -join ', '))
