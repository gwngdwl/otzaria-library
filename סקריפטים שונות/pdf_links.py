import json
import re
from pathlib import Path

from PyPDF2 import PdfReader


def get_pdf_bookmarks(path: Path) -> list[str]:
    reader = PdfReader(path)
    outlines = reader.outline

    titles = []

    def extract(outline_items) -> None:
        for item in outline_items:
            if isinstance(item, list):
                extract(item)
            else:
                titles.append(str(item.title))

    extract(outlines)
    return titles


def find_heading_lines(html_content: list[str], pdf_headings: list[str]) -> dict[str, int | None]:
    results: dict[str, int | None] = {h: None for h in pdf_headings}
    pattern = re.compile(r"<(h[1-6])[^>]*>(.*?)</\1>", re.IGNORECASE)
    for lineno, line in enumerate(html_content, start=1):
        matches = pattern.findall(line)
        for _, inner in matches:
            text = re.sub("<.*?>", "", inner).strip()
            for h in pdf_headings:
                if text == h and results[h] is None:
                    results[h] = lineno

    return results


def main():
    links_folder = Path("links")
    links_folder.mkdir(exist_ok=True, parents=True)
    folders = {
        "סדר זרעים",
        "סדר מועד",
        "סדר נשים",
        "סדר נזיקין",
        "סדר קדשים",
        "סדר טהרות"
    }
    base_path = Path(r"C:\אוצריא\אוצריא\תלמוד בבלי")
    for folder in folders:
        folder_path = base_path / folder
        for file in folder_path.iterdir():
            if file.suffix.lower() != ".pdf":
                continue
            text_file = file.with_suffix(".txt")
            if not text_file.exists():
                print(f"Skipping {file.name}, text file does not exist.")
                continue
            pdf_headings = get_pdf_bookmarks(file)
            with text_file.open("r", encoding="utf-8") as f:
                html_content = f.readlines()
            heading_lines = find_heading_lines(html_content, pdf_headings)
            output_file = links_folder / f"{folder}_{file.stem}_headings.json"
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(heading_lines, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
