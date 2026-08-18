[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$smokePath = Join-Path $PSScriptRoot 'docker-smoke.ps1'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $smokePath,
    [ref]$tokens,
    [ref]$parseErrors
)

if (@($parseErrors).Count -gt 0) {
    throw "docker-smoke.ps1 has parser errors: $($parseErrors -join '; ')"
}

$publisherFunction = @($ast.FindAll({
    param($node)

    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq 'Test-ActualHostPublisher'
}, $true)) | Select-Object -First 1

if ($null -eq $publisherFunction) {
    throw 'docker-smoke.ps1 is missing the Test-ActualHostPublisher function.'
}

. ([scriptblock]::Create($publisherFunction.Extent.Text))

$cases = @(
    [pscustomobject]@{
        Name = 'missing publisher'
        Publisher = $null
        Expected = $false
    },
    [pscustomobject]@{
        Name = 'exposed target without host binding'
        Publisher = [pscustomobject]@{ URL = ''; TargetPort = 8000; PublishedPort = 0; Protocol = 'tcp' }
        Expected = $false
    },
    [pscustomobject]@{
        Name = 'publisher with neither binding field'
        Publisher = [pscustomobject]@{ TargetPort = 5432; Protocol = 'tcp' }
        Expected = $false
    },
    [pscustomobject]@{
        Name = 'loopback host binding'
        Publisher = [pscustomobject]@{ URL = '127.0.0.1'; TargetPort = 8000; PublishedPort = 8000; Protocol = 'tcp' }
        Expected = $true
    },
    [pscustomobject]@{
        Name = 'positive port without URL'
        Publisher = [pscustomobject]@{ URL = ''; TargetPort = 5432; PublishedPort = 5432; Protocol = 'tcp' }
        Expected = $true
    },
    [pscustomobject]@{
        Name = 'host URL without positive port'
        Publisher = [pscustomobject]@{ URL = '0.0.0.0'; TargetPort = 5432; PublishedPort = 0; Protocol = 'tcp' }
        Expected = $true
    }
)

foreach ($case in $cases) {
    $actual = [bool](Test-ActualHostPublisher -Publisher $case.Publisher)
    if ($actual -ne $case.Expected) {
        throw "Publisher case '$($case.Name)' returned '$actual'; expected '$($case.Expected)'."
    }
}

Write-Output "Publisher classification OK: $($cases.Count) synthetic cases."
