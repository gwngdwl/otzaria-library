import csv
import html
import re
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def sanitize_filename(filename: str) -> str:
    filename = unicodedata.normalize("NFD", filename)
    filename = ''.join(
        ch for ch in filename
        if not unicodedata.combining(ch)
    )
    return re.sub(r'[\\/:"*?<>|]', '', filename).replace('_', ' ')


def adjust_html_tag_spaces(html: str) -> str:
    start_pattern = r'(<[^/<>]+?>)([ ]+)'
    end_pattern = r'([ ]+)(</[^<>]+?>)'
    # Move spaces from inside the closing tag to after the tag
    while re.findall(end_pattern, html):
        html = re.sub(end_pattern, r'\2\1', html)

    # Move spaces from the beginning of tags to before the tags
    while re.findall(start_pattern, html):
        html = re.sub(start_pattern, r'\2\1', html)
    # Clean up any double spaces created by the previous step
    return re.sub(r'[ ]{2,}', ' ', html)


def extract_html_info(html: str) -> tuple:
    # Parse the HTML content
    soup = BeautifulSoup(html, 'html.parser')

    # Extract the title text
    title = soup.title.string if soup.title else None

    # Extract the author from the meta tag
    author = None
    author_meta = soup.find('meta', attrs={'name': 'author'})
    if author_meta:
        author = author_meta.get('content')

    # Extract the body HTML
    body = str(soup.body) if soup.body else None

    return title, author, body


def process_body_html(body_html: str) -> str:
    body_html = body_html.replace("\n", " ")
    supported_tags = {
        "a", "abbr", "acronym", "address", "article", "aside", "audio", "b", "bdi", "bdo", "big",
        "blockquote", "br", "caption", "cite", "code", "data", "dd", "del", "details", "dfn", "dl", "dt", "em", "figcaption", "figure", "footer", "font", "h1", "h2", "h3", "h4",
        "h5", "h6", "header", "hr", "i", "iframe", "img", "ins", "kbd", "li", "main", "mark", "nav",
        "noscript", "ol", "p", "pre", "q", "rp", "rt", "ruby", "s", "samp", "section", "small", "span",
        "strike", "strong", "sub", "sup", "summary", "svg", "table", "tbody", "td", "template", "tfoot",
        "th", "thead", "time", "tr", "tt", "u", "ul", "var", "video", "math", "mrow", "msup", "msub",
        "mover", "munder", "msubsup", "moverunder", "mfrac", "mlongdiv", "msqrt", "mroot", "mi", "mn", "mo"
    }
    soup = BeautifulSoup(body_html, 'html.parser')

    # Check if there is an <h1> tag in the document
    has_h1 = soup.find('h1') is not None

    # Decrease heading levels and remove id attributes
    for heading in soup.find_all(re.compile('^h[1-6]$')):
        if has_h1:
            current_level = int(heading.name[1])
            new_level = min(current_level + 1, 6)  # Ensure the level doesn't go beyond h6
            heading.name = f'h{new_level}'
    for tag in soup.find_all():
        if tag.name not in supported_tags:
            tag.unwrap()  # צריך לסדר את span וdiv
        elif tag.name.lower() in ("section", "span", "tr", "div", "a"):
            tag_class = tag.attrs.get("class")
            if tag_class:
                class_replace = ""
                if tag_class == ["footnotes"]:
                    class_replace += "border-top: 1px solid lightgray; margin: 20px 0;"
                elif tag_class == ["header"]:
                    pass
                elif tag_class == ["anchor"]:
                    pass
                elif tag_class == ["odd"]:
                    pass
                elif tag_class == ["underline"]:
                    pass
                elif tag_class == ["even"]:
                    pass
                elif tag_class == ["math"]:
                    pass
                if tag.attrs.get("style"):
                    tag.attrs["style"] += class_replace
                elif class_replace:
                    tag.attrs["style"] = class_replace
                del tag.attrs["class"]

    for tag in soup.find_all():
        if not tag.get_text(strip=True) and tag.name != "br":  # If the tag has no text
            tag.decompose()

    for tag in soup.find_all(recursive=False):
        tag.insert_before('\n')
        tag.insert_after('\n')

    text = str(soup).strip()

    return text


