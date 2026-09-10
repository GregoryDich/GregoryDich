# Shared helpers for the Windows packaging scripts. Dot-source it after setting $ScriptName:
#
#   $ScriptName = Split-Path -Leaf $PSCommandPath
#   . (Join-Path $PSScriptRoot 'Common.ps1')
#
# Mirrors common/lib.sh: product.env parsing, version resolution, DRY_RUN=1 command echo.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:PackagingDir = Split-Path -Parent $PSScriptRoot
$script:PluginDir = Split-Path -Parent $script:PackagingDir
$script:RepoDir = Split-Path -Parent $script:PluginDir
$script:BuildDir = if ($env:BUILD_DIR) { $env:BUILD_DIR } else { Join-Path $script:PluginDir 'build' }
$script:DistDir = if ($env:DIST_DIR) { $env:DIST_DIR } else { Join-Path $script:PluginDir 'dist' }
$script:Python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }

function Test-DryRun { return $env:DRY_RUN -eq '1' }

function Write-Log([string]$Message) {
    [Console]::Error.WriteLine("[$ScriptName] $Message")
}

function Write-Warn([string]$Message) {
    Write-Log "WARNING: $Message"
    if ($env:GITHUB_ACTIONS) { Write-Output "::warning::$Message" }
}

function Fail([string]$Message) {
    if ($env:GITHUB_ACTIONS) { Write-Output "::error::$Message" }
    throw "[$ScriptName] ERROR: $Message"
}

# Runs a command, echoing it first; DRY_RUN=1 only echoes. Values listed in -Redact are never
# printed (pass the secret itself, e.g. a certificate password).
function Invoke-Step {
    param(
        [Parameter(Mandatory)][string]$Exe,
        [string[]]$Arguments = @(),
        [string[]]$Redact = @()
    )
    $shown = foreach ($arg in $Arguments) {
        if ($Redact -contains $arg -and $arg) { "'<redacted>'" }
        elseif ($arg -match '\s') { "'$arg'" }
        else { $arg }
    }
    $line = "$Exe $($shown -join ' ')"
    if (Test-DryRun) {
        Write-Output "+ (dry-run) $line"
        return
    }
    [Console]::Error.WriteLine("+ $line")
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { Fail "'$Exe' exited with $LASTEXITCODE" }
}

function Find-Tool([string]$Name, [string[]]$Candidates = @()) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in $Candidates) {
        $hit = Get-Item $candidate -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    if (Test-DryRun) { Write-Log "dry-run: '$Name' is not installed here, continuing"; return $Name }
    Fail "required tool '$Name' not found"
}

# Parses product.env (KEY="value", ${KEY} references, # comments) into an ordered hashtable.
function Import-ProductEnv {
    $path = Join-Path $script:PackagingDir 'product.env'
    if (-not (Test-Path $path)) { Fail "missing $path" }
    $product = [ordered]@{}
    foreach ($raw in Get-Content $path) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        if ($line -notmatch '^([A-Za-z_][A-Za-z0-9_]*)="([^"]*)"\s*(#.*)?$') { Fail "product.env: cannot parse line: $raw" }
        $key = $Matches[1]
        $value = [regex]::Replace($Matches[2], '\$\{([A-Za-z_][A-Za-z0-9_]*)\}', {
            param($m)
            if (-not $product.Contains($m.Groups[1].Value)) { Fail "product.env: $key references undefined $($m.Groups[1].Value)" }
            $product[$m.Groups[1].Value]
        })
        $product[$key] = $value
    }
    foreach ($key in 'PRODUCT_NAME', 'PRODUCT_SLUG', 'BUNDLE_ID_BASE', 'VENDOR_NAME', 'VENDOR_URL',
                     'PLUGIN_MANUFACTURER_CODE', 'PLUGIN_CODE', 'COPYRIGHT_HOLDER', 'CMAKE_TARGET', 'CMAKE_OPTION_PREFIX') {
        if (-not $product[$key]) { Fail "product.env: $key is empty" }
    }
    if ($product.PRODUCT_SLUG -match '\s') { Fail 'product.env: PRODUCT_SLUG may not contain spaces' }
    return $product
}

# Same precedence as lib.sh resolve_version: argument, $env:VERSION, the git tag of a tag
# build, then the CMakeLists.txt default. Returns @{ Full; Numeric }.
function Resolve-Version([string]$Requested, $Product) {
    $raw = $Requested
    if (-not $raw) { $raw = $env:VERSION }
    if (-not $raw -and $env:GITHUB_REF_TYPE -eq 'tag') { $raw = $env:GITHUB_REF_NAME }
    if (-not $raw) {
        $pattern = "^set\($($Product.CMAKE_OPTION_PREFIX)_VERSION `"([^`"]*)`""
        $match = Select-String -Path (Join-Path $script:PluginDir 'CMakeLists.txt') -Pattern $pattern | Select-Object -First 1
        if (-not $match) { Fail "no version given and CMakeLists.txt has no $($Product.CMAKE_OPTION_PREFIX)_VERSION default" }
        $raw = $match.Matches[0].Groups[1].Value
        Write-Log "no version given, using CMakeLists.txt default $raw"
    }
    $raw = $raw -replace '^v', ''
    if ($raw -notmatch '^(\d+\.\d+\.\d+)(-[0-9A-Za-z.]+)?$') { Fail "version '$raw' is not X.Y.Z or X.Y.Z-prerelease" }
    return @{ Full = $raw; Numeric = $Matches[1] }
}

function Get-Vst3Bundle($Product) {
    return Join-Path $script:BuildDir "$($Product.CMAKE_TARGET)_artefacts\Release\VST3\$($Product.PRODUCT_NAME).vst3"
}

function Get-Vst3BinaryDir($Product) {
    return Join-Path (Get-Vst3Bundle $Product) 'Contents\x86_64-win'
}

function Set-StepOutput([string]$Name, [string]$Value) {
    if ($env:GITHUB_OUTPUT) { "$Name=$Value" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8 }
    Write-Log "$Name=$Value"
}
