#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""crypted-container-ctl

This script can "unlock" an encrypted container file and mount it with
minimal privileges. The "lock" function removes the mount and locks the
container again.

Usage:
  crypted-container-ctl unlock <container_file>
  crypted-container-ctl lock <mount_dir>

Options:
  -h --help     Show this screen.
"""

import os
from pathlib import Path
import re
import sys


from .user_feedback import print_error
from .system_commands import find_luks_path_for_mount_dir, run_cmd

try:
    from docopt import docopt
except ImportError:
    print_error('missing dependency "docopt"')
    sys.exit(5)


__all__ = []

def main(argv=sys.argv):
    arguments = docopt(__doc__, argv=argv[1:])
    subcommands = ('lock', 'unlock')
    command_str = next(cmd for cmd in subcommands if arguments[cmd])

    if command_str == 'unlock':
        cache_file = Path(arguments['<container_file>'])
        ensure_path_exists(cache_file, expect_file=True, name='Encrypted container')
        mount_path = unlock(cache_file)
        if mount_path:
            print(mount_path)
    else:
        cache_dir = Path(arguments['<mount_dir>'])
        ensure_path_exists(cache_dir, expect_dir=True, name='Mount directory')
        tear_down_volume(cache_dir)


def ensure_path_exists(path, *, name, expect_file=False, expect_dir=False):
    if not path.exists():
        print_error('%s does not exist: "%s"' % (name, path))
    elif expect_file and not path.is_file():
        print_error('%s is not a file: "%s"' % (name, path))
    elif expect_dir and not path.is_dir():
        print_error('%s is not a directory: "%s"' % (name, path))
    else:
        return
    sys.exit(5)


# "…(\S+?)\.?" so we can match
#   Error unlocking /dev/loop0: …: Device … is already unlocked as /dev/dm-4
udisksctl_as = re.compile(b' as (\S+?)\.?$')

def _run_cmd(cmd, regex=None, expected=None):
    return run_cmd(cmd, regex=(regex or udisksctl_as), expected=expected)


def unlock(cache_volume_img):
    if not cache_volume_img.exists() or not cache_volume_img.is_file():
        print_error('"%s" does not exist or is not a file' % cache_volume_img)
        return

    disk_id = get_disk_id()

    loop_setup_cmd = ['udisksctl', 'loop-setup', '--file=%s' % cache_volume_img, '--no-user-interaction']
    dev_loop = run_cmd(loop_setup_cmd, regex=udisksctl_as)
   
    path_keyfile = Path('~/.config/borg/borg.cache-%s.key' % (disk_id, )).expanduser()
    if not path_keyfile.exists():
        sys.stderr.write('borg key for disk %s does not exist.\n' % disk_id)
        sys.exit(11)
    unlock_cmd = ['udisksctl', 'unlock', '--block-device='+dev_loop, '--key-file', path_keyfile, '--no-user-interaction']
    dev_dm = run_cmd(unlock_cmd, expected=(0, 1), regex=udisksctl_as)

    mount_cmd = ['udisksctl', 'mount', '--block-device='+dev_dm, '--no-user-interaction']
    udisksctl_at = re.compile(b' at (\S+?)\.?$')
    #   b'Mounted /dev/… at /run/media/….\n'
    mount_path = run_cmd(mount_cmd, regex=udisksctl_at)
    return mount_path


def tear_down_volume(cache_dir):
    luks_path = find_luks_path_for_mount_dir(cache_dir)
    if luks_path is None:
        print_error('no mount found for cache dir "%s"' % cache_dir)
        return

    info_cmd = ['udisksctl', 'info', '--block-device='+luks_path]
    info_regex = re.compile(b"CryptoBackingDevice:\s+'/org/freedesktop/UDisks2/block_devices/(.+?)'")
    loop_name = run_cmd(info_cmd, regex=info_regex)
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


if __name__ == '__main__':
    main()

