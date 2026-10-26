"""Portable GitHub archive client. Python standard library only; never log credentials."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOTS = ('identity', 'workflow', 'memory', 'skills', 'archive')
DESTINATIONS = {
    'preference': 'memory/preferences', 'lesson': 'memory/lessons',
    'decision': 'memory/decisions', 'workflow': 'workflow/updates',
    'skill': 'skills/updates', 'archive': 'archive/entries',
}
SECRET_PATTERN = re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
RECORD_KEYS = {'category', 'title', 'detail', 'source', 'evidence', 'status', 'supersedes'}


class ArchiveError(RuntimeError):
    pass


class ApiError(ArchiveError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(f'GitHub HTTP {status}: {message}')


def credential(required=True):
    for key in ('ARCHIVE_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'):
        if os.getenv(key):
            return os.environ[key]
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    try:
        result = subprocess.run(['git', 'credential', 'fill'],
            input='protocol=https\nhost=github.com\n\n', text=True,
            capture_output=True, env=env, timeout=20)
        fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        if fields.get('password'):
            return fields['password']
    except (OSError, subprocess.TimeoutExpired):
        pass
    if required:
        raise ArchiveError('No GitHub credential. Authorize this repository in your tool host.')
    return None


def safe_path(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+\.md', value):
        raise ArchiveError('Only repository-relative Markdown paths are allowed.')
    if value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/')):
        raise ArchiveError('Invalid repository path.')
    return value


def validate_record(record):
    if not isinstance(record, dict) or set(record) - RECORD_KEYS:
        raise ArchiveError('Unknown record fields.')
    for key in RECORD_KEYS - {'supersedes'}:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ArchiveError(f'Missing nonempty string: {key}')
    normalized = {k: v.strip() for k, v in record.items() if isinstance(v, str)}
    if normalized['category'] not in DESTINATIONS:
        raise ArchiveError('Invalid category.')
    if normalized['status'] not in ('confirmed', 'proposed'):
        raise ArchiveError('Status must be confirmed or proposed.')
    if len(normalized['title']) > 120 or '\n' in normalized['title'] or '\r' in normalized['title']:
        raise ArchiveError('Title must be one line, at most 120 characters.')
    if 'supersedes' in record and (not isinstance(record['supersedes'], str) or not re.fullmatch(r'[a-f0-9]{32}', normalized.get('supersedes', ''))):
        raise ArchiveError('supersedes must be an existing 32-character record ID.')
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    if len(raw.encode('utf-8')) > 24000 or '{{' in raw or SECRET_PATTERN.search(raw):
        raise ArchiveError('Record contains placeholders, likely credentials, or exceeds 24 KB.')
    return normalized


def record_content(record, created_at=None):
    record = validate_record(record)
    digest = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:32]
    path = f"{DESTINATIONS[record['category']]}/{digest}.md"
    timestamp = created_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:
        if datetime.fromisoformat(timestamp).tzinfo is None:
            raise ValueError('Timezone required')
    except (ValueError, TypeError):
        raise ArchiveError('Invalid record timestamp.') from None
    meta = {**record, 'id': digest, 'created_at': timestamp}
    # Metadata is Base64 only to make arbitrary source text safe inside an HTML comment.
    encoded = base64.b64encode(json.dumps(meta, ensure_ascii=False).encode()).decode()
    text = (f"# AI-EDITABLE: {record['title']}\n\n"
        f"<!-- archive-record-v1:{encoded} -->\n\n"
        f"- record_id: {digest}\n- status: {record['status']}\n"
        f"- category: {record['category']}\n- created_at: {timestamp}\n"
        f"- supersedes: {record.get('supersedes', 'none')}\n\n"
        f"## 来源\n\n{record['source']}\n\n## 依据\n\n{record['evidence']}\n\n"
        f"## 内容\n\n{record['detail']}\n")
    return path, text, digest


class GitHub:
    def __init__(self, repo=None):
        self.repo = repo or os.getenv('ARCHIVE_REPO', 'NullCXX/personal-ai-archive')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', self.repo):
            raise ArchiveError('Invalid repository identifier.')
        self.prefix = '/repos/' + self.repo
        self.token = credential(required=False)

    def api(self, method, path, data=None):
        if method != 'GET' and not self.token:
            raise ArchiveError('Writing requires a GitHub credential authorized for this repository.')
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json', 'User-Agent': 'personal-ai-archive/1'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request('https://api.github.com' + self.prefix + path,
            data=json.dumps(data).encode() if data is not None else None,
            method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            try:
                message = json.loads(e.read()).get('message', 'Request failed')
            except (ValueError, UnicodeError):
                message = 'Request failed'
            raise ApiError(e.code, message) from None
        except (urllib.error.URLError, TimeoutError):
            raise ArchiveError('GitHub network request failed; retry without changing record input.') from None

    def head(self):
        return self.api('GET', '/git/ref/heads/main')['object']['sha']

    def pin(self, ref=None):
        if ref in (None, 'main'):
            return self.head()
        if not re.fullmatch(r'[a-f0-9]{40}', ref):
            raise ArchiveError('ref must be main or a full 40-character commit SHA.')
        return ref

    def read(self, path, ref=None):
        path, sha = safe_path(path), self.pin(ref)
        result = self.api('GET', '/contents/' + path + '?ref=' + sha)
        if not isinstance(result, dict) or result.get('type') != 'file' or result.get('encoding') != 'base64' or result.get('size', 0) > 128000:
            raise ArchiveError('Expected a Markdown file no larger than 128 KB.')
        return sha, base64.b64decode(result['content']).decode('utf-8')

    def tree(self, sha):
        result = self.api('GET', '/git/trees/' + sha + '?recursive=1')
        if result.get('truncated'):
            raise ArchiveError('Git tree truncated; cannot safely read a complete archive.')
        return result['tree']

    def snapshot(self):
        sha = self.head()
        paths = sorted(x['path'] for x in self.tree(sha) if x['type'] == 'blob' and x['mode'] == '100644' and x['path'].endswith('.md') and (x['path'] == 'AGENTS.md' or x['path'].split('/')[0] in ROOTS))
        if len(paths) > 500:
            raise ArchiveError('Snapshot exceeds 500 files; use targeted archive_read.')
        with ThreadPoolExecutor(max_workers=6) as pool:
            chunks = list(pool.map(lambda p: f'\n\n<!-- file: {p} -->\n' + self.read(p, sha)[1], paths))
        text = f'# AI-SNAPSHOT: {self.repo}\n\ncommit: {sha}\n' + ''.join(chunks)
        if len(text.encode()) > 2_000_000:
            raise ArchiveError('Snapshot exceeds 2 MB; use targeted archive_read.')
        return text

    def pull(self, branch, title, body):
        query = urllib.parse.urlencode({'state': 'open', 'head': self.repo.split('/')[0] + ':' + branch, 'base': 'main'})
        existing = self.api('GET', '/pulls?' + query)
        if existing:
            return existing[0]
        return self.api('POST', '/pulls', {'title': title, 'head': branch, 'base': 'main', 'body': body})

    def merge_checked(self, pr, timeout=120):
        deadline = time.monotonic() + timeout
        while True:
            current = self.api('GET', f"/pulls/{pr['number']}")
            if current.get('merged'):
                return True, 'already merged'
            if current['head']['sha'] != pr['head']['sha']:
                return False, 'PR head changed; inspect before merging'
            checks = self.api('GET', f"/commits/{pr['head']['sha']}/check-runs?per_page=100")['check_runs']
            trusted = [c for c in checks if c['name'] == 'archive-validate' and c.get('app', {}).get('slug') == 'github-actions' and c.get('head_sha') == pr['head']['sha']]
            latest = max(trusted, key=lambda c: c['id']) if trusted else None
            if latest and latest['status'] == 'completed':
                if latest['conclusion'] != 'success':
                    return False, 'archive-validate did not succeed'
                merged = self.api('PUT', f"/pulls/{pr['number']}/merge", {'merge_method': 'squash', 'sha': pr['head']['sha']})
                return bool(merged.get('merged')), merged.get('message', '')
            if time.monotonic() >= deadline:
                return False, 'CI pending; PR retained for retry'
            time.sleep(min(5, max(0, deadline - time.monotonic())))

    def record(self, record, auto_merge=False, timeout=120):
        path, content, digest = record_content(record)
        base = self.head()
        tree = self.tree(base)
        if record.get('supersedes') and not any(x['path'].endswith('/' + record['supersedes'] + '.md') for x in tree):
            raise ArchiveError('supersedes record does not exist on main.')
        if any(x['path'] == path for x in tree):
            return {'path': path, 'commit': base, 'merged': True, 'duplicate': True}
        branch = 'ai/record-' + digest
        try:
            self.api('POST', '/git/refs', {'ref': 'refs/heads/' + branch, 'sha': base})
        except ApiError as e:
            if e.status != 422:
                raise
        branch_sha = self.api('GET', '/git/ref/heads/' + branch)['object']['sha']
        try:
            self.read(path, branch_sha)
        except ApiError as e:
            if e.status != 404:
                raise
            self.api('PUT', '/contents/' + path, {'message': f"memory({record['category']}): {record['title']}", 'content': base64.b64encode(content.encode()).decode(), 'branch': branch})
        # Check the entire branch delta, not only the intended file, before creating or merging a PR.
        comparison = self.api('GET', '/compare/' + base + '...' + branch)
        files = comparison.get('files', [])
        if len(files) != 1 or files[0]['filename'] != path or files[0]['status'] != 'added':
            raise ArchiveError('Record branch contains unexpected changes; inspect manually.')
        pr = self.pull(branch, f"memory({record['category']}): {record['title']}",
            f"新增一条带来源的 {record['category']} 记录。\n\nPath: `{path}`\nStatus: `{record['status']}`\n\n通过 archive-validate 后才允许工具自动合并。")
        result = {'path': path, 'commit': pr['head']['sha'], 'pull_request': pr['html_url'], 'merged': False, 'duplicate': False}
        if auto_merge:
            try:
                result['merged'], result['message'] = self.merge_checked(pr, timeout)
            except ArchiveError as e:
                result['message'] = str(e)
        return result

    def history(self):
        return [{'sha': c['sha'], 'message': c['commit']['message'], 'url': c['html_url']} for c in self.api('GET', '/commits?sha=main&per_page=100')]

    def restore(self, sha, auto_merge=False, timeout=120, dispatch_check=False):
        sha = self.pin(sha)
        base = self.head()
        comparison = self.api('GET', '/compare/' + sha + '...' + base)
        if comparison['status'] not in ('ahead', 'identical'):
            raise ArchiveError('Restore target must be an ancestor of main.')
        old_tree, current_tree = self.tree(sha), self.tree(base)
        def files(tree):
            return {x['path']: x for x in tree if x['type'] == 'blob' and x['path'].split('/')[0] in ROOTS}
        target, current = files(old_tree), files(current_tree)
        required = ('identity/profile.md', 'workflow/preferences.md', 'memory/preferences.md', 'skills/inventory.md', 'archive/index.md')
        if not all(p in target for p in required):
            raise ArchiveError('Target predates archive initialization or lacks required templates.')
        edits = [{'path': p, 'mode': target.get(p, current.get(p))['mode'], 'type': 'blob', 'sha': target[p]['sha'] if p in target else None} for p in sorted(set(target) | set(current)) if target.get(p, {}).get('sha') != current.get(p, {}).get('sha')]
        if not edits:
            return {'merged': True, 'unchanged': True, 'commit': base}
        for edit in edits:
            safe_path(edit['path'])
            if edit['mode'] != '100644':
                raise ArchiveError('Restore target contains unsupported file modes.')
        tree = self.api('POST', '/git/trees', {'base_tree': base, 'tree': edits})
        commit = self.api('POST', '/git/commits', {'message': 'restore: archive to ' + sha, 'tree': tree['sha'], 'parents': [base]})
        branch = 'restore/' + sha[:12] + '-' + commit['sha'][:8]
        self.api('POST', '/git/refs', {'ref': 'refs/heads/' + branch, 'sha': commit['sha']})
        pr = self.pull(branch, 'restore: archive to ' + sha[:12], f'按所有者恢复指令，将五个档案目录恢复到 `{sha}`。\n保留配置与完整提交历史；请检查新增、修改和删除列表。')
        result = {'commit': commit['sha'], 'pull_request': pr['html_url'], 'merged': False, 'target': sha}
        if auto_merge:
            try:
                if dispatch_check:
                    self.api('POST', '/actions/workflows/validate.yml/dispatches', {'ref': branch, 'inputs': {'base_sha': base}})
                result['merged'], result['message'] = self.merge_checked(pr, timeout)
            except ArchiveError as e:
                result['message'] = str(e)
        return result

    def protect(self):
        body = {'required_status_checks': {'strict': True, 'contexts': ['archive-validate']},
            'enforce_admins': True, 'required_pull_request_reviews': {'dismiss_stale_reviews': True, 'require_code_owner_reviews': False, 'required_approving_review_count': 0},
            'restrictions': None, 'required_linear_history': True, 'allow_force_pushes': False,
            'allow_deletions': False, 'required_conversation_resolution': True}
        self.api('PUT', '/branches/main/protection', body)
        value = self.api('GET', '/branches/main/protection')
        if value.get('allow_force_pushes', {}).get('enabled') or value.get('allow_deletions', {}).get('enabled') or not value.get('enforce_admins', {}).get('enabled'):
            raise ArchiveError('Protection verification failed.')
        return {'enabled': True, 'url': value.get('url')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    read = sub.add_parser('read'); read.add_argument('--path', required=True); read.add_argument('--ref')
    sub.add_parser('snapshot'); sub.add_parser('history'); sub.add_parser('protect')
    record = sub.add_parser('record'); record.add_argument('--input', required=True)
    restore = sub.add_parser('restore'); restore.add_argument('--sha', required=True)
    restore.add_argument('--dispatch-check', action='store_true', help='Trigger validation for GITHUB_TOKEN-created PRs; requires Actions: write.')
    for p in (record, restore):
        p.add_argument('--auto-merge', action='store_true'); p.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    client = GitHub()
    if args.command == 'read':
        sha, content = client.read(args.path, args.ref)
        print(f'<!-- commit: {sha} -->\n' + content); return 0
    if args.command == 'snapshot':
        print(client.snapshot()); return 0
    if args.command == 'record':
        value = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        result = client.record(value, args.auto_merge, args.timeout)
    elif args.command == 'restore':
        result = client.restore(args.sha, args.auto_merge, args.timeout, args.dispatch_check)
    else:
        result = getattr(client, args.command)()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if getattr(args, 'auto_merge', False) and not result.get('merged') else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (ArchiveError, OSError, ValueError) as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
