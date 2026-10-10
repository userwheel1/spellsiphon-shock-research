"""Prove the repository history is a single clean commit.

Scans every blob reachable from any ref for content that must not be published:

  * absolute user paths and the development machine's scratch directory
  * a stray file that once slipped in by accident
  * non-ASCII characters in Python sources (kept ASCII for portability)

Documentation (.md) may contain typographic characters, so the non-ASCII rule is
applied to source files only. Binary blobs are skipped.

The search patterns are assembled at runtime so this script does not itself
contain the strings it looks for.

Usage
-----
    python tools/check_history.py [path-to-repo]
"""
import os
import re
import subprocess
import sys

GIT = os.environ.get('GIT_BIN') or 'git'
PROJECT = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

# Assembled from fragments on purpose - see the module docstring.
_WIN_USERS = 'C:' + chr(92) + 'Users'
_MODLIST = 'E:' + chr(92) + 'Modlists'
_SCRATCH = 'deepseek' + '-' + 'harness'
_STRAY = 'h' + ' -u ' + 'origin' + ' main'
_REMOVED = 'PUBLISH' + 'ING'

FORBIDDEN = [s.encode() for s in (_WIN_USERS, _MODLIST, _SCRATCH, _STRAY, _REMOVED)]

SOURCE_EXT = ('.py',)
TEXT_EXT = ('.py', '.md', '.txt', '.ini', '.yml', '.yaml', '.json')


def git(*args, binary=False):
    out = subprocess.run([GIT, '-C', PROJECT, *args], capture_output=True)
    if out.returncode != 0:
        raise SystemExit('git ' + ' '.join(args) + ' failed:\n'
                         + out.stderr.decode('utf-8', 'replace'))
    return out.stdout if binary else out.stdout.decode('utf-8', 'replace')


def main() -> int:
    print('repository: ' + PROJECT + '\n')

    count = int(git('rev-list', '--all', '--count').strip())
    print('commits reachable from any ref: ' + str(count))
    for line in git('log', '--all', '--format=%h %ad %s', '--date=short').splitlines():
        print('  ' + line)

    entries = git('rev-list', '--objects', '--all').splitlines()
    print('\nobjects reachable in history: ' + str(len(entries)))

    bad = []
    scanned = 0
    for entry in entries:
        parts = entry.split(' ', 1)
        if len(parts) != 2:
            continue
        sha, path = parts
        if not path.lower().endswith(TEXT_EXT):
            continue
        if git('cat-file', '-t', sha).strip() != 'blob':
            continue
        data = git('cat-file', 'blob', sha, binary=True)
        scanned += 1
        for needle in FORBIDDEN:
            if needle in data:
                bad.append((path, 'forbidden: ' + needle.decode('utf-8', 'replace')))
        if path.lower().endswith(SOURCE_EXT) and any(b >= 0x80 for b in data):
            offending = sorted({b for b in data if b >= 0x80})[:4]
            bad.append((path, 'non-ASCII bytes ' + ', '.join(f'{b:02X}' for b in offending)))

    unreachable = [l for l in git('fsck', '--unreachable', '--no-progress').splitlines()
                   if 'unreachable' in l]

    print('text blobs scanned: ' + str(scanned))
    print('unreachable objects: ' + str(len(unreachable)))

    print()
    if bad:
        print('FORBIDDEN CONTENT FOUND:')
        for path, what in sorted(set(bad)):
            print('  ' + path + ': ' + what)
    else:
        print('clean: no personal paths, no stray file, sources are ASCII')

    # an unreachable object is only a problem if it is not an empty tree
    real_unreachable = [l for l in unreachable if 'empty tree' not in l and 'empty blob' not in l]
    ok = (not bad) and count == 1 and not real_unreachable
    print('\n' + ('HISTORY IS A SINGLE CLEAN COMMIT' if ok else 'REVIEW NEEDED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
