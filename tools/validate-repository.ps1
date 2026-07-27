$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$packageRoots = Get-ChildItem -LiteralPath (
	Join-Path $repositoryRoot "Packages"
) -Directory

if ($packageRoots.Count -lt 3) {
	throw "Expected Core, at least one Theme Pack, and one Project Adapter."
}

$packageNames = @{}
foreach ($packageRoot in $packageRoots) {
	$packagePath = Join-Path $packageRoot.FullName "package.json"
	if (-not (Test-Path -LiteralPath $packagePath)) {
		throw "Missing package.json: $($packageRoot.FullName)"
	}
	$package = Get-Content -Raw -LiteralPath $packagePath | ConvertFrom-Json
	if ($packageNames.ContainsKey($package.name)) {
		throw "Duplicate package name: $($package.name)"
	}
	$packageNames[$package.name] = $true
}

$themeFiles = Get-ChildItem -LiteralPath (
	Join-Path $repositoryRoot "Packages"
) -Filter "hydra-theme.json" -File -Recurse
$metaByGuid = @{}
$metaFiles = Get-ChildItem -LiteralPath (
	Join-Path $repositoryRoot "Packages"
) -Filter "*.meta" -File -Recurse
foreach ($metaFile in $metaFiles) {
	$metaBytes = [System.IO.File]::ReadAllBytes($metaFile.FullName)
	if ($metaBytes.Length -eq 0 -or $metaBytes[$metaBytes.Length - 1] -ne 10) {
		throw "Unity metadata must end with LF: $($metaFile.FullName)"
	}
	$metaText = Get-Content -Raw -LiteralPath $metaFile.FullName
	$match = [regex]::Match(
		$metaText,
		"(?m)^guid:\s*([a-fA-F0-9]{32})\s*$"
	)
	if (-not $match.Success) {
		throw "Unity metadata has no valid GUID: $($metaFile.FullName)"
	}
	$guid = $match.Groups[1].Value.ToLowerInvariant()
	if ($metaByGuid.ContainsKey($guid)) {
		throw "Duplicate Unity GUID $guid in $($metaFile.FullName)"
	}
	$metaByGuid[$guid] = [pscustomobject]@{
		path = $metaFile.FullName
		content = $metaText
	}
}

$themeIds = @{}
foreach ($themeFile in $themeFiles) {
	$theme = Get-Content -Raw -LiteralPath $themeFile.FullName |
		ConvertFrom-Json
	if ($theme.schemaVersion -ne 1) {
		throw "Unsupported theme schema in $($themeFile.FullName)"
	}
	if ($themeIds.ContainsKey($theme.themeId)) {
		throw "Duplicate themeId: $($theme.themeId)"
	}
	$themeIds[$theme.themeId] = $true
	$roles = @{}
	foreach ($asset in $theme.assets) {
		if ($roles.ContainsKey($asset.semanticRole)) {
			throw "Duplicate role $($asset.semanticRole) in $($theme.themeId)"
		}
		$roles[$asset.semanticRole] = $true
		if ($asset.assetGuid -notmatch "^[a-fA-F0-9]{32}$") {
			throw "Invalid asset GUID for $($asset.semanticRole)"
		}
		$assetGuid = $asset.assetGuid.ToLowerInvariant()
		if (-not $metaByGuid.ContainsKey($assetGuid)) {
			throw "Theme asset GUID is not packaged: $assetGuid"
		}
		$spritePattern = "(?m)^\s*name:\s*" +
			[regex]::Escape($asset.spriteName) + "\s*$"
		if ($metaByGuid[$assetGuid].content -notmatch $spritePattern) {
			throw "Sprite $($asset.spriteName) is absent from packaged metadata."
		}
	}
}

$projectFiles = Get-ChildItem -LiteralPath (
	Join-Path $repositoryRoot "Packages"
) -Filter "hydra-project.json" -File -Recurse
foreach ($projectFile in $projectFiles) {
	$project = Get-Content -Raw -LiteralPath $projectFile.FullName |
		ConvertFrom-Json
	if ($project.schemaVersion -ne 1) {
		throw "Unsupported project schema in $($projectFile.FullName)"
	}
	foreach ($rule in $project.detectionRules) {
		$selectorCount = @(
			$rule.sourceSpriteName,
			$rule.hostNameContains,
			$rule.hierarchyContains,
			$rule.componentType
		).Where({ -not [string]::IsNullOrWhiteSpace($_) }).Count
		if ($selectorCount -eq 0) {
			throw "Rule $($rule.semanticRole) has no selector."
		}
	}
}

$missingMeta = Get-ChildItem -LiteralPath (
	Join-Path $repositoryRoot "Packages"
) -File -Recurse |
	Where-Object {
		$_.Extension -in @(".cs", ".asmdef", ".png") -and
		-not (Test-Path -LiteralPath "$($_.FullName).meta")
	}
if ($missingMeta.Count -gt 0) {
	throw "Importable files without .meta: $($missingMeta.FullName -join ', ')"
}

[pscustomobject]@{
	status = "pass"
	packages = $packageRoots.Count
	themes = $themeFiles.Count
	projectAdapters = $projectFiles.Count
	unityGuids = $metaByGuid.Count
}
