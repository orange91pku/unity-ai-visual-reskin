using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace HydraCore.VisualReskin.Editor
{
	public sealed class CatalogItem<T>
	{
		public string AssetPath { get; set; }
		public T Manifest { get; set; }
		public string Error { get; set; }
		public bool IsValid => string.IsNullOrEmpty(Error) && Manifest != null;
	}

	public static class ManifestCatalog
	{
		public static IReadOnlyList<CatalogItem<ThemeManifest>> Themes()
		{
			return Load<ThemeManifest>("hydra-theme");
		}

		public static IReadOnlyList<CatalogItem<ProjectManifest>> Projects()
		{
			return Load<ProjectManifest>("hydra-project");
		}

		private static IReadOnlyList<CatalogItem<T>> Load<T>(string name)
			where T : class
		{
			var results = new List<CatalogItem<T>>();
			foreach (var guid in AssetDatabase.FindAssets(
				         $"{name} t:TextAsset"))
			{
				var path = AssetDatabase.GUIDToAssetPath(guid);
				if (!string.Equals(
					    System.IO.Path.GetFileNameWithoutExtension(path),
					    name,
					    StringComparison.OrdinalIgnoreCase))
					continue;
				var item = new CatalogItem<T> { AssetPath = path };
				try
				{
					var textAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(path);
					item.Manifest = JsonUtility.FromJson<T>(textAsset.text);
					if (item.Manifest == null)
						item.Error = "Manifest JSON returned null.";
				}
				catch (Exception exception)
				{
					item.Error = exception.Message;
				}
				results.Add(item);
			}
			return results.OrderBy(item => item.AssetPath).ToList();
		}
	}
}

