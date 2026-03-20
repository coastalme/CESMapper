from __future__ import annotations

import argparse
import configparser
import fnmatch
import os
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "CESMapper"
DEFAULT_ALLOWLIST = ROOT / "release-allowlist.txt"
DEFAULT_METADATA = ROOT / "metadata.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a lean QGIS plugin release archive from an allowlist."
    )
    parser.add_argument(
        "--allowlist",
        default=str(DEFAULT_ALLOWLIST),
        help="Path to the release allowlist file.",
    )
    parser.add_argument(
        "--metadata",
        default=str(DEFAULT_METADATA),
        help="Path to metadata.txt used to derive the version.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output zip path. Defaults to CESMapper-<version>.zip.",
    )
    return parser.parse_args()


def read_version(metadata_path: Path) -> str:
    parser = configparser.ConfigParser()
    with metadata_path.open("r", encoding="utf-8") as metadata_file:
        parser.read_file(metadata_file)

    try:
        return parser["general"]["version"].strip()
    except KeyError as exc:
        raise ValueError(f"Unable to determine plugin version from {metadata_path}") from exc


def read_allowlist(allowlist_path: Path) -> list[str]:
    entries: list[str] = []
    with allowlist_path.open("r", encoding="utf-8") as allowlist_file:
        for raw_line in allowlist_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            entries.append(line)

    if not entries:
        raise ValueError(f"Allowlist is empty: {allowlist_path}")

    return entries


def resolve_entry(entry: str) -> list[Path]:
    normalized = entry.replace("\\", "/")

    if normalized.endswith("/"):
        directory = ROOT / normalized.rstrip("/")
        if not directory.is_dir():
            raise FileNotFoundError(f"Allowlisted directory not found: {entry}")
        return sorted(path for path in directory.rglob("*") if path.is_file())

    if any(char in normalized for char in "*?["):
        matches = sorted(
            path
            for path in ROOT.rglob("*")
            if path.is_file() and fnmatch.fnmatch(path.relative_to(ROOT).as_posix(), normalized)
        )
        if not matches:
            raise FileNotFoundError(f"Allowlist pattern matched no files: {entry}")
        return matches

    file_path = ROOT / normalized
    if not file_path.is_file():
        raise FileNotFoundError(f"Allowlisted file not found: {entry}")
    return [file_path]


def collect_files(entries: list[str]) -> list[Path]:
    selected: dict[str, Path] = {}
    for entry in entries:
        for path in resolve_entry(entry):
            relative_path = path.relative_to(ROOT).as_posix()
            selected[relative_path] = path

    if not selected:
        raise ValueError("Allowlist did not resolve to any files")

    return [selected[key] for key in sorted(selected)]


def build_archive(output_path: Path, files: list[Path]) -> None:
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative_path = path.relative_to(ROOT).as_posix()
            archive_name = f"{PLUGIN_NAME}/{relative_path}"
            archive.write(path, archive_name)


def main() -> int:
    args = parse_args()
    allowlist_path = Path(args.allowlist).resolve()
    metadata_path = Path(args.metadata).resolve()

    version = read_version(metadata_path)
    output_path = Path(args.output).resolve() if args.output else ROOT / f"{PLUGIN_NAME}-{version}.zip"

    files = collect_files(read_allowlist(allowlist_path))
    build_archive(output_path, files)

    print(f"Created archive: {output_path.name}")
    print(f"Included files: {len(files)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)