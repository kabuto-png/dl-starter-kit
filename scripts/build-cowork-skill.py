#!/usr/bin/env python3
"""
build-cowork-skill.py

Convert the AKC skill in dl_starter_kit to a Cowork-compatible .skill bundle.

Strips Claude Code-only syntax from SKILL.md and zips the cleaned skill
folder as <name>.skill, ready to install in Claude Cowork via
"Copy to your skills".

Adapted from unclaude-code/scripts/convert-skills-to-cowork.py.

Usage:
    python3 scripts/build-cowork-skill.py
    python3 scripts/build-cowork-skill.py --input skill --output cowork-skills
"""

import argparse
import re
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STRIP_PATTERNS = [
    (r'`/(?:ck|uc|mkt):[\w-]+[^`]*`', ''),
    (r'\bAskUserQuestion\b', 'ask the user'),
    (r'\bTaskCreate\b|\bTaskUpdate\b|\bTaskList\b', ''),
    (r'\bExplore\b subagents?', 'subagents'),
    (r'`(?:ck|uc|mkt):[\w-]+`', ''),
    (r'^name: (?:ck|uc|mkt):(.+)$', r'name: \1'),
    (r'^argument-hint:.*\n', ''),
]


def clean(content: str) -> str:
    for pattern, replacement in STRIP_PATTERNS:
        flags = re.MULTILINE if pattern.startswith('^') else 0
        content = re.sub(pattern, replacement, content, flags=flags)
    return re.sub(r'\n{3,}', '\n\n', content).strip() + '\n'


def skill_name_from_frontmatter(content: str, fallback: str) -> str:
    m = re.search(r'^name:\s*(\S+)\s*$', content, re.MULTILINE)
    return m.group(1) if m else fallback


def stage_skill(source: Path, work: Path) -> Path | None:
    skill_md = source / "SKILL.md"
    if not skill_md.exists():
        return None

    raw = skill_md.read_text(encoding='utf-8')
    name = skill_name_from_frontmatter(raw, source.name)
    out = work / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    (out / "SKILL.md").write_text(clean(skill_md.read_text(encoding='utf-8')), encoding='utf-8')

    # Copy bundled markdown assets alongside SKILL.md
    for extra in ("examples.md", "eval-cases.md"):
        f = source / extra
        if f.exists():
            (out / extra).write_text(clean(f.read_text(encoding='utf-8')), encoding='utf-8')

    for subdir in ("references", "assets"):
        src = source / subdir
        if src.exists():
            shutil.copytree(src, out / subdir)

    return out


def package(skill_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_file = output_dir / f"{skill_dir.name}.skill"
    with zipfile.ZipFile(skill_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(skill_dir.rglob('*')):
            if f.is_file():
                zf.write(f, f"{skill_dir.name}/{f.relative_to(skill_dir)}")
    return skill_file


def find_skills(path: Path) -> list[Path]:
    if (path / "SKILL.md").exists():
        return [path]
    return sorted(d for d in path.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', '-i', type=Path, default=REPO_ROOT / 'skill')
    p.add_argument('--output', '-o', type=Path, default=REPO_ROOT / 'cowork-skills')
    args = p.parse_args()

    src = args.input.resolve()
    out = args.output.resolve()
    work = Path('/tmp/dl-cowork-build')
    if work.exists():
        shutil.rmtree(work)

    if not src.exists():
        raise SystemExit(f"Input not found: {src}")

    skills = find_skills(src)
    if not skills:
        raise SystemExit(f"No SKILL.md under {src}")

    print(f"Building {len(skills)} cowork skill(s) -> {out}\n")
    for s in skills:
        print(f"  {s.name} ...", end=' ', flush=True)
        staged = stage_skill(s, work)
        if not staged:
            print("skip (no SKILL.md)")
            continue
        result = package(staged, out)
        print(f"ok -> {result.relative_to(REPO_ROOT) if result.is_relative_to(REPO_ROOT) else result}")

    shutil.rmtree(work, ignore_errors=True)
    print(f"\nInstall in Cowork: open the .skill file or use 'Copy to your skills'.")


if __name__ == "__main__":
    main()
