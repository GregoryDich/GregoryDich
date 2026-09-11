# Builds Rubber Band Library as a static x64 library for MSVC and exports PKG_CONFIG_PATH so
# CMakeLists.txt's pkg_check_modules(rubberband) finds it. Same single-file build as
# macos/rubberband.sh (built-in FFT and resampler, no other dependencies); /MD matches the
# runtime CMake selects for the plugin (CMakeLists.txt does not override it).
# Requires cl.exe/lib.exe on PATH (a Developer Command Prompt or ilammy/msvc-dev-cmd) and
# pkg-config (choco install pkgconfiglite). Dot-source and call Build-RubberBand.
#
# Rubber Band is GPL-2.0-or-later OR commercial: a closed-source release needs the commercial
# licence - this script only builds it.

$script:RubberBandGit = if ($env:RUBBERBAND_GIT) { $env:RUBBERBAND_GIT } else { 'https://github.com/breakfastquay/rubberband.git' }
$script:RubberBandTag = if ($env:RUBBERBAND_TAG) { $env:RUBBERBAND_TAG } else { 'v3.3.0' }
$script:RubberBandCommit = if ($env:RUBBERBAND_COMMIT) { $env:RUBBERBAND_COMMIT } else { '2be46b0dffb13273a67396c77bc9278736bb03d2' }

function Build-RubberBand {
    $prefix = Join-Path $script:BuildDir 'rubberband'
    $src = Join-Path $prefix 'src'
    $lib = Join-Path $prefix 'lib\rubberband.lib'
    $pc = Join-Path $prefix 'lib\pkgconfig\rubberband.pc'

    if ((Test-Path $lib) -and (Test-Path $pc)) {
        Write-Log "Rubber Band already built in $prefix"
    } else {
        $git = Find-Tool 'git'
        $cl = Find-Tool 'cl'
        $libExe = Find-Tool 'lib'
        if (-not (Test-DryRun)) {
            New-Item -ItemType Directory -Force -Path (Join-Path $prefix 'lib\pkgconfig'), (Join-Path $prefix 'include') | Out-Null
        }
        if (-not (Test-Path (Join-Path $src '.git'))) {
            Invoke-Step $git @('clone', '--quiet', '--depth', '1', '--branch', $script:RubberBandTag, $script:RubberBandGit, $src)
        }
        if (-not (Test-DryRun)) {
            $head = (& $git -C $src rev-parse HEAD).Trim()
            if ($head -ne $script:RubberBandCommit) { Fail "Rubber Band $script:RubberBandTag resolved to $head, expected $script:RubberBandCommit" }
        }
        $obj = Join-Path $prefix 'RubberBandSingle.obj'
        Invoke-Step $cl @('/nologo', '/c', '/O2', '/MD', '/EHsc', '/std:c++17', '/DNDEBUG', '/D_USE_MATH_DEFINES', '/DNOMINMAX',
                          '/DWIN32_LEAN_AND_MEAN', "/Fo$obj", (Join-Path $src 'single\RubberBandSingle.cpp'))
        Invoke-Step $libExe @('/nologo', "/OUT:$lib", $obj)
        if (Test-DryRun) {
            Write-Output "+ (dry-run) copy $(Join-Path $src 'rubberband') -> $(Join-Path $prefix 'include')"
            Write-Output "+ (dry-run) write $pc"
        } else {
            Copy-Item -Path (Join-Path $src 'rubberband') -Destination (Join-Path $prefix 'include') -Recurse -Force
            $prefixPc = $prefix -replace '\\', '/'
            @(
                "prefix=$prefixPc"
                'libdir=${prefix}/lib'
                'includedir=${prefix}/include'
                ''
                'Name: rubberband'
                'Description: Rubber Band Library (static, single-file build)'
                "Version: $($script:RubberBandTag.TrimStart('v'))"
                'Libs: -L${libdir} -lrubberband'
                'Cflags: -I${includedir}'
            ) | Set-Content -Path $pc -Encoding ascii
        }
    }
    $pkgDir = Join-Path $prefix 'lib\pkgconfig'
    $env:PKG_CONFIG_PATH = if ($env:PKG_CONFIG_PATH) { "$pkgDir;$($env:PKG_CONFIG_PATH)" } else { $pkgDir }
    Write-Log "PKG_CONFIG_PATH=$($env:PKG_CONFIG_PATH)"
}
