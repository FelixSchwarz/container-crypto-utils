#!/usr/bin/env python3

import os
from pathlib import Path
import re
import subprocess
import sys


def main(argv=sys.argv):
    command_str = argv[1]
    assert command_str in ('unlock', 'lock'), command_str

    if command_str == 'unlock':
        cache_file = argv[2]
        mount_path = unlock(cache_file)
        if mount_path:
            print(mount_path)
    else:
        cache_dir = argv[2]
        tear_down_volume(cache_dir)

def print_error(s):
    if isinstance(s, bytes):
        try:
            s = s.decode('UTF-8')
        except UnicodeDecodeError:
            print('error while decoding %r' % s)
            sys.exit(5)
    sys.stderr.write(s + '\n')

# "…(\S+?)\.?" so we can match
#   Error unlocking /dev/loop0: …: Device … is already unlocked as /dev/dm-4
udisksctl_as = re.compile(b' as (\S+?)\.?$')

def unlock(cache_volume_img):
    p = Path(cache_volume_img)
    if not p.exists() or not p.is_file():
        print_error('"%s" does not exist or is not a file' % cache_volume_img)
        return

    disk_id = get_disk_id()

    loop_setup_cmd = ['udisksctl', 'loop-setup', '--file='+cache_volume_img, '--no-user-interaction']
    dev_loop = _run_cmd(loop_setup_cmd, regex=udisksctl_as)
   
    path_keyfile = Path('~/.config/borg/borg.cache-%s.key' % (disk_id, )).expanduser()
    if not path_keyfile.exists():
        sys.stderr.write('borg key for disk %s does not exist.\n' % disk_id)
        sys.exit(11)
    unlock_cmd = ['udisksctl', 'unlock', '--block-device='+dev_loop, '--key-file', path_keyfile, '--no-user-interaction']
    dev_dm = _run_cmd(unlock_cmd, expected=(0, 1), regex=udisksctl_as)

    mount_cmd = ['udisksctl', 'mount', '--block-device='+dev_dm, '--no-user-interaction']
    udisksctl_at = re.compile(b' at (\S+?)\.?$')
    #   b'Mounted /dev/… at /run/media/….\n'
    mount_path = _run_cmd(mount_cmd, regex=udisksctl_at)
    return mount_path


def tear_down_volume(cache_dir):
    mount_cmd = ['mount']
    
    mount_pattern = r'^(/dev/mapper/luks\-.+?)\s+on\s+%s\s+type' % re.escape(cache_dir)
    luks_path = _run_cmd(mount_cmd, regex=re.compile(mount_pattern.encode('utf8'), re.MULTILINE))
    if luks_path is None:
        print_error('no mount found for cache dir "%s"' % cache_dir)
        return

    info_cmd = ['udisksctl', 'info', '--block-device='+luks_path]
    info_regex = re.compile(b"CryptoBackingDevice:\s+'/org/freedesktop/UDisks2/block_devices/(.+?)'")
    loop_name = _run_cmd(info_cmd, regex=info_regex)
    dev_loop = '/dev/' + loop_name

    unmount_cmd = ['udisksctl', 'unmount', '--block-device='+luks_path, '--no-user-interaction']
    _run_cmd(unmount_cmd)
    lock_cmd = ['udisksctl', 'lock', '--block-device='+dev_loop, '--no-user-interaction']
    _run_cmd(lock_cmd)
    loop_delete_cmd = ['udisksctl', 'loop-delete', '--block-device='+dev_loop, '--no-user-interaction']
    _run_cmd(loop_delete_cmd)


def get_disk_id():
    paths = (
        Path(os.getcwd()),
        Path(__file__).parent,
    )
    extension = '.DISK'
    for path in paths:
        disk_paths = tuple(path.glob('*' + extension))
        if disk_paths:
            disk_file = disk_paths[0].name
            return disk_file[:-len(extension)]
    raise ValueError('no disk ID found')


def _run_cmd(cmd, regex=None, expected=None):
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

    match = (regex or udisksctl_as).search(stdout)
    if match is None:
        if regex is None:
            return None
        print_error(stdout)
        print_error(stderr)
    target_location = match.group(1).decode('ascii')
    return target_location

if __name__ == '__main__':
    main()

