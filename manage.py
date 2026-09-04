"""Portable setup and entry points; run with Python 3.14."""
import argparse
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')


def call(args, cwd=ROOT):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['setup', 'test', 'run'])
    parser.add_argument('module', nargs='?', default='web',
                        choices=['web', 'family-deals', 'movies', 'tickets', 'tickets-demo'])
    parser.add_argument('--browsers', action='store_true', help='Install Chromium for live Movies/Tickets')
    args = parser.parse_args()
    if sys.version_info < (3, 14):
        parser.error('Use Python 3.14 or newer; Python 3.14 is the verified baseline.')
    if args.command == 'setup':
        if not PYTHON.exists():
            venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
        call([PYTHON, '-m', 'pip', 'install', '-r', ROOT / 'requirements.txt'])
        call([PYTHON, '-m', 'pip', 'check'])
        if args.browsers:
            call([PYTHON, '-m', 'playwright', 'install', 'chromium'])
        for module in ['seat-watcher', 'ticket-watcher']:
            folder = ROOT / 'modules' / module
            target = folder / '.env'
            if not target.exists():
                with target.open('x', encoding='utf-8') as stream:
                    stream.write((folder / '.env.example').read_text(encoding='utf-8'))
        print('Setup complete. Configure optional module .env files, then run: python manage.py test')
        return
    if not PYTHON.exists():
        parser.error('Run python manage.py setup first.')
    if args.command == 'test':
        call([PYTHON, 'tools/verify_repo.py'])
        for folder, suite in [('.', 'core'), ('.', 'web'), ('.', 'adapters'),
                              ('modules/family-deals', 'tests'),
                              ('modules/ticket-watcher', 'tests'),
                              ('modules/seat-watcher', 'tests')]:
            call([PYTHON, '-m', 'unittest', 'discover', '-s', suite, '-p', 'test_*.py', '-v'], ROOT / folder)
        return
    entries = {
        'web': ('web', 'server.py', []),
        'family-deals': ('modules/family-deals', 'server.py', []),
        'movies': ('modules/seat-watcher', 'seat_watcher_premium.py', []),
        'tickets': ('modules/ticket-watcher', 'ticketmaster_live_watcher.py', []),
        'tickets-demo': ('modules/ticket-watcher', 'app.py', ['--demo', '--once']),
    }
    folder, script, extra = entries[args.module]
    call([PYTHON, script, *extra], ROOT / folder)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
