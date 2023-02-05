
from pathlib import Path
import re
import subprocess
import sys

from .user_feedback import print_error

__all__ = [
    'delete_loop_device',
    'find_luks_path_for_mount_dir',
    'lock_loop_device',
    'mount',
    'run_cmd',
    'unmount',
]

def find_luks_path_for_mount_dir(mount_dir, *, _cmd_output:bytes=None, verbose=False):
    mount_cmd = ['/usr/bin/mount']
    if _cmd_output is None:
        stdout, stderr = _run_cmd(mount_cmd)
    else:
        assert isinstance(_cmd_output, bytes)
        stdout = _cmd_output
        stderr = None
    dir_str = Path(mount_dir).absolute().as_posix()
    mount_pattern = r'^(/dev/mapper/luks\-.+?)\s+on\s+%s\s+type' % re.escape(dir_str)
    mount_regex = re.compile(mount_pattern.encode('utf8'), re.MULTILINE)
    luks_path = extract_pattern_from_output(stdout, regex=mount_regex, stderr=stderr, print_errors=verbose)
    return luks_path


def mount(dev_dm, *, _cmd_output:bytes=None, verbose=False):
    dev_str = Path(dev_dm).absolute().as_posix()
    mount_cmd = ['/usr/bin/udisksctl', 'mount', '--block-device='+dev_str, '--no-user-interaction']
    #   b'Mounted /dev/… at /run/media/….\n'
    if _cmd_output is None:
        # exit code 1: "... already mounted at ..."
        stdout, stderr = _run_cmd(mount_cmd, expected=(0, 1))
    else:
        assert isinstance(_cmd_output, bytes)
        stdout = _cmd_output
        stderr = None
    udisksctl_at = re.compile(br" at `?(\S+?)'?\.?$")
    mount_path = extract_pattern_from_output(stdout, regex=udisksctl_at, stderr=stderr)
    return mount_path


def unmount(luks_path, *, _cmd_output:bytes=None):
    path_str = Path(luks_path).absolute().as_posix()
    unmount_cmd = ['/usr/bin/udisksctl', 'unmount', '--block-device='+path_str, '--no-user-interaction']
    if _cmd_output is None:
        stdout, stderr = _run_cmd(unmount_cmd)
    else:
        assert isinstance(_cmd_output, bytes)
        stdout = _cmd_output
        stderr = None
    unmount_pattern = r'^Unmounted (/dev/.+)\.'
    unmount_regex = re.compile(unmount_pattern.encode('utf8'))
    luks_dev = extract_pattern_from_output(stdout, regex=unmount_regex, stderr=stderr)
    return luks_dev


def lock_loop_device(loop_path, *, _cmd_output:bytes=None):
    dev_loop = Path(loop_path).absolute().as_posix()
    lock_cmd = ['/usr/bin/udisksctl', 'lock', '--block-device='+dev_loop, '--no-user-interaction']
    if _cmd_output is None:
        stdout, stderr = _run_cmd(lock_cmd)
    else:
        assert isinstance(_cmd_output, bytes)
        stdout = _cmd_output
        stderr = None
    lock_pattern = r'^Locked (/dev/.+)\.'
    lock_regex = re.compile(lock_pattern.encode('utf8'))
    locked_dev = extract_pattern_from_output(stdout, regex=lock_regex, stderr=stderr)
    assert locked_dev is not None


def delete_loop_device(loop_path):
    dev_loop = Path(loop_path).absolute().as_posix()
    lock_cmd = ['/usr/bin/udisksctl', 'loop-delete', '--block-device='+dev_loop, '--no-user-interaction']
    stdout, stderr = _run_cmd(lock_cmd)


def _run_cmd(cmd, *, expected=None):
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
    return stdout, stderr

def extract_pattern_from_output(stdout, *, regex, stderr=None, print_errors=False):
    match = regex.search(stdout)
    if match is None:
        if print_errors:
            print_error(stdout)
            if stderr:
                print_error(stderr)
        return None
    target_location = match.group(1).decode('ascii')
    return target_location

def run_cmd(cmd, *, regex, expected=None) -> str:
    stdout, stderr = _run_cmd(cmd, expected=expected)
    target_location = extract_pattern_from_output(stdout, regex=regex, stderr=stderr)
    return target_location