def get_updated_csv(url: str) -> list[list[str]]:
    content = requests.get(url)
    content.raise_for_status()
    content = content.text.splitlines()
    csv_format = csv.reader(content)
    return list(csv_format)


def read_old_csv_file(csv_path: Path) -> list[list[str]]:
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8") as csv_content:
            return list(csv.reader(csv_content))
    return []


def author_list(file_path: Path) -> list[str]:
    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as file:
            return file.read().splitlines()
    return []


def write_to_csv(csv_path: Path, data: list) -> None:
    with csv_path.open("a", newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(data)


def get_book(book_path: str, base_url: str) -> str | None:
    full_url = f"{base_url}/{book_path}.html"
    content = requests.get(full_url)
    content.raise_for_status()
    return content.text


def genre_folder_name(genre: str) -> str:
    genre_map = {
        "article": "מאמרים",
        "drama": "דרמה",
        "fables": "משלים",
        "letters": "מכתבים",
        "lexicon": "לקסיקון",
        "memoir": "זכרונות",
        "poetry": "שירה",
        "prose": "פרוזה",
        "reference": "ספרי עיון",
    }
    genre = genre.split(":")[-1].split(".")[-1].strip()
    return genre_map.get(genre, sanitize_filename(genre))


def main(url: str, kosher_file: Path, base_url: str, not_kosher_file: Path, need_to_check_file: Path, csv_path: Path, destination_path: Path) -> None:
    updated_csv = get_updated_csv(url)
    old_csv = read_old_csv_file(csv_path)
    kosher_list = author_list(kosher_file)
    not_kosher_list = author_list(not_kosher_file)
    need_to_check_list = author_list(need_to_check_file)
    for line in updated_csv[1:]:
        if line in old_csv:
            continue
        author = line[3]
        if author in not_kosher_list:
            continue
        if author not in kosher_list:
            if author not in need_to_check_list and author not in not_kosher_list:
                need_to_check_list.append(author)
                with need_to_check_file.open("w", encoding="utf-8") as need_to_check_new:
                    need_to_check_new.write("\n".join(need_to_check_list))
            continue
        html_content = get_book(line[1], base_url)
        if html_content:
            pattern = r'את הטקסט(?:ים|\[ים\])?\s+לעיל\s+הפיקו\s+מתנדבי\s+<a href="https://benyehuda\.org/">פרויקט בן־יהודה באינטרנט</a>\.\s*<br\s*/?>\s*הכל\s+זמין\s+תמיד\s+בכתובת\s+הבאה:\s*<br\s*/?>\s*<a href="https://benyehuda\.org/read/\d+">https://benyehuda\.org/read/\d+</a>'
            html_content = re.sub(pattern, '', html_content)
            title, author, body = extract_html_info(html_content)
            processed_text = process_body_html(body).splitlines()
            output_text = [f"<h1>{title}</h1>" if title else f"<h1>{line[2]}</h1>", author if author else (line[3] if line[3] else "")] + [adjust_html_tag_spaces(line).strip() for line in processed_text if line.strip() and line.strip() != "<!DOCTYPE html>"]
            if output_text[2] == title:
                output_text.pop(2)
            join_lines = html.unescape("\n".join(output_text))
            target_path = destination_path / genre_folder_name(line[8]) / sanitize_filename(line[3])
            target_path.mkdir(parents=True, exist_ok=True)
            target_file = target_path / f"{sanitize_filename(line[2])}.txt"
            num = 1
            while target_file.exists():
                num += 1
                target_file = target_path / f"{sanitize_filename(line[2])}_{num}.txt"
            with target_file.open("w", encoding="utf-8") as output:
                output.write(join_lines)
            write_to_csv(csv_path, line)


url = "https://raw.githubusercontent.com/projectbenyehuda/public_domain_dump/refs/heads/master/pseudocatalogue.csv"
kosher_file = Path(__file__).parent / "kosher_file.txt"
not_kosher_file = Path(__file__).parent / "not_kosher_file.txt"
need_to_check_file = Path(__file__).parent / "need_to_check.txt"
base_url = "https://raw.githubusercontent.com/projectbenyehuda/public_domain_dump/refs/heads/master/html"
csv_path = Path(__file__).parent / "list.csv"
destination_path = Path(__file__).parent.parent / "ספרים" / "לא ממויין"

main(url, kosher_file, base_url, not_kosher_file, need_to_check_file, csv_path, destination_path)
