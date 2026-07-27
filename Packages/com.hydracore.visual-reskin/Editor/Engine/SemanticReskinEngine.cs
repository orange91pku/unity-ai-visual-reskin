using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace HydraCore.VisualReskin.Editor
{
	public static class SemanticReskinEngine
	{
		private const string OutputFolder =
			"art-audit/visual-reskin";

		public static ReskinScanReport Scan(
			ThemeManifest theme,
			ProjectManifest project,
			bool includeItems = true)
		{
			var errors = new List<string>();
			var items = new List<ReskinPlanItem>();
			var report = new ReskinScanReport
			{
				generatedAtUtc = DateTime.UtcNow.ToString("O"),
				projectId = project?.projectId ?? string.Empty,
				themeId = theme?.themeId ?? string.Empty
			};
			if (!ValidateInputs(theme, project, errors))
			{
				report.errors = errors.ToArray();
				return report;
			}

			foreach (var scenePath in project.productionScenes)
			{
				if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
				continue;
				var scene = EditorSceneManager.OpenPreviewScene(scenePath);
				try
				{
					report.scenesScanned++;
					ScanImages(
						Resources.FindObjectsOfTypeAll<Image>()
							.Where(image =>
								image != null &&
								image.gameObject.scene == scene),
						scenePath,
						theme,
						project,
						report,
						items,
						includeItems);
					report.missingScripts += CountMissingScripts(scene);
				}
				finally
				{
					EditorSceneManager.ClosePreviewScene(scene);
				}
			}

			foreach (var prefabPath in OwnedPrefabPaths(project))
			{
				var root = PrefabUtility.LoadPrefabContents(prefabPath);
				try
				{
					report.prefabsScanned++;
					ScanImages(
						root.GetComponentsInChildren<Image>(true),
						prefabPath,
						theme,
						project,
						report,
						items,
						includeItems);
					report.missingScripts +=
						GameObjectUtility
							.GetMonoBehavioursWithMissingScriptCount(root);
				}
				finally
				{
					PrefabUtility.UnloadPrefabContents(root);
				}
			}

			report.items = includeItems
				? items
					.OrderBy(item => item.assetPath, StringComparer.Ordinal)
					.ThenBy(item => item.hierarchyPath, StringComparer.Ordinal)
					.ToArray()
				: Array.Empty<ReskinPlanItem>();
			report.planSignature = BuildPlanSignature(items);
			report.errors = errors.ToArray();
			report.passed =
				errors.Count == 0 &&
				report.missingScripts == 0 &&
				report.ambiguousImages == 0 &&
				report.unresolvedDestinations == 0 &&
				(report.mappedImages > 0 ||
				 report.alreadyAppliedImages > 0);
			WriteJson(report, "scan-latest.json");
			return report;
		}

		public static ReskinTransaction Apply(
			ThemeManifest theme,
			ProjectManifest project)
		{
			RequireSafeEditorState();
			var plan = Scan(theme, project);
			if (!plan.passed)
				throw new InvalidOperationException(
					"Reskin dry-run failed. Persistent apply is blocked.");

			var transaction = NewTransaction(theme, project, plan);
			if (plan.mappedImages == 0)
			{
				transaction.state = "no_op_verified";
				transaction.passed = true;
				transaction.missingScriptsBefore = plan.missingScripts;
				transaction.missingScriptsAfter = plan.missingScripts;
				transaction.completedAtUtc = DateTime.UtcNow.ToString("O");
				WriteTransaction(transaction);
				return transaction;
			}

			var targetPaths = plan.items
				.Where(item => item.mapped && !item.alreadyApplied)
				.Select(item => item.assetPath)
				.Distinct(StringComparer.Ordinal)
				.OrderBy(path => path, StringComparer.Ordinal)
				.ToList();

			try
			{
				BackupFiles(transaction, targetPaths);
				GuardThemeMetadata(transaction, theme);
				transaction.state = "applying";
				WriteTransaction(transaction);

				var sceneSetup = EditorSceneManager.GetSceneManagerSetup();
				try
				{
					foreach (var scenePath in project.productionScenes)
					{
						if (!targetPaths.Contains(scenePath))
							continue;
						var scene = EditorSceneManager.OpenScene(
							scenePath,
							OpenSceneMode.Single);
						var changed = ApplyImages(
							Resources.FindObjectsOfTypeAll<Image>()
								.Where(image =>
									image != null &&
									image.gameObject.scene == scene),
							theme,
							project);
						if (changed > 0)
						{
							EditorSceneManager.MarkSceneDirty(scene);
							if (!EditorSceneManager.SaveScene(scene))
								throw new IOException(
									$"Failed to save scene: {scenePath}");
						}
						transaction.appliedImages += changed;
					}

					foreach (var prefabPath in targetPaths
						         .Where(path =>
							         path.EndsWith(
								         ".prefab",
								         StringComparison.OrdinalIgnoreCase)))
					{
						var root = PrefabUtility.LoadPrefabContents(prefabPath);
						try
						{
							var changed = ApplyImages(
								root.GetComponentsInChildren<Image>(true),
								theme,
								project);
							if (changed > 0)
							{
								PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
								transaction.appliedPrefabs++;
								transaction.appliedImages += changed;
							}
						}
						finally
						{
							PrefabUtility.UnloadPrefabContents(root);
						}
					}
				}
				finally
				{
					EditorSceneManager.RestoreSceneManagerSetup(sceneSetup);
				}

				AssetDatabase.SaveAssets();
				AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
				var verification = Scan(theme, project, false);
				transaction.missingScriptsAfter =
					verification.missingScripts;
				CompleteGuardChecks(transaction);
				transaction.passed =
					verification.passed &&
					verification.mappedImages == 0 &&
					transaction.appliedImages > 0 &&
					transaction.missingScriptsBefore == 0 &&
					transaction.missingScriptsAfter == 0 &&
					transaction.guardedFiles.All(file => file.unchanged);
				if (!transaction.passed)
					throw new InvalidOperationException(
						"Post-apply verification failed.");

				CapturePostHashes(transaction);
				transaction.state = "applied_verified";
				transaction.completedAtUtc = DateTime.UtcNow.ToString("O");
				WriteTransaction(transaction);
				File.WriteAllText(LatestPointerPath(), transaction.transactionPath);
				return transaction;
			}
			catch (Exception exception)
			{
				transaction.error = exception.ToString();
				RestoreBackups(transaction);
				transaction.state = "auto_rolled_back";
				transaction.passed = false;
				transaction.completedAtUtc = DateTime.UtcNow.ToString("O");
				WriteTransaction(transaction);
				throw;
			}
		}

		public static ReskinTransaction RollbackLastApply()
		{
			RequireSafeEditorState();
			var pointerPath = LatestPointerPath();
			if (!File.Exists(pointerPath))
				throw new FileNotFoundException(
					"No applied transaction is available.",
					pointerPath);
			var transactionPath = File.ReadAllText(pointerPath).Trim();
			if (string.IsNullOrEmpty(transactionPath) ||
			    !File.Exists(transactionPath))
				throw new FileNotFoundException(
					"The latest transaction manifest is unavailable.",
					transactionPath);
			var transaction = JsonUtility.FromJson<ReskinTransaction>(
				File.ReadAllText(transactionPath));
			RestoreBackups(transaction);
			transaction.state = "rolled_back";
			transaction.passed = true;
			transaction.completedAtUtc = DateTime.UtcNow.ToString("O");
			WriteTransaction(transaction);
			File.WriteAllText(
				pointerPath,
				transaction.parentTransactionPath ?? string.Empty);
			AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
			return transaction;
		}

		private static bool ValidateInputs(
			ThemeManifest theme,
			ProjectManifest project,
			ICollection<string> errors)
		{
			if (theme == null)
				errors.Add("Theme manifest is null.");
			if (project == null)
				errors.Add("Project manifest is null.");
			if (errors.Count > 0)
				return false;

			var themeValidation = ManifestValidator.Validate(theme);
			foreach (var error in themeValidation.Errors)
				errors.Add(error);
			var projectValidation = ManifestValidator.Validate(project);
			foreach (var error in projectValidation.Errors)
				errors.Add(error);
			return errors.Count == 0;
		}

		private static void ScanImages(
			IEnumerable<Image> images,
			string assetPath,
			ThemeManifest theme,
			ProjectManifest project,
			ReskinScanReport report,
			ICollection<ReskinPlanItem> records,
			bool includeItems)
		{
			var themeGuids = new HashSet<string>(
				theme.assets.Select(binding => binding.assetGuid),
				StringComparer.OrdinalIgnoreCase);
			foreach (var image in images
				         .Where(image => image != null)
				         .OrderBy(
					         image => HierarchyPath(image.transform),
					         StringComparer.Ordinal))
			{
				report.totalImages++;
				var sourcePath = image.sprite == null
					? string.Empty
					: AssetDatabase.GetAssetPath(image.sprite);
				var sourceGuid = string.IsNullOrEmpty(sourcePath)
					? string.Empty
					: AssetDatabase.AssetPathToGUID(sourcePath);
				var alreadyApplied =
					!string.IsNullOrEmpty(sourceGuid) &&
					themeGuids.Contains(sourceGuid);
				var match = alreadyApplied
					? RuleMatch.None
					: MatchRule(image, project);
				ThemeAssetBinding destination = null;
				string error = null;
				if (match.Ambiguous)
				{
					report.ambiguousImages++;
					error = "Multiple top-priority semantic roles matched.";
				}
				else if (match.Rule != null)
				{
					destination = theme.assets.FirstOrDefault(binding =>
						string.Equals(
							binding.semanticRole,
							match.Rule.semanticRole,
							StringComparison.Ordinal));
					if (destination == null ||
					    ResolveSprite(destination) == null)
					{
						report.unresolvedDestinations++;
						error =
							$"Theme has no resolvable binding for " +
							$"{match.Rule.semanticRole}.";
					}
				}

				var mapped = destination != null && error == null;
				if (alreadyApplied)
					report.alreadyAppliedImages++;
				else if (mapped)
					report.mappedImages++;
				else
					report.unmappedImages++;

				if (!includeItems)
					continue;
				records.Add(new ReskinPlanItem
				{
					assetPath = assetPath,
					hierarchyPath = HierarchyPath(image.transform),
					hostName = image.name,
					sourceSpriteName =
						image.sprite == null ? string.Empty : image.sprite.name,
					sourceSpriteGuid = sourceGuid,
					semanticRole =
						match.Rule == null ? string.Empty : match.Rule.semanticRole,
					destinationSpriteName =
						destination?.spriteName ?? string.Empty,
					destinationAssetGuid =
						destination?.assetGuid ?? string.Empty,
					matchedBy = match.MatchedBy,
					mapped = mapped,
					alreadyApplied = alreadyApplied,
					ambiguous = match.Ambiguous,
					error = error ?? string.Empty
				});
			}
		}

		private static int ApplyImages(
			IEnumerable<Image> images,
			ThemeManifest theme,
			ProjectManifest project)
		{
			var changed = 0;
			var themeGuids = new HashSet<string>(
				theme.assets.Select(binding => binding.assetGuid),
				StringComparer.OrdinalIgnoreCase);
			foreach (var image in images.Where(image => image != null))
			{
				var sourcePath = image.sprite == null
					? string.Empty
					: AssetDatabase.GetAssetPath(image.sprite);
				var sourceGuid = string.IsNullOrEmpty(sourcePath)
					? string.Empty
					: AssetDatabase.AssetPathToGUID(sourcePath);
				if (themeGuids.Contains(sourceGuid))
					continue;
				var match = MatchRule(image, project);
				if (match.Rule == null || match.Ambiguous)
					continue;
				var binding = theme.assets.FirstOrDefault(candidate =>
					string.Equals(
						candidate.semanticRole,
						match.Rule.semanticRole,
						StringComparison.Ordinal));
				var sprite = ResolveSprite(binding);
				if (binding == null || sprite == null)
					continue;

				Undo.RecordObject(image, "Apply semantic visual theme");
				Undo.RecordObject(
					image.rectTransform,
					"Apply semantic visual theme");
				image.sprite = sprite;
				image.preserveAspect = binding.preserveAspect;
				if (binding.clearMaterial)
					image.material = null;
				if (binding.resetTint)
					image.color = Color.white;
				ApplyImageMode(image, sprite, binding.imageMode);
				if (binding.scale > 0f &&
				    !Mathf.Approximately(binding.scale, 1f))
					image.rectTransform.localScale =
						Vector3.one * binding.scale;
				EditorUtility.SetDirty(image);
				EditorUtility.SetDirty(image.rectTransform);
				changed++;
			}
			return changed;
		}

		private static void ApplyImageMode(
			Image image,
			Sprite sprite,
			string imageMode)
		{
			if (image.type == Image.Type.Filled ||
			    string.Equals(
				    imageMode,
				    "filled",
				    StringComparison.OrdinalIgnoreCase))
			{
				image.type = Image.Type.Filled;
				return;
			}
			if (string.Equals(
				    imageMode,
				    "sliced",
				    StringComparison.OrdinalIgnoreCase) ||
			    (string.Equals(
				     imageMode,
				     "auto",
				     StringComparison.OrdinalIgnoreCase) &&
			     sprite.border.sqrMagnitude > 0f))
				image.type = Image.Type.Sliced;
			else
				image.type = Image.Type.Simple;
		}

		private static RuleMatch MatchRule(
			Image image,
			ProjectManifest project)
		{
			var path = HierarchyPath(image.transform);
			var matches = project.detectionRules
				.Where(rule => RuleMatches(rule, image, path))
				.OrderByDescending(rule => rule.priority)
				.ToList();
			if (matches.Count == 0)
				return RuleMatch.None;
			var highest = matches[0].priority;
			var top = matches
				.Where(rule => rule.priority == highest)
				.ToList();
			var roles = top
				.Select(rule => rule.semanticRole)
				.Distinct(StringComparer.Ordinal)
				.ToList();
			return new RuleMatch
			{
				Rule = top[0],
				Ambiguous = roles.Count > 1,
				MatchedBy = DescribeRule(top[0])
			};
		}

		private static bool RuleMatches(
			SemanticDetectionRule rule,
			Image image,
			string hierarchyPath)
		{
			if (!string.IsNullOrWhiteSpace(rule.sourceSpriteName) &&
			    (image.sprite == null ||
			     !string.Equals(
				     image.sprite.name,
				     rule.sourceSpriteName,
				     StringComparison.OrdinalIgnoreCase)))
				return false;
			if (!Contains(image.name, rule.hostNameContains))
				return false;
			if (!Contains(hierarchyPath, rule.hierarchyContains))
				return false;
			if (!string.IsNullOrWhiteSpace(rule.componentType) &&
			    !image.GetComponents<Component>().Any(component =>
				    component != null &&
				    (string.Equals(
					     component.GetType().Name,
					     rule.componentType,
					     StringComparison.Ordinal) ||
				     string.Equals(
					     component.GetType().FullName,
					     rule.componentType,
					     StringComparison.Ordinal))))
				return false;
			return true;
		}

		private static bool Contains(string value, string selector)
		{
			return string.IsNullOrWhiteSpace(selector) ||
			       (!string.IsNullOrEmpty(value) &&
			        value.IndexOf(
				        selector,
				        StringComparison.OrdinalIgnoreCase) >= 0);
		}

		private static string DescribeRule(SemanticDetectionRule rule)
		{
			if (!string.IsNullOrWhiteSpace(rule.sourceSpriteName))
				return $"sprite:{rule.sourceSpriteName}";
			if (!string.IsNullOrWhiteSpace(rule.hierarchyContains))
				return $"hierarchy:{rule.hierarchyContains}";
			if (!string.IsNullOrWhiteSpace(rule.hostNameContains))
				return $"host:{rule.hostNameContains}";
			return $"component:{rule.componentType}";
		}

		private static Sprite ResolveSprite(ThemeAssetBinding binding)
		{
			if (binding == null)
				return null;
			var path = AssetDatabase.GUIDToAssetPath(binding.assetGuid);
			return AssetDatabase.LoadAllAssetsAtPath(path)
				.OfType<Sprite>()
				.FirstOrDefault(sprite =>
					string.Equals(
						sprite.name,
						binding.spriteName,
						StringComparison.Ordinal));
		}

		private static IEnumerable<string> OwnedPrefabPaths(
			ProjectManifest project)
		{
			var roots = project.prefabRoots?
				.Where(root => AssetDatabase.IsValidFolder(root))
				.ToArray() ?? Array.Empty<string>();
			if (roots.Length == 0)
				return Array.Empty<string>();
			return AssetDatabase.FindAssets("t:Prefab", roots)
				.Select(AssetDatabase.GUIDToAssetPath)
				.Where(path =>
					!project.excludedPathSegments.Any(segment =>
						path.IndexOf(
							segment,
							StringComparison.OrdinalIgnoreCase) >= 0))
				.OrderBy(path => path, StringComparer.Ordinal);
		}

		private static int CountMissingScripts(Scene scene)
		{
			return scene.GetRootGameObjects().Sum(root =>
				GameObjectUtility
					.GetMonoBehavioursWithMissingScriptCount(root));
		}

		private static string HierarchyPath(Transform transform)
		{
			var parts = new Stack<string>();
			for (var cursor = transform;
			     cursor != null;
			     cursor = cursor.parent)
				parts.Push(cursor.name);
			return string.Join("/", parts);
		}

		private static string BuildPlanSignature(
			IEnumerable<ReskinPlanItem> items)
		{
			var text = string.Join(
				"\n",
				items
					.Where(item => item.mapped)
					.OrderBy(item => item.assetPath, StringComparer.Ordinal)
					.ThenBy(item => item.hierarchyPath, StringComparer.Ordinal)
					.Select(item =>
						$"{item.assetPath}|{item.hierarchyPath}|" +
						$"{item.sourceSpriteGuid}|{item.semanticRole}|" +
						$"{item.destinationAssetGuid}|" +
						$"{item.destinationSpriteName}"));
			using (var sha = SHA256.Create())
				return string.Concat(
					sha.ComputeHash(Encoding.UTF8.GetBytes(text))
						.Select(value => value.ToString("x2")));
		}

		private static ReskinTransaction NewTransaction(
			ThemeManifest theme,
			ProjectManifest project,
			ReskinScanReport plan)
		{
			var id = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff");
			var root = Path.Combine(
				ProjectRoot(),
				OutputFolder,
				"transactions",
				id);
			Directory.CreateDirectory(root);
			var pointer = LatestPointerPath();
			return new ReskinTransaction
			{
				id = id,
				state = "prepared",
				createdAtUtc = DateTime.UtcNow.ToString("O"),
				projectId = project.projectId,
				themeId = theme.themeId,
				planSignature = plan.planSignature,
				transactionPath = Path.Combine(root, "transaction.json"),
				backupRoot = Path.Combine(root, "backup"),
				parentTransactionPath =
					File.Exists(pointer) ? File.ReadAllText(pointer).Trim() : "",
				missingScriptsBefore = plan.missingScripts
			};
		}

		private static void BackupFiles(
			ReskinTransaction transaction,
			IEnumerable<string> assetPaths)
		{
			var files = new List<ReskinTransactionFile>();
			foreach (var assetPath in assetPaths)
			{
				var source = AbsolutePath(assetPath);
				if (!File.Exists(source))
					throw new FileNotFoundException(
						"Transaction target is missing.",
						source);
				var backup = Path.Combine(
					transaction.backupRoot,
					assetPath.Replace('/', Path.DirectorySeparatorChar));
				Directory.CreateDirectory(Path.GetDirectoryName(backup));
				File.Copy(source, backup, true);
				files.Add(new ReskinTransactionFile
				{
					assetPath = assetPath,
					backupPath = backup,
					hashBefore = HashFile(source)
				});
			}
			transaction.files = files.ToArray();
		}

		private static void GuardThemeMetadata(
			ReskinTransaction transaction,
			ThemeManifest theme)
		{
			transaction.guardedFiles = theme.assets
				.Select(binding => AssetDatabase.GUIDToAssetPath(binding.assetGuid))
				.Where(path => !string.IsNullOrEmpty(path))
				.Select(path => path + ".meta")
				.Distinct(StringComparer.Ordinal)
				.Where(path => File.Exists(PhysicalAssetPath(path)))
				.Select(path => new ReskinGuardedFile
				{
					assetPath = path,
					hashBefore = HashFile(PhysicalAssetPath(path))
				})
				.ToArray();
		}

		private static void CompleteGuardChecks(
			ReskinTransaction transaction)
		{
			foreach (var file in transaction.guardedFiles)
			{
				file.hashAfter = HashFile(PhysicalAssetPath(file.assetPath));
				file.unchanged = string.Equals(
					file.hashBefore,
					file.hashAfter,
					StringComparison.OrdinalIgnoreCase);
			}
		}

		private static void CapturePostHashes(ReskinTransaction transaction)
		{
			foreach (var file in transaction.files)
				file.hashAfter = HashFile(AbsolutePath(file.assetPath));
		}

		private static void RestoreBackups(ReskinTransaction transaction)
		{
			foreach (var file in transaction.files)
			{
				var destination = AbsolutePath(file.assetPath);
				Directory.CreateDirectory(Path.GetDirectoryName(destination));
				File.Copy(file.backupPath, destination, true);
				var restoredHash = HashFile(destination);
				if (!string.Equals(
					    restoredHash,
					    file.hashBefore,
					    StringComparison.OrdinalIgnoreCase))
					throw new IOException(
						$"Rollback hash mismatch: {file.assetPath}");
			}
			AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
		}

		private static void RequireSafeEditorState()
		{
			if (EditorApplication.isPlayingOrWillChangePlaymode)
				throw new InvalidOperationException(
					"Stop Play Mode before persistent reskin operations.");
			if (EditorApplication.isCompiling || EditorApplication.isUpdating)
				throw new InvalidOperationException(
					"Wait for Unity compilation/import to finish.");
			for (var index = 0;
			     index < SceneManager.sceneCount;
			     index++)
			{
				var scene = SceneManager.GetSceneAt(index);
				if (scene.isDirty)
					throw new InvalidOperationException(
						$"Save or discard dirty scene first: {scene.path}");
			}
		}

		private static string ProjectRoot()
		{
			return Directory.GetParent(Application.dataPath).FullName;
		}

		private static string AbsolutePath(string assetPath)
		{
			return Path.Combine(
				ProjectRoot(),
				assetPath.Replace('/', Path.DirectorySeparatorChar));
		}

		private static string PhysicalAssetPath(string assetPath)
		{
			if (!assetPath.StartsWith(
				    "Packages/",
				    StringComparison.OrdinalIgnoreCase))
				return AbsolutePath(assetPath);
			var package =
				UnityEditor.PackageManager.PackageInfo.FindForAssetPath(
					assetPath);
			if (package == null)
				return AbsolutePath(assetPath);
			var prefix = $"Packages/{package.name}/";
			var relative = assetPath.StartsWith(
				prefix,
				StringComparison.OrdinalIgnoreCase)
				? assetPath.Substring(prefix.Length)
				: Path.GetFileName(assetPath);
			return Path.Combine(
				package.resolvedPath,
				relative.Replace('/', Path.DirectorySeparatorChar));
		}

		private static string LatestPointerPath()
		{
			var path = Path.Combine(
				ProjectRoot(),
				OutputFolder,
				"latest.txt");
			Directory.CreateDirectory(Path.GetDirectoryName(path));
			return path;
		}

		private static string HashFile(string path)
		{
			using (var stream = File.OpenRead(path))
			using (var sha = SHA256.Create())
				return string.Concat(
					sha.ComputeHash(stream)
						.Select(value => value.ToString("x2")));
		}

		private static void WriteJson(object value, string fileName)
		{
			var output = Path.Combine(ProjectRoot(), OutputFolder, fileName);
			Directory.CreateDirectory(Path.GetDirectoryName(output));
			File.WriteAllText(output, JsonUtility.ToJson(value, true));
		}

		private static void WriteTransaction(ReskinTransaction transaction)
		{
			Directory.CreateDirectory(
				Path.GetDirectoryName(transaction.transactionPath));
			File.WriteAllText(
				transaction.transactionPath,
				JsonUtility.ToJson(transaction, true));
		}

		private sealed class RuleMatch
		{
			public static readonly RuleMatch None = new RuleMatch();
			public SemanticDetectionRule Rule;
			public bool Ambiguous;
			public string MatchedBy = string.Empty;
		}
	}
}
