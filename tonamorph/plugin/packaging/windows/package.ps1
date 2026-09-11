# Build the Windows installer with Inno Setup from installer.iss: the VST3 bundle, the EULA
# (legal/eula.md) as the licence page and THIRD_PARTY_LICENSES.md as the notices file.
# Output: DIST_DIR\<PRODUCT_SLUG>-<VERSION>-Windows-Setup.exe (…-Setup-unsigned.exe when UNSIGNED=1).
#
#   packaging\windows\package.ps1 [-Version X.Y.Z]
#
# Environment: UNSIGNED=1 labels a dry-run installer, ALLOW_LICENSE_PLACEHOLDER=1 tolerates
# unresolved EULA tokens (dry runs only), BUILD_DIR, DIST_DIR, DRY_RUN=1. EULA tokens come from
# PRODUCT_NAME (set here from product.env), COMPANY_LEGAL_NAME, ... (see common/eula_to_txt.py).
param(
    [string]$Version
)
$ScriptName = Split-Path -Leaf $PSCommandPath
. (Join-Path $PSScriptRoot 'Common.ps1')

$product = Import-ProductEnv
$ver = Resolve-Version $Version $product
$env:PRODUCT_NAME = $product.PRODUCT_NAME

$work = Join-Path $script:BuildDir 'installer'
$license = Join-Path $work 'license.txt'
if (-not (Test-DryRun)) { New-Item -ItemType Directory -Force -Path $work, $script:DistDir | Out-Null }

$flags = @('--missing-ok')
if ($env:ALLOW_LICENSE_PLACEHOLDER -eq '1') { $flags += '--unresolved-ok' }
Invoke-Step $script:Python (@((Join-Path $script:PackagingDir 'common\eula_to_txt.py'),
                              (Join-Path $script:RepoDir 'legal\eula.md'), $license) + $flags)

$notices = Join-Path $work 'notices.txt'
Invoke-Step $script:Python (@((Join-Path $script:PackagingDir 'common\eula_to_txt.py'),
                              (Join-Path $script:RepoDir 'THIRD_PARTY_LICENSES.md'), $notices,
                              '--placeholder-title', 'Third-Party Notices') + $flags)

$bundle = Get-Vst3Bundle $product
if (-not (Test-DryRun) -and -not (Test-Path $bundle)) { Fail "VST3 bundle not found (run build.ps1 first): $bundle" }

function Find-Iscc {
    $cmd = Get-Command 'iscc' -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}
$iscc = Find-Iscc
if (-not $iscc) {
    if (Test-DryRun) {
        $iscc = 'iscc'
    } else {
        Invoke-Step 'choco' @('install', 'innosetup', '--no-progress', '-y')
        $iscc = Find-Iscc
        if (-not $iscc) { Fail 'ISCC.exe not found after installing Inno Setup' }
    }
}

$suffix = if ($env:UNSIGNED -eq '1') { '-unsigned' } else { '' }
$baseName = "$($product.PRODUCT_SLUG)-$($ver.Full)-Windows-Setup$suffix"
Invoke-Step $iscc @(
    "/DProductName=$($product.PRODUCT_NAME)",
    "/DProductSlug=$($product.PRODUCT_SLUG)",
    "/DVersion=$($ver.Full)",
    "/DVersionNumeric=$($ver.Numeric)",
    "/DPublisher=$($product.VENDOR_NAME)",
    "/DPublisherUrl=$($product.VENDOR_URL)",
    "/DBundleId=$($product.BUNDLE_ID_BASE)",
    "/DCopyrightHolder=$($product.COPYRIGHT_HOLDER)",
    "/DSourceDir=$bundle",
    "/DLicenseFile=$license",
    "/DNoticesFile=$notices",
    "/DOutputDir=$($script:DistDir)",
    "/DOutputBaseName=$baseName",
    '/Qp',
    (Join-Path $PSScriptRoot 'installer.iss'))

$installer = Join-Path $script:DistDir "$baseName.exe"
if (-not (Test-DryRun) -and -not (Test-Path $installer)) { Fail "Inno Setup did not produce $installer" }
Write-Log "wrote $installer"
Set-StepOutput 'installer' $installer
