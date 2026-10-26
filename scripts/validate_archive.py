"""Validate archive structure and append-only automatic memory PRs."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
from archive_sync import ArchiveError, DESTINATIONS, ROOTS, SECRET_PATTERN, RECORD_KEYS, record_content

REQUIRED = ('identity/profile.md', 'workflow/preferences.md', 'memory/preferences.md', 'skills/inventory.md', 'archive/index.md', 'AGENTS.md', 'ai-integration.md')


def validate_file(path, text):
    if len(text.encode('utf-8')) > 128000:
        raise ArchiveError(f'{path}: exceeds 128 KB')
    if not re.match(r'^# AI-(READONLY|EDITABLE|INDEX|POLICY|INTEGRATION|REVIEW): ', text):
        raise ArchiveError(f'{path}: missing AI tag on first line')
    if SECRET_PATTERN.search(text):
        raise ArchiveError(f'{path}: possible credential found (value not logged)')
    if str(Path(path).parent).replace('\\', '/') in DESTINATIONS.values():
        if not re.fullmatch(r'[a-f0-9]{32}\.md', Path(path).name):
            raise ArchiveError(f'{path}: invalid record filename')
        found = re.search(r'<!-- archive-record-v1:([A-Za-z0-9+/=]+) -->', text)
        if not found:
            raise ArchiveError(f'{path}: missing record metadata')
        try:
            meta = json.loads(base64.b64decode(found[1], validate=True))
            if set(meta) != (set(meta) & RECORD_KEYS) | {'id', 'created_at'}:
                raise ValueError('Unexpected metadata fields')
            data = {k: v for k, v in meta.items() if k in RECORD_KEYS}
            expected_path, expected, digest = record_content(data, meta['created_at'])
        except (ValueError, KeyError, TypeError) as e:
            raise ArchiveError(f'{path}: invalid metadata') from e
        if expected_path != path or meta['id'] != digest or text != expected:
            raise ArchiveError(f'{path}: record metadata/content/ID mismatch')


def validate_changes(changes, branch):
    for status, path in changes:
        if branch.startswith('restore/'):
            if path.split('/')[0] not in ROOTS or not path.endswith('.md'):
                raise ArchiveError('Restore PR may only change archive Markdown directories.')
        elif branch.startswith('ai/'):
            if status != 'A' or str(Path(path).parent).replace('\\', '/') not in DESTINATIONS.values():
                raise ArchiveError('Automatic memory PRs may only add records in approved directories.')
        elif status == 'D':
            raise ArchiveError('Deletion requires an explicit restore/ branch.')


def validate(root, base=None, branch=''):
    for name in REQUIRED:
        if not (root / name).is_file():
            raise ArchiveError('Missing required file: ' + name)
    count = 0
    for path in root.rglob('*'):
        rel = path.relative_to(root).as_posix()
        if any(p in ('.git', '__pycache__', '.venv', '.local') for p in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise ArchiveError('Symlinks are not allowed: ' + rel)
        if path.is_file() and path.suffix.lower() == '.md':
            validate_file(rel, path.read_text(encoding='utf-8'))
            count += 1
        if path.is_file() and (path.name.startswith('.env') or path.suffix in ('.pem', '.key', '.bundle')):
            raise ArchiveError('Potentially sensitive file in repository: ' + rel)
    if base:
        if not re.fullmatch(r'[a-f0-9]{40}', base):
            raise ArchiveError('base must be a full commit SHA.')
        output = subprocess.check_output(['git', 'diff', '--name-status', '-z', '--no-renames', base, 'HEAD'], cwd=root).decode()
        entries = output.rstrip('\0').split('\0') if output else []
        validate_changes(list(zip(entries[::2], entries[1::2])), branch)
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base'); parser.add_argument('--branch', default='')
    args = parser.parse_args()
    try:
        count = validate(Path(__file__).resolve().parents[1], args.base, args.branch)
        print(f'archive-validate: PASS ({count} Markdown files)')
    except (ArchiveError, ValueError, OSError, subprocess.SubprocessError) as e:
        print('archive-validate: FAIL: ' + str(e), file=sys.stderr)
        sys.exit(1)
