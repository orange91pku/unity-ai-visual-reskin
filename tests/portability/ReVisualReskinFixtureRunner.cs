using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using HydraCore.VisualReskin.Editor;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

public static class ReVisualReskinFixtureRunner
{
	private const string ScenePath = "Assets/Scenes/Fixture.unity";
	private const string LegacyTexturePath =
		"Assets/Fixture/legacy_purchase.png";
	private const string ThemeId = "hydracore.theme.300mind";
	private const string ProjectId = "hydracore.fixture";

	public static void Run()
	{
		try
		{
			PrepareFixture();
			var theme = ManifestCatalog.Themes()
				.Single(item =>
					item.IsValid && item.Manifest.themeId == ThemeId)
				.Manifest;
			var project = ManifestCatalog.Projects()
				.Single(item =>
					item.IsValid && item.Manifest.projectId == ProjectId)
				.Manifest;

			var sceneHashBefore = HashFile(ScenePath);
			var dryRun = SemanticReskinEngine.Scan(theme, project);
			Debug.Log("REVRS_DRY_RUN " + JsonUtility.ToJson(dryRun, true));
			Require(
				dryRun.passed,
				"Dry-run did not pass: " +
				string.Join(" | ", dryRun.errors));
			Require(dryRun.mappedImages == 1, "Expected one mapped Image.");
			Require(dryRun.missingScripts == 0, "Baseline Missing Script.");

			var apply = SemanticReskinEngine.Apply(theme, project);
			Require(apply.passed, "Apply transaction did not pass.");
			Require(
				apply.state == "applied_verified",
				"Apply state was not applied_verified.");
			Require(apply.appliedImages == 1, "Expected one applied Image.");
			Require(
				apply.guardedFiles.Length == 2,
				"Expected two guarded atlas metadata files.");
			Require(
				apply.guardedFiles.All(file => file.unchanged),
				"Theme metadata changed during apply.");

			var verify = SemanticReskinEngine.Scan(theme, project);
			Require(verify.passed, "Post-apply scan did not pass.");
			Require(verify.mappedImages == 0, "Mapping remained after apply.");
			Require(
				verify.alreadyAppliedImages == 1,
				"Applied Image was not recognized.");

			var noOp = SemanticReskinEngine.Apply(theme, project);
			Require(noOp.passed, "No-op transaction did not pass.");
			Require(
				noOp.state == "no_op_verified" &&
				noOp.appliedImages == 0,
				"Second apply was not an idempotent no-op.");

			var rollback = SemanticReskinEngine.RollbackLastApply();
			Require(rollback.passed, "Rollback did not pass.");
			Require(
				HashFile(ScenePath) == sceneHashBefore,
				"Rollback did not restore the exact scene hash.");

			var restored = SemanticReskinEngine.Scan(theme, project);
			Require(restored.passed, "Restored scan did not pass.");
			Require(
				restored.mappedImages == 1,
				"Rollback did not restore the legacy mapping.");

			var report = new PortabilityReport
			{
				generatedAtUtc = DateTime.UtcNow.ToString("O"),
				unityVersion = Application.unityVersion,
				corePackageVersion = "0.2.0",
				themeId = theme.themeId,
				projectId = project.projectId,
				dryRunPassed = dryRun.passed,
				applyPassed = apply.passed,
				noOpPassed = noOp.passed,
				rollbackPassed = rollback.passed,
				sceneHashRestored = true,
				missingScripts = restored.missingScripts,
				guardedThemeMetaFiles = apply.guardedFiles.Length,
				passed = true
			};
			var output = Path.Combine(
				Directory.GetParent(Application.dataPath).FullName,
				"art-audit",
				"portability-fixture-report.json");
			Directory.CreateDirectory(Path.GetDirectoryName(output));
			File.WriteAllText(output, JsonUtility.ToJson(report, true));
			Debug.Log($"REVRS_PORTABILITY_PASS {output}");
		}
		catch (Exception exception)
		{
			Debug.LogException(exception);
			EditorApplication.Exit(1);
			return;
		}
		EditorApplication.Exit(0);
	}

	private static void PrepareFixture()
	{
		Directory.CreateDirectory("Assets/Fixture/Prefabs");
		Directory.CreateDirectory("Assets/Scenes");
		if (!File.Exists(LegacyTexturePath))
		{
			var texture = new Texture2D(64, 32, TextureFormat.RGBA32, false);
			texture.SetPixels32(Enumerable.Repeat(
				new Color32(40, 190, 90, 255),
				64 * 32).ToArray());
			texture.Apply();
			File.WriteAllBytes(LegacyTexturePath, texture.EncodeToPNG());
			UnityEngine.Object.DestroyImmediate(texture);
			AssetDatabase.ImportAsset(
				LegacyTexturePath,
				ImportAssetOptions.ForceSynchronousImport);
			var importer =
				(TextureImporter)AssetImporter.GetAtPath(LegacyTexturePath);
			importer.textureType = TextureImporterType.Sprite;
			importer.spriteImportMode = SpriteImportMode.Single;
			importer.SaveAndReimport();
		}

		var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(LegacyTexturePath);
		var scene = EditorSceneManager.NewScene(
			NewSceneSetup.EmptyScene,
			NewSceneMode.Single);
		var canvasObject = new GameObject(
			"FixtureCanvas",
			typeof(Canvas),
			typeof(CanvasScaler),
			typeof(GraphicRaycaster));
		canvasObject.GetComponent<Canvas>().renderMode =
			RenderMode.ScreenSpaceOverlay;
		var imageObject = new GameObject(
			"FixturePurchaseButton",
			typeof(RectTransform),
			typeof(Image),
			typeof(Button));
		imageObject.transform.SetParent(canvasObject.transform, false);
		var image = imageObject.GetComponent<Image>();
		image.sprite = sprite;
		image.type = Image.Type.Simple;
		image.rectTransform.sizeDelta = new Vector2(320f, 120f);
		if (!EditorSceneManager.SaveScene(scene, ScenePath))
			throw new IOException("Failed to save fixture scene.");
		AssetDatabase.SaveAssets();
		AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
	}

	private static string HashFile(string assetPath)
	{
		var absolutePath = Path.Combine(
			Directory.GetParent(Application.dataPath).FullName,
			assetPath.Replace('/', Path.DirectorySeparatorChar));
		using (var stream = File.OpenRead(absolutePath))
		using (var sha = SHA256.Create())
			return string.Concat(
				sha.ComputeHash(stream)
					.Select(value => value.ToString("x2")));
	}

	private static void Require(bool condition, string message)
	{
		if (!condition)
			throw new InvalidOperationException(message);
	}

	[Serializable]
	private sealed class PortabilityReport
	{
		public string generatedAtUtc;
		public string unityVersion;
		public string corePackageVersion;
		public string themeId;
		public string projectId;
		public bool dryRunPassed;
		public bool applyPassed;
		public bool noOpPassed;
		public bool rollbackPassed;
		public bool sceneHashRestored;
		public int missingScripts;
		public int guardedThemeMetaFiles;
		public bool passed;
	}
}
