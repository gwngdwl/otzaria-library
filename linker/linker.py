from __future__ import annotations

import asyncio
import bisect
import json
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

import aiohttp
from tqdm.asyncio import tqdm


class SefariaLinkResult(TypedDict):
    refs: list[str] | None
    startChar: int
    endChar: int
    linkFailed: bool
    text: str


class RefData(TypedDict):
    heRef: str
    url: str
    primaryCategory: str


def get_line_number(prefix: list[int], char_index: int) -> int:
    return bisect.bisect_right(prefix, char_index)


async def call_sefaria_linker(session: aiohttp.ClientSession, text: str, title: str) -> tuple[list[SefariaLinkResult], dict[str, RefData]]:
    url = "https://www.sefaria.org/api/find-refs"
    payload = {
        "text": {
            "body": text,
            "title": title
        }
    }
    async with session.post(url, json=payload) as response:
        response.raise_for_status()
        data = await response.json()
    
    await asyncio.sleep(5)
    task_id = data.get("task_id")
    num = 0
    while num < 5:
        async with session.get(f"https://www.sefaria.org/api/async/{task_id}") as response:
            links = await response.json()
        
        if links["state"] == "FAILURE":
            raise Exception("Task did not complete successfully")
        if links["ready"] is False or links["state"] == "PENDING":
            print(f"{links['state']=} {links['ready']=}")
            print("Waiting for linker to be ready...")
            await asyncio.sleep(50)
            num += 1
        else:
            return links["result"]["body"]["results"], links["result"]["body"]["refData"]


async def link_book(session: aiohttp.ClientSession, input_file: Path, output_file: Path | None = None, title: str | None = None, chunk_size: int = 100) -> None:
    output_file = output_file if output_file else input_file.with_suffix(".json")
    title = title if title else input_file.stem
    dict_all = defaultdict(list)
    with input_file.open("r", encoding="utf-8") as file:
        all_lines = file.readlines()
    for i in range((len(all_lines) + chunk_size - 1) // chunk_size):
        lines = all_lines[i * chunk_size:(i + 1) * chunk_size]
        text = "".join(lines)
        lengths = [len(line) for line in lines]
        prefix = [0]
        for ln in lengths:
            prefix.append(prefix[-1] + ln)
        links, ref_data = await call_sefaria_linker(session, text, title)
        for result in links:
            refs = result["refs"]
            if refs is None:
                continue
            refs_dict = {ref: ref_data.get(ref, {}).get("heRef") for ref in refs}
            start_index = result["startChar"]
            end_index = result["endChar"]
            line = get_line_number(prefix, start_index)
            absolute_line = line + i * chunk_size
            line_start_char = prefix[line - 1] if line > 0 else 0
            start_in_line = start_index - line_start_char
            end_in_line = end_index - line_start_char
            converted_link = {"start": start_in_line, "end": end_in_line, "refs": refs_dict}
            dict_all[absolute_line].append(converted_link)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(dict_all, f, ensure_ascii=False, indent=4)


async def process_book(session: aiohttp.ClientSession, file_path: Path, link_path: Path, title: str, semaphore: asyncio.Semaphore) -> None:
    """Process a single book with rate limiting."""
    async with semaphore:
        print(f"Linking {file_path}...")
        try:
            await link_book(session, file_path, link_path, title)
            print(f"Successfully linked {file_path}")
        except Exception as e:
            print(f"Error linking {file_path}: {e}")


async def main() -> None:
    base_path = Path("/workspaces/otzaria-library")
    links_target = base_path / "sefaria_linker" / "links_temp"
    folders = (
        "Ben-YehudaToOtzaria/ספרים/אוצריא",
        "DictaToOtzaria/ספרים/ערוך/אוצריא",
        "OnYourWayToOtzaria/ספרים/אוצריא",
        "OraytaToOtzaria/ספרים/אוצריא",
        "tashmaToOtzaria/ספרים/אוצריא",
        # "sefariaToOtzaria/sefaria_api/ספרים/אוצריא",
        "MoreBooks/ספרים/אוצריא",
        "wiki_jewish_books/ספרים/אוצריא",
    )
    
    # Collect all tasks
    tasks = []
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent operations
    
    async with aiohttp.ClientSession() as session:
        for folder in folders:
            folder_path = base_path / folder
            links_temp_path = links_target / folder.split("/")[0]
            links_temp_path.mkdir(exist_ok=True, parents=True)
            
            for root, _, files in folder_path.walk():
                for file in files:
                    file_path = root / file
                    if file_path.suffix.lower() != ".txt":
                        continue
                    title = " ".join(file_path.parts[folder_path.parts.index("אוצריא") + 1:-1]) + " " + file_path.stem
                    link_path = links_temp_path / f"{file_path.stem}_links.json"
                    if link_path.exists():
                        continue
                    
                    task = process_book(session, file_path, link_path, title, semaphore)
                    tasks.append(task)
        
        # Run all tasks with progress bar
        if tasks:
            await tqdm.gather(*tasks, desc="Processing books")


if __name__ == "__main__":
    asyncio.run(main())
