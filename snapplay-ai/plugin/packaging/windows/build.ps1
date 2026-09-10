# Configure and build the Release x64 VST3.
#
#   packaging\windows\build.ps1 [-Version X.Y.Z] [-NoRubberBand]
#
# Environment: VERSION (else git tag, else CMakeLists default), BUILD_DIR (default plugin\build),
# JOBS (default 4), DRY_RUN=1 to print the commands only. Needs a Visual Studio generator
# (the default on the runners); Rubber Band additionally needs cl.exe and pkg-config on PATH.
param(
    [string]$Version,
    [switch]$NoRubberBand
)
$ScriptName = Split-Path -Leaf $PSCommandPath
. (Join-Path $PSScriptRoot 'Common.ps1')

$product = Import-ProductEnv
$ver = Resolve-Version $Version $product
$jobs = if ($env:JOBS) { $env:JOBS } else { '4' }
Write-Log "$($product.PRODUCT_NAME) $($ver.Full) (numeric $($ver.Numeric)) x64 Release"

$useRubberBand = 'OFF'
if (-not $NoRubberBand) {
    . (Join-Path $PSScriptRoot 'rubberband.ps1')
    Build-RubberBand
    $useRubberBand = 'ON'
}

$cmake = Find-Tool 'cmake'
Invoke-Step $cmake @('-S', $script:PluginDir, '-B', $script:BuildDir, '-A', 'x64',
                     "-D$($product.CMAKE_OPTION_PREFIX)_VERSION=$($ver.Numeric)",
                     "-D$($product.CMAKE_OPTION_PREFIX)_USE_RUBBERBAND=$useRubberBand")
Invoke-Step $cmake @('--build', $script:BuildDir, '--config', 'Release', '--target', "$($product.CMAKE_TARGET)_VST3", '--parallel', $jobs)

$bundle = Get-Vst3Bundle $product
$binaryDir = Get-Vst3BinaryDir $product
$binary = Join-Path $binaryDir "$($product.PRODUCT_NAME).vst3"
if (Test-DryRun) {
    Write-Output "+ (dry-run) expect $binary"
} else {
    if (-not (Test-Path $binary)) { Fail "expected VST3 binary not found: $binary" }
    if ($useRubberBand -eq 'ON' -and -not (Select-String -Path (Join-Path $script:BuildDir 'CMakeCache.txt') -Pattern 'RUBBERBAND_FOUND.*=1' -Quiet)) {
        Write-Warn 'could not confirm from the CMake cache that Rubber Band was linked; check the configure log'
    }
    Write-Log "built $bundle"
}
Set-StepOutput 'vst3_bundle' $bundle
Set-StepOutput 'vst3_binary_dir' $binaryDir
