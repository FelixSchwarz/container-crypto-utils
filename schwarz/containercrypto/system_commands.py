
import re
import subprocess
import sys

from .user_feedback import print_error

__all__ = [
    'find_luks_path_for_mount_dir',
    'run_cmd',
]

def find_luks_path_for_mount_dir(mount_dir):
    mount_cmd = ['mount']
    mount_pattern = r'^(/dev/mapper/luks\-.+?)\s+on\s+%s\s+type' % re.escape(mount_dir)
    luks_path = run_cmd(mount_cmd, regex=re.compile(mount_pattern.encode('utf8'), re.MULTILINE))
    return luks_path

def run_cmd(cmd, *, regex, expected=None):
    if expected is None:
        expected = (0, )
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.returncode
    if exit_code not in expected:
        print_error('command failed: "%s" (exit code %d)' % (' '.join(cmd), exit_code))
        if stdout:
            print_error(stdout)
        if stderr:
            print_error(stderr)
        sys.exit(exit_code)

    match = regex.search(stdout)
    if match is None:
        if regex is None:
            return None
        print_error(stdout)
        print_error(stderr)
    target_location = match.group(1).decode('ascii')
    return target_location

