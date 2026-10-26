import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from archive_sync import ArchiveError, ApiError, GitHub, record_content, safe_path, validate_record
from validate_archive import validate_changes, validate_file
import mcp_server

RECORD = {'category': 'lesson', 'title': 'Verified lesson', 'detail': 'Use a fixed commit when reading files.', 'source': 'unit-test', 'evidence': 'Two files shared a commit.', 'status': 'confirmed'}


class RecordTests(unittest.TestCase):
    def test_public_client_can_initialize_without_credential(self):
        with patch('archive_sync.credential', return_value=None):
            client = GitHub('owner/public-repo')
        self.assertIsNone(client.token)

    def test_anonymous_client_cannot_write(self):
        with patch('archive_sync.credential', return_value=None):
            client = GitHub('owner/public-repo')
        with self.assertRaises(ArchiveError):
            client.api('POST', '/git/refs', {})

    def test_retries_produce_same_path(self):
        a = record_content(RECORD, '2026-01-01T00:00:00+00:00')
        b = record_content(dict(reversed(list(RECORD.items()))), '2026-02-01T00:00:00+00:00')
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[2], b[2])
        self.assertNotEqual(a[1], b[1])

    def test_records_are_verified_and_tampering_rejected(self):
        path, body, _ = record_content(RECORD)
        validate_file(path, body)
        with self.assertRaises(ArchiveError):
            validate_file(path, body.replace('Use a fixed commit', 'Trust arbitrary files'))

    def test_placeholders_credentials_and_invalid_category_rejected(self):
        for field, value in [('detail', '{{unknown}}'), ('detail', 'ghp_' + 'a' * 36), ('category', 'identity'), ('status', 'guessed'), ('title', 'a\nb'), ('supersedes', 2)]:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ArchiveError):
                    validate_record({**RECORD, field: value})

    def test_path_traversal_rejected(self):
        for path in ('../secret.md', '/etc/secret.md', 'identity/../secret.md', 'identity//x.md', 'identity%2fsecret.md', 'x.md?ref=evil'):
            with self.assertRaises(ArchiveError):
                safe_path(path)

    def test_automatic_changes_cannot_delete_or_modify_identity(self):
        for status, path in [('D', 'memory/lessons/x.md'), ('M', 'memory/preferences.md'), ('A', 'identity/new.md'), ('M', '.github/workflows/validate.yml')]:
            with self.assertRaises(ArchiveError):
                validate_changes([(status, path)], 'ai/record-test')
        validate_changes([('A', 'memory/lessons/' + 'a' * 32 + '.md')], 'ai/record-test')

    def test_restore_cannot_replace_workflow(self):
        with self.assertRaises(ArchiveError):
            validate_changes([('M', '.github/workflows/validate.yml')], 'restore/test')
        validate_changes([('D', 'memory/lessons/x.md')], 'restore/test')


