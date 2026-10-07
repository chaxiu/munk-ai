#Requires -Version 5.1
<#
.SYNOPSIS
  Install the Munk AI standalone runtime on Windows.

.DESCRIPTION
  Reads the R2 channel/version manifest, downloads the windows-x86_64 zip,
  verifies SHA-256, installs under %LOCALAPPDATA%\munk, and adds a user PATH
  entry for the munk.cmd launcher.

.EXAMPLE
  irm https://downloads.munk.sh/install.ps1 | iex

.EXAMPLE
  $env:MUNK_CHANNEL = "beta"; irm https://downloads.munk.sh/install.ps1 | iex

.EXAMPLE
  .\install.ps1 -Channel beta
#>
[CmdletBinding()]
param(
    [ValidateSet("stable", "beta")]
    [string]$Channel = $(
        if (-not [string]::IsNullOrWhiteSpace($env:MUNK_CHANNEL)) {
            $env:MUNK_CHANNEL
        } else {
            "stable"
        }
    ),

    [string]$Version = "",

    [string]$Variant = "full",

    [string]$InstallDir = "",

    [string]$BinDir = "",

    [string]$BaseUrl = "https://downloads.munk.sh",

    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Usage {
    @"
Usage: install.ps1 [options]

Options:
  -Channel <channel>       Release channel to install (default: stable)
  -Version <version>       Install an explicit version instead of the current channel
  -Variant <variant>       Runtime variant to install (default: full)
  -InstallDir <path>       Runtime install root (default: %LOCALAPPDATA%\munk)
  -BinDir <path>           Launcher directory for munk.cmd (default: %LOCALAPPDATA%\munk\bin)
  -BaseUrl <url>           Download manifest base URL (default: https://downloads.munk.sh)
  -Help                    Show this help text

Examples:
  irm https://downloads.munk.sh/install.ps1 | iex
  `$env:MUNK_CHANNEL = "beta"; irm https://downloads.munk.sh/install.ps1 | iex
  .\install.ps1 -Channel beta
  .\install.ps1 -Channel stable

Environment:
  MUNK_CHANNEL             Optional default for -Channel when piping irm | iex
"@
}

function Get-NormalizedArch {
    $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
    switch ($arch) {
        "x64" { return "x86_64" }
        "arm64" {
            throw "Windows arm64 is not supported yet (planned: windows-arm64). Phase 1 ships windows-x86_64 only."
        }
        default {
            throw "unsupported Windows architecture: $arch"
        }
    }
}

function Get-ManifestValue {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$Manifest,

        [Parameter(Mandatory = $true)]
        [string]$Expression,

        [Parameter(Mandatory = $true)]
        [string]$TargetKey,

        [Parameter(Mandatory = $true)]
        [string]$VariantName
    )

    switch ($Expression) {
        "version" { return [string]$Manifest.version }
        "channel" { return [string]$Manifest.channel }
        default {
            $artifacts = $Manifest.artifacts
            if ($null -eq $artifacts) {
                throw "manifest is missing artifacts"
            }
            $targetProperty = $artifacts.PSObject.Properties[$TargetKey]
            if ($null -eq $targetProperty) {
                $hint = ""
                if ($TargetKey -like "windows-*" -or $TargetKey -like "linux-*") {
                    $hint = " Hint: Windows/Linux preview builds publish to beta first (`$env:MUNK_CHANNEL='beta'; irm https://downloads.munk.sh/install.ps1 | iex)."
                }
                throw "no artifact found for target=$TargetKey.$hint"
            }
            $target = $targetProperty.Value
            $variantProperty = $target.PSObject.Properties[$VariantName]
            if ($null -eq $variantProperty) {
                throw "no artifact found for target=$TargetKey variant=$VariantName"
            }
            $variantPayload = $variantProperty.Value
            $valueProperty = $variantPayload.PSObject.Properties[$Expression]
            if ($null -eq $valueProperty -or [string]::IsNullOrWhiteSpace([string]$valueProperty.Value)) {
                throw "missing manifest field '$Expression' for target=$TargetKey variant=$VariantName"
            }
            return [string]$valueProperty.Value
        }
    }
}

function Download-File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Invoke-WebRequest -Uri $Url -OutFile $OutputPath -UseBasicParsing
}

function Get-Sha256Hex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )
    return (Get-FileHash -Algorithm SHA256 -Path $FilePath).Hash.ToLowerInvariant()
}

