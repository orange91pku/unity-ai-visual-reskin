using System;

namespace HydraCore.VisualReskin.Editor
{
	[Serializable]
	public sealed class ReskinScanReport
	{
		public int schemaVersion = 1;
		public string kind = "hydracore-visual-reskin-scan";
		public string generatedAtUtc;
		public string projectId;
		public string themeId;
		public string planSignature;
		public bool passed;
		public int scenesScanned;
		public int prefabsScanned;
		public int totalImages;
		public int mappedImages;
		public int alreadyAppliedImages;
		public int unmappedImages;
		public int ambiguousImages;
		public int unresolvedDestinations;
		public int missingScripts;
		public string[] errors = Array.Empty<string>();
		public ReskinPlanItem[] items = Array.Empty<ReskinPlanItem>();
	}

	[Serializable]
	public sealed class ReskinPlanItem
	{
		public string assetPath;
		public string hierarchyPath;
		public string hostName;
		public string sourceSpriteName;
		public string sourceSpriteGuid;
		public string semanticRole;
		public string destinationSpriteName;
		public string destinationAssetGuid;
		public string matchedBy;
		public bool mapped;
		public bool alreadyApplied;
		public bool ambiguous;
		public string error;
	}

	[Serializable]
	public sealed class ReskinTransaction
	{
		public int schemaVersion = 1;
		public string kind = "hydracore-visual-reskin-transaction";
		public string id;
		public string state;
		public string createdAtUtc;
		public string completedAtUtc;
		public string projectId;
		public string themeId;
		public string planSignature;
		public string transactionPath;
		public string backupRoot;
		public string parentTransactionPath;
		public bool passed;
		public int appliedImages;
		public int appliedPrefabs;
		public int missingScriptsBefore;
		public int missingScriptsAfter;
		public string error;
		public ReskinTransactionFile[] files =
			Array.Empty<ReskinTransactionFile>();
		public ReskinGuardedFile[] guardedFiles =
			Array.Empty<ReskinGuardedFile>();
	}

	[Serializable]
	public sealed class ReskinTransactionFile
	{
		public string assetPath;
		public string backupPath;
		public string hashBefore;
		public string hashAfter;
	}

	[Serializable]
	public sealed class ReskinGuardedFile
	{
		public string assetPath;
		public string hashBefore;
		public string hashAfter;
		public bool unchanged;
	}
}
