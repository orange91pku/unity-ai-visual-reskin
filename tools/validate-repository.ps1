$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$releaseVersion = (
	Get-Content -Raw -LiteralPath (Join-Path $repositoryRoot "VERSION")
).Trim()
if ($releaseVersion -notmatch "^\d+\.\d+\.\d+$") {
	throw "VERSION is not a release SemVer: $releaseVersion"
}

$pyprojectText = Get-Content -Raw -LiteralPath (
	Join-Path $repositoryRoot "pyproject.toml"
)
$pyprojectVersionMatch = [regex]::Match(
	$pyprojectText,
	'(?m)^version\s*=\s*"([^"]+)"\s*$'
)
if (
	-not $pyprojectVersionMatch.Success -or
	$pyprojectVersionMatch.Groups[1].Value -ne $releaseVersion
) {
	throw "pyproject.toml version must equal VERSION $releaseVersion."
}

$pythonInitText = Get-Content -Raw -LiteralPath (
	Join-Path $repositoryRoot "revisual_rag/__init__.py"
)
$pythonVersionMatch = [regex]::Match(
	$pythonInitText,
	'(?m)^__version__\s*=\s*"([^"]+)"\s*$'
)
if (
	-not $pythonVersionMatch.Success -or
	$pythonVersionMatch.Groups[1].Value -ne $releaseVersion
) {
	throw "Python __version__ must equal VERSION $releaseVersion."
}

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
	if ($package.version -ne $releaseVersion) {
		throw "Package $($package.name) must use version $releaseVersion."
	}
	if (
		$null -ne $package.dependencies -and
		$null -ne $package.dependencies."com.hydracore.visual-reskin" -and
		$package.dependencies."com.hydracore.visual-reskin" -ne $releaseVersion
	) {
		throw "Package $($package.name) must depend on Core $releaseVersion."
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
	if ($theme.version -ne $releaseVersion) {
		throw "Theme $($theme.themeId) must use version $releaseVersion."
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
	if ($project.adapterVersion -ne $releaseVersion) {
		throw "Project adapter $($project.projectId) must use version $releaseVersion."
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
	releaseVersion = $releaseVersion
	packages = $packageRoots.Count
	themes = $themeFiles.Count
	projectAdapters = $projectFiles.Count
	unityGuids = $metaByGuid.Count
}
