param(
    [string]$Model,
    [string]$OutputFolder,
    [string[]]$Clipping,
    [ValidateSet('Keep','Omit')][string]$SmallDetails = 'Keep',
    [ValidateSet('Source','OutputLayer')][string]$SectionWidthSource = 'Source'
)
$ErrorActionPreference = 'Stop'
if ($Model) { $Model = (Resolve-Path -LiteralPath $Model).Path }
if ($OutputFolder) { $OutputFolder = [IO.Path]::GetFullPath($OutputFolder) }
$psPreviousOptions, $psPreviousPath = $env:PLANSECTION_PDF_OPTIONS, $env:PATH
try {
    $env:PLANSECTION_PDF_OPTIONS = @{
        model = $Model; output = $OutputFolder; clipping = @($Clipping | Where-Object { $_ })
        small_details = $SmallDetails -eq 'Keep'
        section_width_source = if ($SectionWidthSource -eq 'OutputLayer') { 'output_layer' } else { 'source' }
    } | ConvertTo-Json -Compress
    & (Join-Path $PSScriptRoot 'data/run_native_check.ps1') -Script (Join-Path $PSScriptRoot 'PlanSectionPDF.py')
} finally {
    $env:PLANSECTION_PDF_OPTIONS, $env:PATH = $psPreviousOptions, $psPreviousPath
}
