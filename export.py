import argparse
import hashlib
import json
from pathlib import Path
import sys
try:
    import tomllib # Requires Python 3.11 or later.
except ImportError:
    import tomli as tomllib # Fallback for older Python versions.


def get_file_hash(filepath: Path, algorithm: str) -> str:
    hash_func = getattr(hashlib, algorithm)()

    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest().lower()

def main():
    parser = argparse.ArgumentParser(description="Modrinth pack JSON generator (Prism Launcher only)")
    parser.add_argument("--target-dir", type=str, default=".", help="Minecraft directory")
    args = parser.parse_args()

    target_dir = Path(args.target_dir)
    mods_dir = target_dir / "mods"
    index_dir = mods_dir / ".index"
    output_path = target_dir / "modrinth.index.json"

    if not index_dir.exists() or not index_dir.is_dir():
        print(f"Error: インデックスディレクトリが見つかりません: {index_dir}", file=sys.stderr)
        return

    files_array = []
    print("\033[96m処理を開始します\033[0m") 

    for toml_path in index_dir.glob("*.toml"):
        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)

            filename = data.get("filename")
            mode = data["download"].get("mode", "")
            url = data["download"].get("url", "")
            file_id = data["update"]["curseforge"].get("file-id")

            if not filename:
                print(f"Warning: [{toml_path.name}] 'filename' が見つかりません。")
                continue

            jar_path = mods_dir / filename
            if not jar_path.is_file():
                print(f"Warning: JARファイルが見つかりません: {filename}")
                continue

            print(f"処理中: {filename}")
            
            sha1 = get_file_hash(jar_path, "sha1")
            sha512 = get_file_hash(jar_path, "sha512")
            size = jar_path.stat().st_size

            downloads = []
            if mode == "url" and url: # GitHub, Modrinth, etc.
                downloads.append(url)
            elif mode == "metadata:curseforge" and file_id: # CurseForge
                fid = int(file_id)
                p1 = fid // 1000
                p2 = f"{fid % 1000:03d}"
                downloads.append(f"https://mediafilez.forgecdn.net/files/{p1}/{p2}/{filename}")

            files_array.append({
                "path": f"mods/{filename}",
                "hashes": {
                    "sha1": sha1,
                    "sha512": sha512
                },
                "downloads": downloads,
                "fileSize": size
            })

        except Exception as e:
            print(f"Error: [{toml_path.name}] を処理中にエラーが発生しました: {e}", file=sys.stderr)

    if not files_array:
        print("Warning: 出力対象のファイルがありませんでした。")
        return

    try:
        files_data = {
            "formatVersion": 1,
            "game": "minecraft",
            "versionId": "1.0.0",
            "name": "Modpack name",
            "summary": "Modpack description",
            "files": files_array,
            "dependencies": {}
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(files_data, f, indent=4, ensure_ascii=False)

        print(f"\n\033[92m完了 {output_path} を作成しました。\033[0m")
    except Exception as e:
        print(f"Error: JSONの保存に失敗: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()