using System;

namespace HydraCore.VisualReskin
{
	[Serializable]
	public sealed class ThemeManifest
	{
		public int schemaVersion = 1;
		public string themeId;
		public string displayName;
		public string version;
		public string[] styleTags = Array.Empty<string>();
		public ThemeAssetBinding[] assets = Array.Empty<ThemeAssetBinding>();
	}

	[Serializable]
	public sealed class ThemeAssetBinding
	{
		public string semanticRole;
		public string assetGuid;
		public string spriteName;
		public string imageMode = "auto";
		public bool preserveAspect;
		public float scale = 1f;
		public bool clearMaterial;
		public bool resetTint;
		public float[] border = Array.Empty<float>();
		public string[] tags = Array.Empty<string>();
	}
}
