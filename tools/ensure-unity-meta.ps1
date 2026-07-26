$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$packagesRoot = Join-Path $repositoryRoot "Packages"

function New-UnityGuid {
	return [Guid]::NewGuid().ToString("N")
}

function Write-Utf8NoBom {
	param(
		[string]$Path,
		[string]$Content
	)
	$encoding = New-Object System.Text.UTF8Encoding($false)
	[System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

$directories = Get-ChildItem -LiteralPath $packagesRoot -Directory -Recurse |
	Where-Object {
		$_.Name -notlike "*~" -and
		$_.Parent.FullName -ne $packagesRoot
	}
foreach ($directory in $directories) {
	$metaPath = "$($directory.FullName).meta"
	if (Test-Path -LiteralPath $metaPath) {
		continue
	}
	$guid = New-UnityGuid
	$content = @"
fileFormatVersion: 2
guid: $guid
folderAsset: yes
DefaultImporter:
  externalObjects: {}
  userData:
  assetBundleName:
  assetBundleVariant:
"@
	Write-Utf8NoBom -Path $metaPath -Content $content
}

$importableExtensions = @(".cs", ".asmdef", ".json")
$files = Get-ChildItem -LiteralPath $packagesRoot -File -Recurse |
	Where-Object {
		$importableExtensions -contains $_.Extension -and
		$_.Name -ne "package.json"
	}
foreach ($file in $files) {
	$metaPath = "$($file.FullName).meta"
	if (Test-Path -LiteralPath $metaPath) {
		continue
	}
	$guid = New-UnityGuid
	$importer = switch ($file.Extension) {
		".cs" { "MonoImporter" }
		".asmdef" { "AssemblyDefinitionImporter" }
		default { "TextScriptImporter" }
	}
	$content = @"
fileFormatVersion: 2
guid: $guid
$($importer):
  externalObjects: {}
  userData:
  assetBundleName:
  assetBundleVariant:
"@
	Write-Utf8NoBom -Path $metaPath -Content $content
}

Write-Output "Unity metadata ensured."
