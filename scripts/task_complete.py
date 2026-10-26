"""Agent task-completion hook: receives a JSON record, adds a sourced memory."""
import json
import os
from pathlib import Path
import sys
from archive_sync import ArchiveError, GitHub

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        if len(sys.argv) != 2:
            raise ArchiveError('Usage: python scripts/task_complete.py <record.json>')
        record = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
        auto_merge = os.getenv('ARCHIVE_AUTO_MERGE') == '1'
        result = GitHub().record(record, auto_merge=auto_merge)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2 if auto_merge and not result.get('merged') else 0)
    except (ArchiveError, ValueError, OSError) as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
