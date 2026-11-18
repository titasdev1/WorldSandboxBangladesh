#!/usr/bin/env python3
"""Reject invalid bool(...) constructor calls in Godot GDScript source files.

Godot 4.x does not provide a bool() constructor. Boolean-returning expressions
should use their native bool value or an explicit comparison such as == true.
This scanner ignores comments and quoted strings, including triple-quoted text.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def find_invalid_bool_calls(source: str) -> list[tuple[int, int]]:
    locations: list[tuple[int, int]] = []
    index = 0
    line = 1
    column = 1
    length = len(source)

    while index < length:
        char = source[index]

        if char == "\n":
            index += 1
            line += 1
            column = 1
            continue

        if char == "#":
            while index < length and source[index] != "\n":
                index += 1
                column += 1
            continue

        if char in ("'", '"'):
            delimiter = char * 3 if source.startswith(char * 3, index) else char
            index += len(delimiter)
            column += len(delimiter)
            while index < length:
                if source.startswith(delimiter, index):
                    index += len(delimiter)
                    column += len(delimiter)
                    break
                if source[index] == "\\":
                    index += 1
                    column += 1
                    if index < length:
                        if source[index] == "\n":
                            line += 1
                            column = 1
                        else:
                            column += 1
                        index += 1
                    continue
                if source[index] == "\n":
                    line += 1
                    column = 1
                    index += 1
                    continue
                index += 1
                column += 1
            continue

        if char.isalpha() or char == "_":
            token_line, token_column = line, column
            start = index
            while index < length and (source[index].isalnum() or source[index] == "_"):
                index += 1
                column += 1
            token = source[start:index]
            if token == "bool":
                lookahead = index
                while lookahead < length and source[lookahead].isspace():
                    lookahead += 1
                if lookahead < length and source[lookahead] == "(":
                    locations.append((token_line, token_column))
            continue

        index += 1
        column += 1

    return locations


def scan_tree(root: Path) -> list[tuple[Path, int, int]]:
    findings: list[tuple[Path, int, int]] = []
    for path in sorted(root.rglob("*.gd")):
        if ".godot" in path.parts or ".git" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        for line, column in find_invalid_bool_calls(source):
            findings.append((path, line, column))
    return findings


def self_test() -> None:
    valid = '''
# bool(comment_only)
var label = "bool(string_only)"
var single = 'bool(single_quoted)'
var multiline = """bool(also_string_only)"""
var enabled: bool = flag == true
'''
    invalid = 'var a = bool(value)\nif not bool(world.get("active")):\n    pass\n'
    if find_invalid_bool_calls(valid):
        raise SystemExit("Self-test failed: false positive in comments/strings.")
    found = find_invalid_bool_calls(invalid)
    if len(found) != 2 or found[0] != (1, 9) or found[1] != (2, 8):
        raise SystemExit(f"Self-test failed: unexpected detection result {found!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("GDSCRIPT_BOOL_CAST_CHECKER_SELF_TEST_PASS")
        return 0

    findings = scan_tree(args.root.resolve())
    if findings:
        for path, line, column in findings:
            print(f"{path}:{line}:{column}: invalid bool(...) call; use the boolean value or an explicit comparison")
        print(f"GDSCRIPT_BOOL_CAST_CHECK_FAILED: {len(findings)} invalid call(s)")
        return 1

    print("GDSCRIPT_BOOL_CAST_CHECK_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
