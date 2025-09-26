# // Chg_AUTOEXEC_2609: автоматизация выставления auto_execute для задач
"""Utility to normalize `auto_execute` flags in orchestrator manifests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


# // Chg_AUTOEXEC_2609: параметры по умолчанию
DEFAULT_INBOX_RELATIVE = Path("orchestrator") / "inbox"
DEFAULT_DIFF_ROOT = Path("orchestrator") / "outbox" / "auto_execute_patches"


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for the auto-execute updater."""

    parser = argparse.ArgumentParser(
        description=(
            "Update auto_execute flags in orchestrator manifests based on priority and "
            "require_human_switch markers."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to repository root (default: parent of scripts/ directory).",
    )
    parser.add_argument(
        "--inbox",
        type=Path,
        default=DEFAULT_INBOX_RELATIVE,
        help="Relative path (from repo root) to manifests inbox directory.",
    )
    parser.add_argument(
        "--glob",
        default="*.json",
        help="Glob pattern for selecting manifests (default: *.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )
    parser.add_argument(
        "--write-diff",
        action="store_true",
        help="Write unified diff files alongside updated manifests.",
    )
    parser.add_argument(
        "--diff-root",
        type=Path,
        default=DEFAULT_DIFF_ROOT,
        help="Relative path (from repo root) where diff files will be stored.",
    )

    return parser.parse_args()


def update_auto_flag(manifest: dict) -> Tuple[bool, bool]:
    """Apply auto_execute flag rules.

    Returns a tuple of two booleans: (changed, set_true).
    """

    priority = manifest.get("priority")
    require_human = manifest.get("require_human_switch", False)

    should_auto = priority != "P0" and not require_human

    if should_auto:
        if manifest.get("auto_execute") is True:
            return False, True
        manifest["auto_execute"] = True
        return True, True

    if "auto_execute" in manifest:
        return False, False

    manifest["auto_execute"] = False
    return True, False


def ensure_trailing_newline(text: str) -> str:
    """Return text with a single trailing newline."""

    return text if text.endswith("\n") else text + "\n"


def read_text(path: Path) -> str:
    """Read UTF-8 text from a file."""

    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text to a file, ensuring directories exist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_diff(original: str, updated: str, rel_path: Path) -> str:
    """Generate a unified diff between two versions of text."""

    import difflib

    old_lines = original.splitlines(keepends=True)
    new_lines = updated.splitlines(keepends=True)
    diff_iter = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{rel_path.as_posix()}",
        tofile=f"b/{rel_path.as_posix()}",
    )
    return "".join(diff_iter)


def discover_manifests(root: Path, rel_inbox: Path, pattern: str) -> Iterable[Path]:
    """Yield manifest file paths matching the pattern."""

    inbox = root / rel_inbox
    if not inbox.exists():
        raise FileNotFoundError(f"Inbox directory not found: {inbox}")
    yield from inbox.glob(pattern)


def process_manifest(
    repo_root: Path,
    manifest_path: Path,
    dry_run: bool,
    write_diff: bool,
    diff_root: Path,
) -> Tuple[bool, str]:
    """Process a single manifest file.

    Returns (changed, message).
    """

    rel_path = manifest_path.relative_to(repo_root)
    try:
        original_text = read_text(manifest_path)
        manifest_data = json.loads(original_text)
    except json.JSONDecodeError as exc:
        return False, f"ERROR {rel_path}: invalid JSON ({exc})"
    except OSError as exc:
        return False, f"ERROR {rel_path}: {exc}"

    changed, set_true = update_auto_flag(manifest_data)

    if not changed:
        state = "auto_execute=true" if set_true else "auto_execute=false"
        return False, f"SKIP  {rel_path}: already {state}"

    updated_text = json.dumps(manifest_data, ensure_ascii=False, indent=2)
    updated_text = ensure_trailing_newline(updated_text)

    if dry_run:
        action = "would set" if set_true else "would ensure"
        return True, f"DRY   {rel_path}: {action} auto_execute={'true' if set_true else 'false'}"

    write_text(manifest_path, updated_text)

    diff_message = ""
    if write_diff:
        diff_text = make_diff(original_text, updated_text, rel_path)
        diff_path = repo_root / diff_root / rel_path.with_suffix(".diff")
        write_text(diff_path, diff_text)
        diff_message = f", diff -> {diff_path.relative_to(repo_root)}"

    return True, (
        f"UPDATE {rel_path}: auto_execute={'true' if set_true else 'false'}{diff_message}"
    )


def main() -> int:
    """Entry point for CLI usage."""

    args = parse_arguments()
    repo_root = args.repo_root.resolve()
    rel_inbox = args.inbox
    pattern = args.glob
    diff_root = args.diff_root

    try:
        manifests = sorted(discover_manifests(repo_root, rel_inbox, pattern))
    except FileNotFoundError as exc:
        print(str(exc), flush=True)
        return 1

    if not manifests:
        print(
            f"No manifests found in {(repo_root / rel_inbox)} matching pattern '{pattern}'.",
            flush=True,
        )
        return 0

    changed_files: List[str] = []

    for manifest_path in manifests:
        changed, message = process_manifest(
            repo_root=repo_root,
            manifest_path=manifest_path,
            dry_run=args.dry_run,
            write_diff=args.write_diff,
            diff_root=diff_root,
        )
        print(message, flush=True)
        if changed and not args.dry_run:
            changed_files.append(str(manifest_path.relative_to(repo_root)))

    summary_prefix = "Changed files" if not args.dry_run else "Files needing changes"
    summary_value = len(changed_files)
    print(f"{summary_prefix}: {summary_value}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
