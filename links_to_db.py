import json
from pathlib import Path

folders = (
    "Ben-YehudaToOtzaria",
    "DictaToOtzaria/ערוך",
    "OnYourWayToOtzaria",
    "OraytaToOtzaria",
    "tashmaToOtzaria",
    "sefariaToOtzaria/sefaria_export",
    "sefariaToOtzaria/sefaria_api",
    "MoreBooks",
    "wikiJewishBooksToOtzaria",
    "ToratEmetToOtzaria",
    "wikisourceToOtzaria",
    "pninimToOtzaria"
)

folders_path = [Path(folder) for folder in folders]
rel_to_abs_path = {}

for folder in folders_path:
    books_path = folder / "ספרים" / "אוצריא"
    links_path = folder / "links"

    if not links_path.exists():
        continue
    for root, _, files in books_path.walk():
        for file in files:
            file_path = root / file
            if file_path.suffix.lower() != ".txt":
                continue
            if file_path.name in rel_to_abs_path:
                print(f"Duplicate file name found: {file_path.name}")
            rel_to_abs_path[file_path.name] = str(file_path.relative_to(books_path))


for folder in folders_path:
    links_path = folder / "links"
    if not links_path.exists():
        continue
    for file in links_path.iterdir():
        if file.suffix.lower() != ".json":
            continue
        if not file.stem.endswith("_links"):
            continue
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            rel_path = entry["path_2"]
            absolute_path = rel_to_abs_path.get(rel_path)
            if absolute_path is None:
                print(f"Missing file for relative path: {rel_path} in {file}")
                continue
            entry["absolute_path"] = absolute_path
        with file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
