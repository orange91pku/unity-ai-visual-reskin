using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace HydraCore.VisualReskin.Editor
{
	public sealed class ValidationReport
	{
		public readonly List<string> Errors = new List<string>();
		public readonly List<string> Warnings = new List<string>();
		public int ResolvedAssets;
		public bool Passed => Errors.Count == 0;
	}

	public static class ManifestValidator
	{
		public static ValidationReport Validate(ThemeManifest manifest)
		{
			var report = new ValidationReport();
			if (manifest == null)
			{
				report.Errors.Add("Theme manifest is null.");
				return report;
			}
			if (manifest.schemaVersion != 1)
				report.Errors.Add(
					$"Unsupported theme schema: {manifest.schemaVersion}.");
			if (string.IsNullOrWhiteSpace(manifest.themeId))
				report.Errors.Add("themeId is required.");
			if (string.IsNullOrWhiteSpace(manifest.version))
				report.Errors.Add("version is required.");

			var roles = new HashSet<string>(StringComparer.Ordinal);
			foreach (var binding in manifest.assets ??
			         Array.Empty<ThemeAssetBinding>())
			{
				if (string.IsNullOrWhiteSpace(binding.semanticRole))
				{
					report.Errors.Add("A binding has no semanticRole.");
					continue;
				}
				if (!roles.Add(binding.semanticRole))
					report.Errors.Add(
						$"Duplicate semantic role: {binding.semanticRole}.");
				var path = AssetDatabase.GUIDToAssetPath(binding.assetGuid);
				if (string.IsNullOrEmpty(path))
				{
					report.Errors.Add(
						$"{binding.semanticRole}: GUID cannot be resolved.");
					continue;
				}
				var sprite = AssetDatabase.LoadAllAssetsAtPath(path)
					.OfType<Sprite>()
					.FirstOrDefault(candidate =>
						string.Equals(
							candidate.name,
							binding.spriteName,
							StringComparison.Ordinal));
				if (sprite == null)
				{
					report.Errors.Add(
						$"{binding.semanticRole}: sprite " +
						$"'{binding.spriteName}' was not found at {path}.");
					continue;
				}
				if (binding.border != null && binding.border.Length != 0 &&
				    binding.border.Length != 4)
					report.Errors.Add(
						$"{binding.semanticRole}: border must have four values.");
				report.ResolvedAssets++;
			}
			return report;
		}

		public static ValidationReport Validate(ProjectManifest manifest)
		{
			var report = new ValidationReport();
			if (manifest == null)
			{
				report.Errors.Add("Project manifest is null.");
				return report;
			}
			if (manifest.schemaVersion != 1)
				report.Errors.Add(
					$"Unsupported project schema: {manifest.schemaVersion}.");
			if (string.IsNullOrWhiteSpace(manifest.projectId))
				report.Errors.Add("projectId is required.");
			foreach (var scene in manifest.productionScenes ??
			         Array.Empty<string>())
				if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scene) == null)
					report.Errors.Add($"Production scene is missing: {scene}");
			foreach (var rule in manifest.detectionRules ??
			         Array.Empty<SemanticDetectionRule>())
			{
				if (string.IsNullOrWhiteSpace(rule.semanticRole))
					report.Errors.Add("A detection rule has no semanticRole.");
				if (string.IsNullOrWhiteSpace(rule.sourceSpriteName) &&
				    string.IsNullOrWhiteSpace(rule.hostNameContains) &&
				    string.IsNullOrWhiteSpace(rule.hierarchyContains) &&
				    string.IsNullOrWhiteSpace(rule.componentType))
					report.Errors.Add(
						$"{rule.semanticRole}: rule has no selector.");
			}
			return report;
		}
	}
}

