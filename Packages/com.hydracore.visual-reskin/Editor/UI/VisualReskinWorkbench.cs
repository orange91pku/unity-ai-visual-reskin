using System.Linq;
using UnityEditor;
using UnityEngine;

namespace HydraCore.VisualReskin.Editor
{
	public sealed class VisualReskinWorkbench : EditorWindow
	{
		private Vector2 scroll;
		private int themeIndex;
		private int projectIndex;
		private ReskinScanReport lastScan;
		private ReskinTransaction lastTransaction;

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
				"Select a Theme Pack and Project Adapter. Scan is read-only. " +
				"Apply is transactional and requires explicit confirmation.",
				MessageType.Info);

			var themes = ManifestCatalog.Themes()
				.Where(item => item.IsValid)
				.ToList();
			var projects = ManifestCatalog.Projects()
				.Where(item => item.IsValid)
				.ToList();
			if (themes.Count == 0 || projects.Count == 0)
			{
				EditorGUILayout.HelpBox(
					"At least one valid Theme Pack and Project Adapter are required.",
					MessageType.Warning);
			}
			else
			{
				themeIndex = Mathf.Clamp(themeIndex, 0, themes.Count - 1);
				projectIndex = Mathf.Clamp(projectIndex, 0, projects.Count - 1);
				themeIndex = EditorGUILayout.Popup(
					"Theme",
					themeIndex,
					themes.Select(item => item.Manifest.displayName).ToArray());
				projectIndex = EditorGUILayout.Popup(
					"Project",
					projectIndex,
					projects.Select(item => item.Manifest.displayName).ToArray());
				DrawActions(
					themes[themeIndex].Manifest,
					projects[projectIndex].Manifest);
			}

			scroll = EditorGUILayout.BeginScrollView(scroll);
			DrawLastRun();
			EditorGUILayout.Space();
			DrawCatalogSummary(themes, projects);
			EditorGUILayout.EndScrollView();
		}

		private void DrawActions(
			ThemeManifest theme,
			ProjectManifest project)
		{
			EditorGUILayout.BeginHorizontal();
			if (GUILayout.Button("Scan / Dry Run"))
			{
				lastTransaction = null;
				lastScan = SemanticReskinEngine.Scan(theme, project);
			}
			using (new EditorGUI.DisabledScope(
				       lastScan == null || !lastScan.passed))
			{
				if (GUILayout.Button("Apply + Verify"))
				{
					if (EditorUtility.DisplayDialog(
						    "Apply visual theme?",
						    "Core will back up every target file, apply the " +
						    "approved semantic plan, verify it, and automatically " +
						    "rollback on failure.",
						    "Apply",
						    "Cancel"))
					{
						lastTransaction =
							SemanticReskinEngine.Apply(theme, project);
						lastScan = SemanticReskinEngine.Scan(theme, project);
					}
				}
			}
			if (GUILayout.Button("Rollback Last Apply") &&
			    EditorUtility.DisplayDialog(
				    "Rollback last apply?",
				    "The latest applied transaction will be restored from its " +
				    "hash-verified backup.",
				    "Rollback",
				    "Cancel"))
				lastTransaction = SemanticReskinEngine.RollbackLastApply();
			EditorGUILayout.EndHorizontal();
		}

		private void DrawLastRun()
		{
			if (lastScan != null)
			{
				EditorGUILayout.LabelField(
					"Latest scan",
					EditorStyles.boldLabel);
				EditorGUILayout.HelpBox(
					$"{(lastScan.passed ? "PASS" : "BLOCKED")} — " +
					$"{lastScan.scenesScanned} scenes, " +
					$"{lastScan.prefabsScanned} prefabs, " +
					$"{lastScan.totalImages} images, " +
					$"{lastScan.mappedImages} mapped, " +
					$"{lastScan.alreadyAppliedImages} already applied, " +
					$"{lastScan.missingScripts} Missing Script.",
					lastScan.passed ? MessageType.Info : MessageType.Error);
				foreach (var error in lastScan.errors)
					EditorGUILayout.HelpBox(error, MessageType.Error);
			}
			if (lastTransaction != null)
			{
				EditorGUILayout.LabelField(
					"Latest transaction",
					EditorStyles.boldLabel);
				EditorGUILayout.HelpBox(
					$"{lastTransaction.state} — " +
					$"{lastTransaction.appliedImages} image operations, " +
					$"{lastTransaction.appliedPrefabs} prefabs.",
					lastTransaction.passed
						? MessageType.Info
						: MessageType.Error);
			}
		}

		private static void DrawCatalogSummary(
			System.Collections.Generic.IReadOnlyCollection<
				CatalogItem<ThemeManifest>> themes,
			System.Collections.Generic.IReadOnlyCollection<
				CatalogItem<ProjectManifest>> projects)
		{
			EditorGUILayout.LabelField("Catalog", EditorStyles.boldLabel);
			EditorGUILayout.LabelField(
				$"{themes.Count} valid Theme Pack(s), " +
				$"{projects.Count} valid Project Adapter(s).");
			foreach (var theme in themes)
			{
				var validation = ManifestValidator.Validate(theme.Manifest);
				EditorGUILayout.LabelField(
					$"Theme: {theme.Manifest.displayName} — " +
					$"{validation.ResolvedAssets}/" +
					$"{theme.Manifest.assets.Length} resolved");
			}
			foreach (var project in projects)
				EditorGUILayout.LabelField(
					$"Adapter: {project.Manifest.displayName} — " +
					$"{project.Manifest.productionScenes.Length} scenes, " +
					$"{project.Manifest.detectionRules.Length} rules");
		}
	}
}