function Set-DirectoryJunction {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LinkPath,

        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    if (Test-Path -LiteralPath $LinkPath) {
        $existing = Get-Item -LiteralPath $LinkPath -Force
        if ($existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            cmd.exe /c "rmdir `"$LinkPath`"" | Out-Null
        } else {
            Remove-Item -LiteralPath $LinkPath -Recurse -Force
        }
    }
    New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null
}

function Write-LauncherShim {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ShimPath,

        [Parameter(Mandatory = $true)]
        [string]$InstallRoot
    )

    $shimParent = Split-Path -Parent $ShimPath
    New-Item -ItemType Directory -Force -Path $shimParent | Out-Null
    $content = @(
        "@echo off"
        "setlocal"
        "set `"MUNK_INSTALL_ROOT=$InstallRoot`""
        "call `"%MUNK_INSTALL_ROOT%\current\bin\munk.cmd`" %*"
        "exit /b %ERRORLEVEL%"
    ) -join "`r`n"
    Set-Content -LiteralPath $ShimPath -Value $content -Encoding ASCII
}

function Ensure-UserPathContains {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory
    )

    $normalized = [System.IO.Path]::GetFullPath($Directory).TrimEnd("\")
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -eq $current) {
        $current = ""
    }
    $parts = @()
    if (-not [string]::IsNullOrWhiteSpace($current)) {
        $parts = $current.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries)
    }
    foreach ($part in $parts) {
        try {
            $candidate = [System.IO.Path]::GetFullPath($part.Trim()).TrimEnd("\")
        } catch {
            continue
        }
        if ($candidate.Equals($normalized, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $false
        }
    }
    $updated = if ([string]::IsNullOrWhiteSpace($current)) {
        $normalized
    } else {
        "$current;$normalized"
    }
    [Environment]::SetEnvironmentVariable("Path", $updated, "User")
    $env:Path = "$normalized;$env:Path"
    return $true
}

function Write-InstallState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StatePath,

        [Parameter(Mandatory = $true)]
        [string]$ResolvedChannel,

        [Parameter(Mandatory = $true)]
        [string]$ResolvedVersion,

        [Parameter(Mandatory = $true)]
        [string]$ResolvedVariant,

        [Parameter(Mandatory = $true)]
        [string]$ManifestUrl
    )

    $payload = [ordered]@{
        channel      = $ResolvedChannel
        version      = $ResolvedVersion
        variant      = $ResolvedVariant
        manifest_url = $ManifestUrl
        installed_at = (Get-Date).ToUniversalTime().ToString("o")
    }
    $json = $payload | ConvertTo-Json -Depth 4
    Set-Content -LiteralPath $StatePath -Value $json -Encoding UTF8
}

function Resolve-ExtractedRuntimeRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExtractDir
    )

    $children = @(Get-ChildItem -LiteralPath $ExtractDir -Directory)
    if ($children.Count -lt 1) {
        throw "installer could not locate extracted runtime root"
    }
    return $children[0].FullName
}

if ($Help) {
    Show-Usage
    exit 0
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "munk"
}
if ([string]::IsNullOrWhiteSpace($BinDir)) {
    $BinDir = Join-Path $InstallDir "bin"
}

$TargetKey = "windows-$(Get-NormalizedArch)"
$NormalizedBaseUrl = $BaseUrl.TrimEnd("/")
if (-not [string]::IsNullOrWhiteSpace($Version)) {
    $ManifestUrl = "$NormalizedBaseUrl/releases/v$Version/version.json"
} else {
    $ManifestUrl = "$NormalizedBaseUrl/channels/$Channel.json"
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("munk-install-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

try {
    $ManifestPath = Join-Path $TempRoot "version.json"
    Write-Host "fetching manifest: $ManifestUrl"
    Download-File -Url $ManifestUrl -OutputPath $ManifestPath
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

    $ResolvedVersion = Get-ManifestValue -Manifest $Manifest -Expression "version" -TargetKey $TargetKey -VariantName $Variant
    try {
        $ResolvedChannel = Get-ManifestValue -Manifest $Manifest -Expression "channel" -TargetKey $TargetKey -VariantName $Variant
    } catch {
        $ResolvedChannel = $Channel
    }
    if ([string]::IsNullOrWhiteSpace($ResolvedChannel)) {
        $ResolvedChannel = $Channel
    }

    $ArchiveUrl = Get-ManifestValue -Manifest $Manifest -Expression "archive_url" -TargetKey $TargetKey -VariantName $Variant
    $Sha256Url = Get-ManifestValue -Manifest $Manifest -Expression "sha256_url" -TargetKey $TargetKey -VariantName $Variant
    $ArchiveFilename = Get-ManifestValue -Manifest $Manifest -Expression "filename" -TargetKey $TargetKey -VariantName $Variant
    try {
        $ManifestSha256 = Get-ManifestValue -Manifest $Manifest -Expression "sha256" -TargetKey $TargetKey -VariantName $Variant
    } catch {
        $ManifestSha256 = ""
    }

    $ArchivePath = Join-Path $TempRoot $ArchiveFilename
    $Sha256Path = Join-Path $TempRoot "$ArchiveFilename.sha256"
    $ExtractDir = Join-Path $TempRoot "extract"
    $VersionsDir = Join-Path $InstallDir "versions"
    $VersionDir = Join-Path $VersionsDir "$ResolvedVersion-$Variant"
    $StagedVersionDir = Join-Path $VersionsDir (".{0}-{1}.tmp.{2}" -f $ResolvedVersion, $Variant, $PID)
    $BackupVersionDir = Join-Path $VersionsDir (".{0}-{1}.backup.{2}" -f $ResolvedVersion, $Variant, $PID)
    $CurrentLink = Join-Path $InstallDir "current"
    $LauncherShim = Join-Path $BinDir "munk.cmd"

    New-Item -ItemType Directory -Force -Path $ExtractDir, $VersionsDir, $BinDir | Out-Null

    Write-Host "downloading archive: $ArchiveUrl"
    Download-File -Url $ArchiveUrl -OutputPath $ArchivePath
    Write-Host "downloading checksum: $Sha256Url"
    Download-File -Url $Sha256Url -OutputPath $Sha256Path

    $Expected = ((Get-Content -LiteralPath $Sha256Path -Raw -Encoding UTF8).Trim() -split "\s+")[0].ToLowerInvariant()
    $Actual = Get-Sha256Hex -FilePath $ArchivePath
    if ($Expected -ne $Actual) {
        throw "archive checksum mismatch"
    }
    if (-not [string]::IsNullOrWhiteSpace($ManifestSha256) -and $Expected -ne $ManifestSha256.ToLowerInvariant()) {
        throw "manifest checksum does not match downloaded checksum file"
    }

    Write-Host "extracting runtime"
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $ExtractDir -Force
    $ExtractedRoot = Resolve-ExtractedRuntimeRoot -ExtractDir $ExtractDir

    if (Test-Path -LiteralPath $StagedVersionDir) {
        Remove-Item -LiteralPath $StagedVersionDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $BackupVersionDir) {
        Remove-Item -LiteralPath $BackupVersionDir -Recurse -Force
    }
    Move-Item -LiteralPath $ExtractedRoot -Destination $StagedVersionDir
    if (Test-Path -LiteralPath $VersionDir) {
        Move-Item -LiteralPath $VersionDir -Destination $BackupVersionDir
    }
    try {
        Move-Item -LiteralPath $StagedVersionDir -Destination $VersionDir
    } catch {
        if (Test-Path -LiteralPath $StagedVersionDir) {
            Remove-Item -LiteralPath $StagedVersionDir -Recurse -Force
        }
        if (Test-Path -LiteralPath $BackupVersionDir) {
            Move-Item -LiteralPath $BackupVersionDir -Destination $VersionDir -ErrorAction SilentlyContinue
        }
        throw "failed to activate runtime at $VersionDir"
    }
    if (Test-Path -LiteralPath $BackupVersionDir) {
        Remove-Item -LiteralPath $BackupVersionDir -Recurse -Force
    }

    $RuntimeLauncher = Join-Path $VersionDir "bin\munk.cmd"
    if (-not (Test-Path -LiteralPath $RuntimeLauncher)) {
        throw "installed runtime is missing launcher: $RuntimeLauncher"
    }

    Set-DirectoryJunction -LinkPath $CurrentLink -TargetPath $VersionDir
    Write-LauncherShim -ShimPath $LauncherShim -InstallRoot $InstallDir
    Write-InstallState `
        -StatePath (Join-Path $InstallDir "install-state.json") `
        -ResolvedChannel $ResolvedChannel `
        -ResolvedVersion $ResolvedVersion `
        -ResolvedVariant $Variant `
        -ManifestUrl $ManifestUrl

    $PathUpdated = Ensure-UserPathContains -Directory $BinDir

    Write-Host "installed munk $ResolvedVersion ($Variant, $ResolvedChannel)"
    Write-Host "runtime root: $VersionDir"
    Write-Host "launcher: $LauncherShim"
    if ($PathUpdated) {
        Write-Host "updated user PATH to include: $BinDir"
        Write-Host "open a new terminal to use 'munk' directly"
    }
    Write-Host "verify with:"
    Write-Host "  munk --help"
    Write-Host "  munk version"
    Write-Host "  munk doctor"
    Write-Host "Windows supports Android and Web. iOS device bridge requires macOS."
    Write-Host "for web testing, prepare Playwright Chromium with:"
    Write-Host "  munk doctor --fix"
} finally {
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
