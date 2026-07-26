using System;

namespace HydraCore.VisualReskin
{
	[Serializable]
	public sealed class ProjectManifest
	{
		public int schemaVersion = 1;
		public string projectId;
		public string displayName;
		public string adapterVersion;
		public string[] productionScenes = Array.Empty<string>();
		public string[] prefabRoots = Array.Empty<string>();
		public string[] excludedPathSegments = Array.Empty<string>();
		public SemanticDetectionRule[] detectionRules =
			Array.Empty<SemanticDetectionRule>();
		public RuntimeReviewSurface[] reviewSurfaces =
			Array.Empty<RuntimeReviewSurface>();
	}

	[Serializable]
	public sealed class SemanticDetectionRule
	{
		public int priority;
		public string semanticRole;
		public string sourceSpriteName;
		public string hostNameContains;
		public string hierarchyContains;
		public string componentType;
	}

	[Serializable]
	public sealed class RuntimeReviewSurface
	{
		public string id;
		public string scenePath;
		public string entryAction;
		public int width = 720;
		public int height = 1280;
	}
}

