param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $InputPath).Path
$dest = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $dest -Force | Out-Null
$powerpoint = $null
$presentation = $null
try {
    $powerpoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerpoint.Presentations.Open($source, -1, 0, 0)
    $presentation.Export($dest, 'PNG', 1600, 900)
    $frames = @(Get-ChildItem -LiteralPath $dest -Filter '*.PNG')
    if ($frames.Count -ne $presentation.Slides.Count) { throw 'PowerPoint frame count mismatch' }
    [pscustomobject]@{renderer='PowerPoint';slides=$presentation.Slides.Count;directory=$dest} | ConvertTo-Json
} finally {
    if ($presentation) { $presentation.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
    if ($powerpoint) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint) }
}
