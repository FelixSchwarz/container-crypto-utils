#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""crypted-container-ctl

This script can "unlock" an encrypted container file and mount it with
minimal privileges. The "lock" function removes the mount and locks the
container again.

Usage:
  crypted-container-ctl [--verbose] unlock <container_file>
  crypted-container-ctl [--verbose] lock <mount_dir>
  crypted-container-ctl --version

Options:
  -h --help     Show this screen.
"""

try:
    from importlib.metadata import version
except ImportError:
    # Python <= 3.7
    from importlib_metadata import version
import os
from pathlib import Path
import re
import sys

from .user_feedback import print_error
from .system_commands import *

try:
    from docopt import docopt
except ImportError:
    print_error('missing dependency "docopt"')
    sys.exit(5)


__all__ = []

def main(argv=sys.argv):
    arguments = docopt(__doc__, argv=argv[1:])
    verbose = arguments['--verbose']
    show_version = arguments['--version']
    if show_version:
        app_version = version('ContainerCryptoUtils')
        print(app_version)
        return
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
        tear_down_volume(cache_dir, verbose=verbose)


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
    path_keyfile = find_keyfile(disk_id)
    if not path_keyfile:
        sys.stderr.write('borg key for disk %s does not exist.\n' % disk_id)
        sys.exit(11)

    loop_setup_cmd = ['/usr/bin/udisksctl', 'loop-setup', '--file=%s' % cache_volume_img, '--no-user-interaction']
    dev_loop = run_cmd(loop_setup_cmd, regex=udisksctl_as)

    unlock_cmd = ['/usr/bin/udisksctl', 'unlock', '--block-device='+dev_loop, '--key-file', path_keyfile, '--no-user-interaction']
    dev_dm = run_cmd(unlock_cmd, expected=(0, 1), regex=udisksctl_as)
    mount_path = mount(dev_dm)
    return mount_path


def find_keyfile(disk_id):
    disk_key = f'.config/borg/borg.cache-{disk_id}.key'

    home_path = Path('~').expanduser()
    key_path = home_path / disk_key
    if key_path.exists():
        return key_path

    os_username = os.getenv('SUDO_USER')
    if os_username:
        os_username_home = Path(f'~{os_username}').expanduser()
        key_path = os_username_home / disk_key
        if key_path.exists():
            return key_path
    return None


def tear_down_volume(cache_dir, *, verbose=False):
    luks_path = find_luks_path_for_mount_dir(cache_dir, verbose=verbose)
    if luks_path is None:
        print_error('no mount found for cache dir "%s"' % cache_dir)
        return

    info_cmd = ['/usr/bin/udisksctl', 'info', '--block-device='+luks_path]
    info_regex = re.compile(b"CryptoBackingDevice:\s+'/org/freedesktop/UDisks2/block_devices/(.+?)'")
    loop_name = run_cmd(info_cmd, regex=info_regex)
    dev_loop = '/dev/' + loop_name

    unmount(luks_path)
    lock_loop_device(dev_loop)
    delete_loop_device(dev_loop)


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

