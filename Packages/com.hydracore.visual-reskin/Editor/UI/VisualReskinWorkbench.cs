using System.Linq;
using UnityEditor;
using UnityEngine;

namespace HydraCore.VisualReskin.Editor
{
	public sealed class VisualReskinWorkbench : EditorWindow
	{
		private Vector2 scroll;

		[MenuItem("Tools/HydraCore/Visual Reskin Workbench")]
		public static void Open()
		{
			GetWindow<VisualReskinWorkbench>("Visual Reskin");
		}

		private void OnGUI()
		{
			EditorGUILayout.LabelField(
				"HydraCore Visual Reskin",
				EditorStyles.boldLabel);
			EditorGUILayout.HelpBox(
				"Core discovers Theme Packs and Project Adapters. " +
				"Validation never modifies project assets.",
				MessageType.Info);

			if (GUILayout.Button("Refresh and validate catalogs"))
				Repaint();

			scroll = EditorGUILayout.BeginScrollView(scroll);
			DrawThemes();
			EditorGUILayout.Space();
			DrawProjects();
			EditorGUILayout.EndScrollView();
		}

		private static void DrawThemes()
		{
			EditorGUILayout.LabelField("Theme Packs", EditorStyles.boldLabel);
			var themes = ManifestCatalog.Themes();
			if (themes.Count == 0)
				EditorGUILayout.HelpBox(
					"No hydra-theme.json manifests found.",
					MessageType.Warning);
			foreach (var item in themes)
			{
				if (!item.IsValid)
				{
					EditorGUILayout.HelpBox(
						$"{item.AssetPath}: {item.Error}",
						MessageType.Error);
					continue;
				}
				var report = ManifestValidator.Validate(item.Manifest);
				EditorGUILayout.BeginVertical("box");
				EditorGUILayout.LabelField(
					$"{item.Manifest.displayName}  v{item.Manifest.version}");
				EditorGUILayout.LabelField(item.Manifest.themeId);
				EditorGUILayout.LabelField(
					$"{report.ResolvedAssets}/{item.Manifest.assets.Length} " +
					"bindings resolved");
				DrawReport(report);
				EditorGUILayout.EndVertical();
			}
		}

		private static void DrawProjects()
		{
			EditorGUILayout.LabelField(
				"Project Adapters",
				EditorStyles.boldLabel);
			var projects = ManifestCatalog.Projects();
			if (projects.Count == 0)
				EditorGUILayout.HelpBox(
					"No hydra-project.json manifests found.",
					MessageType.Warning);
			foreach (var item in projects)
			{
				if (!item.IsValid)
				{
					EditorGUILayout.HelpBox(
						$"{item.AssetPath}: {item.Error}",
						MessageType.Error);
					continue;
				}
				var report = ManifestValidator.Validate(item.Manifest);
				EditorGUILayout.BeginVertical("box");
				EditorGUILayout.LabelField(
					$"{item.Manifest.displayName}  " +
					$"v{item.Manifest.adapterVersion}");
				EditorGUILayout.LabelField(item.Manifest.projectId);
				EditorGUILayout.LabelField(
					$"{item.Manifest.productionScenes.Length} scenes, " +
					$"{item.Manifest.detectionRules.Length} detection rules");
				DrawReport(report);
				EditorGUILayout.EndVertical();
			}
		}

		private static void DrawReport(ValidationReport report)
		{
			foreach (var error in report.Errors)
				EditorGUILayout.HelpBox(error, MessageType.Error);
			foreach (var warning in report.Warnings)
				EditorGUILayout.HelpBox(warning, MessageType.Warning);
			if (report.Passed)
				EditorGUILayout.LabelField("Contract validation: PASS");
		}
	}
}

