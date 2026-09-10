# Authenticode-sign and/or verify the VST3 binary inside a bundle and the installer exe.
#
#   packaging\windows\sign.ps1 -Mode pfx    -Path <X.vst3 bundle dir | file.exe> ...
#   packaging\windows\sign.ps1 -Mode verify -Path ...
#
# Modes:
#   pfx     signtool sign /fd SHA256 /td SHA256 /tr <TimestampUrl> with the certificate from
#           WINDOWS_PFX_BASE64 + WINDOWS_PFX_PASSWORD (decoded to a temp file, deleted after).
#   verify  only the gate: signtool verify /pa /v. The release workflow uses this after
#           azure/trusted-signing-action (Azure Artifact Signing), which signs in place and
#           needs no certificate file - see .github/workflows/release.yml.
# A .vst3 argument that is a directory resolves to Contents\x86_64-win\*.vst3. DRY_RUN=1 echoes.
param(
    [Parameter(Mandatory)][string[]]$Path,
    [ValidateSet('pfx', 'verify')][string]$Mode = 'pfx',
    [string]$TimestampUrl = 'http://timestamp.digicert.com'
)
$ScriptName = Split-Path -Leaf $PSCommandPath
. (Join-Path $PSScriptRoot 'Common.ps1')

$product = Import-ProductEnv
$signtool = Find-Tool 'signtool' @("${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe")

$targets = @(foreach ($item in $Path) {
    if (Test-Path $item -PathType Container) {
        $found = @(Get-ChildItem -Path (Join-Path $item 'Contents\x86_64-win') -Filter '*.vst3' -File -ErrorAction SilentlyContinue)
        if (-not $found) { Fail "no x86_64-win\*.vst3 binary inside $item" }
        $found.FullName
    } elseif (Test-Path $item -PathType Leaf) {
        (Resolve-Path $item).Path
    } elseif ((Test-DryRun) -and ($item -like '*.vst3')) {
        Join-Path $item "Contents\x86_64-win\$(Split-Path -Leaf $item)"
    } elseif (Test-DryRun) {
        $item
    } else {
        Fail "not found: $item"
    }
})

if ($Mode -eq 'pfx') {
    if (-not $env:WINDOWS_PFX_BASE64 -or -not $env:WINDOWS_PFX_PASSWORD) {
        Fail 'WINDOWS_PFX_BASE64 and WINDOWS_PFX_PASSWORD are required for -Mode pfx'
    }
    if ($env:GITHUB_ACTIONS) { Write-Output "::add-mask::$($env:WINDOWS_PFX_PASSWORD)" }
    $pfx = Join-Path ([IO.Path]::GetTempPath()) ("codesign-" + [guid]::NewGuid().ToString('N') + '.pfx')
    try {
        if (-not (Test-DryRun)) {
            [IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:WINDOWS_PFX_BASE64))
        }
        foreach ($target in $targets) {
            Invoke-Step $signtool @('sign', '/fd', 'SHA256', '/td', 'SHA256', '/tr', $TimestampUrl,
                                    '/f', $pfx, '/p', $env:WINDOWS_PFX_PASSWORD,
                                    '/d', $product.PRODUCT_NAME, '/du', $product.VENDOR_URL, $target) `
                        -Redact @($env:WINDOWS_PFX_PASSWORD)
        }
    } finally {
        Remove-Item -Path $pfx -Force -ErrorAction SilentlyContinue
    }
}

foreach ($target in $targets) {
    Invoke-Step $signtool @('verify', '/pa', '/v', $target)
}
Write-Log "${Mode}: $($targets.Count) file(s) verified"
