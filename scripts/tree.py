#!/usr/bin/env python3
"""Генерирует doc/tree: дерево файлов проекта и подсчёт строк кода.

Список файлов берётся через `git ls-files --cached --others --exclude-standard` -
это ровно те файлы, которые git реально закоммитил бы, т.е. правила .gitignore
учитываются автоматически, без ручного парсинга.

Полностью перезаписывает doc/tree при каждом запуске. Вызывается pre-commit
хуком (.githooks/pre-commit), можно запустить и вручную: `python3 scripts/tree.py`.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "doc" / "tree"


def list_project_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(line for line in result.stdout.splitlines() if line)


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def build_tree_lines(paths: list[str]) -> list[str]:
    tree: dict = {}
    for rel_path in paths:
        parts = rel_path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node.setdefault(parts[-1], None)

    lines: list[str] = ["."]

    def render(node: dict, prefix: str) -> None:
        entries = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0]))
        for index, (name, child) in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if child is not None:
                extension = "    " if is_last else "│   "
                render(child, prefix + extension)

    render(tree, "")
    return lines


def build_loc_summary(paths: list[str]) -> list[str]:
    by_extension: dict[str, int] = defaultdict(int)
    total = 0
    for rel_path in paths:
        path = ROOT / rel_path
        if not path.is_file():
            continue
        lines = count_lines(path)
        total += lines
        extension = path.suffix or "(без расширения)"
        by_extension[extension] += lines

    summary = [f"Всего файлов: {len(paths)}", f"Всего строк: {total}", "", "По расширениям:"]
    for extension, lines in sorted(by_extension.items(), key=lambda kv: kv[1], reverse=True):
        summary.append(f"  {extension:20} {lines}")
    return summary


def main() -> None:
    paths = list_project_files()

    output_lines = ["Структура проекта", "=" * 60, ""]
    output_lines.extend(build_tree_lines(paths))
    output_lines.append("")
    output_lines.append("Строки кода")
    output_lines.append("=" * 60)
    output_lines.extend(build_loc_summary(paths))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"Записано в {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
