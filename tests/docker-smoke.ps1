[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8080',
    [string]$ComposeOverride = 'docker-compose.local.yml'
)

$ErrorActionPreference = 'Stop'

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

function Assert-UnpublishedPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Service,
        [Parameter(Mandatory = $true)]
        [int]$ContainerPort
    )

    $portOutput = & docker compose -f docker-compose.yml -f $ComposeOverride port $Service $ContainerPort
    if (@($portOutput).Count -gt 0 -and -not [string]::IsNullOrWhiteSpace(($portOutput -join "`n"))) {
        throw "Service '$Service' unexpectedly publishes container port ${ContainerPort}: $($portOutput -join '; ')"
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
}

Assert-UnpublishedPort -Service 'api' -ContainerPort 8000
Assert-UnpublishedPort -Service 'postgres' -ContainerPort 5432

Write-Host ("Smoke OK: {0} ({1})" -f $BaseUrl, ((@('gateway', 'api', 'postgres')) -join ', '))
