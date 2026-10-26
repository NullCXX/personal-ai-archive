"""Small stdio MCP server; line-delimited JSON-RPC, Python 3.10+, no dependencies."""
import json
import os
from pathlib import Path
import sys
from archive_sync import ArchiveError, GitHub

SUPPORTED = ('2024-11-05', '2025-03-26', '2025-06-18', '2025-11-25')
SCHEMAS = json.loads((Path(__file__).resolve().parents[1] / 'integrations/tool-definitions.json').read_text(encoding='utf-8'))


def available_tools():
    return [t for t in SCHEMAS if t['name'] != 'archive_record' or os.getenv('ARCHIVE_ALLOW_WRITE') == '1']


def respond(message):
    if not isinstance(message, dict):
        return {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'Invalid request'}}
    if 'id' not in message:
        return None
    request_id, method, params = message['id'], message.get('method'), message.get('params') or {}
    result = None
    if method == 'initialize':
        version = params.get('protocolVersion')
        result = {'protocolVersion': version if version in SUPPORTED else SUPPORTED[-1], 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'personal-ai-archive', 'version': '1.0.0'}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': available_tools()}
    elif method == 'tools/call':
        name, args = params.get('name'), params.get('arguments') or {}
        if name not in [t['name'] for t in available_tools()]:
            return {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32602, 'message': 'Tool unavailable; writes require ARCHIVE_ALLOW_WRITE=1.'}}
        try:
            if not isinstance(args, dict):
                raise ArchiveError('Tool arguments must be an object.')
            client = GitHub()
            if name == 'archive_read':
                if set(args) - {'path', 'ref'} or 'path' not in args:
                    raise ArchiveError('Expected path and optional ref.')
                sha, body = client.read(args['path'], args.get('ref'))
                text = f'<!-- commit: {sha} -->\n' + body
            elif name == 'archive_snapshot':
                if args:
                    raise ArchiveError('Snapshot takes no arguments.')
                text = client.snapshot()
            else:
                text = json.dumps(client.record(args, auto_merge=os.getenv('ARCHIVE_AUTO_MERGE') == '1'), ensure_ascii=False)
            result = {'content': [{'type': 'text', 'text': text}], 'isError': False}
        except (ArchiveError, ValueError, OSError, TypeError) as e:
            result = {'content': [{'type': 'text', 'text': str(e)}], 'isError': True}
    else:
        return {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32601, 'message': 'Method not found'}}
    return {'jsonrpc': '2.0', 'id': request_id, 'result': result}


def main():
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        try:
            response = respond(json.loads(line))
        except (ValueError, TypeError, AttributeError):
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON-RPC message'}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