class MergeTests(unittest.TestCase):
    def client(self):
        return GitHub.__new__(GitHub)

    def test_failed_check_never_merges(self):
        client = self.client()
        pr = {'number': 1, 'head': {'sha': 'a' * 40}}
        def api(method, path, data=None):
            self.assertEqual(method, 'GET')
            if path.startswith('/pulls/'):
                return pr
            return {'check_runs': [{'id': 1, 'name': 'archive-validate', 'app': {'slug': 'github-actions'}, 'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'failure'}]}
        client.api = api
        self.assertFalse(client.merge_checked(pr, timeout=0)[0])

    def test_spoofed_check_never_merges(self):
        client = self.client()
        pr = {'number': 1, 'head': {'sha': 'a' * 40}}
        def api(method, path, data=None):
            self.assertEqual(method, 'GET')
            if path.startswith('/pulls/'):
                return pr
            return {'check_runs': [{'id': 1, 'name': 'archive-validate', 'app': {'slug': 'other-app'}, 'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'success'}]}
        client.api = api
        self.assertFalse(client.merge_checked(pr, timeout=0)[0])

    def test_changed_head_never_merges(self):
        client = self.client()
        client.api = lambda *a: {'head': {'sha': 'b' * 40}}
        self.assertFalse(client.merge_checked({'number': 1, 'head': {'sha': 'a' * 40}}, timeout=0)[0])

    def test_merge_pins_validated_sha(self):
        client = self.client()
        pr = {'number': 1, 'head': {'sha': 'a' * 40}}
        def api(method, path, data=None):
            if method == 'PUT':
                self.assertEqual(data['sha'], 'a' * 40)
                return {'merged': True}
            if path.startswith('/pulls/'):
                return pr
            return {'check_runs': [{'id': 1, 'name': 'archive-validate', 'app': {'slug': 'github-actions'}, 'head_sha': 'a' * 40, 'status': 'completed', 'conclusion': 'success'}]}
        client.api = api
        self.assertTrue(client.merge_checked(pr, timeout=0)[0])

    def test_duplicate_on_main_does_not_write(self):
        client = self.client()
        path = record_content(RECORD)[0]
        client.head = lambda: 'a' * 40
        client.tree = lambda sha: [{'path': path}]
        client.api = lambda *a: self.fail('Duplicate record must not make a mutation')
        self.assertTrue(client.record(RECORD)['duplicate'])

    def test_restore_uses_new_commit_and_retains_config(self):
        client = self.client()
        client.repo = 'owner/repo'
        base, target = 'a' * 40, 'b' * 40
        client.head = lambda: base
        names = ['identity/profile.md','workflow/preferences.md','memory/preferences.md','skills/inventory.md','archive/index.md']
        old = [{'path': p,'type':'blob','mode':'100644','sha':'c' * 40} for p in names]
        current = old + [{'path':'memory/lessons/new.md','type':'blob','mode':'100644','sha':'d' * 40}]
        client.tree = lambda sha: old if sha == target else current
        calls = []
        def api(method,path,data=None):
            calls.append((method,path,data))
            if path.startswith('/compare/'):
                return {'status':'ahead'}
            return {'sha':'e' * 40}
        client.api = api
        client.pull = lambda *a: {'html_url':'https://github.com/owner/repo/pull/1'}
        result = client.restore(target)
        self.assertFalse(result['merged'])
        edits = next(x[2]['tree'] for x in calls if x[1] == '/git/trees')
        self.assertEqual(edits, [{'path':'memory/lessons/new.md','mode':'100644','type':'blob','sha':None}])
        commit = next(x[2] for x in calls if x[1] == '/git/commits')
        self.assertEqual(commit['parents'], [base])
        self.assertFalse(any(x[0] == 'PATCH' for x in calls))
        client.merge_checked = lambda pr, timeout: (True, 'merged')
        calls.clear()
        result = client.restore(target, auto_merge=True, dispatch_check=True)
        self.assertTrue(result['merged'])
        dispatch = next(x[2] for x in calls if x[1] == '/actions/workflows/validate.yml/dispatches')
        self.assertEqual(dispatch['inputs']['base_sha'], base)
        self.assertTrue(dispatch['ref'].startswith('restore/'))


class MCPTests(unittest.TestCase):
    def test_default_read_only(self):
        with patch.dict(os.environ, {'ARCHIVE_ALLOW_WRITE': '0'}):
            response = mcp_server.respond({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
            self.assertEqual([t['name'] for t in response['result']['tools']], ['archive_read', 'archive_snapshot'])
            denied = mcp_server.respond({'id': 2, 'method': 'tools/call', 'params': {'name': 'archive_record', 'arguments': RECORD}})
            self.assertIn('error', denied)

    def test_stdio_handshake_and_notifications(self):
        messages = [{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}}, {'jsonrpc':'2.0','method':'notifications/initialized'}, {'jsonrpc':'2.0','id':2,'method':'ping'}]
        result = subprocess.run([sys.executable, str(Path(mcp_server.__file__))], input='\n'.join(json.dumps(m) for m in messages)+'\n', text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(lines[1]['id'], 2)


if __name__ == '__main__':
    unittest.main()
