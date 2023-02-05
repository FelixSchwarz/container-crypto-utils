#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""crypted-container-ctl

This script can "unlock" an encrypted container file and mount it with
minimal privileges. The "lock" function removes the mount and locks the
container again.

Usage:
  crypted-container-ctl [--verbose] unlock <container_file>
  crypted-container-ctl [--verbose] lock <mount_dir>
  crypted-container-ctl [--verbose] init <container_file>
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
from pwd import getpwnam
import re
import shlex
import sys

from .user_feedback import print_error
from .system_commands import _run_cmd
from .system_commands import *

try:
    from docopt import docopt
except ImportError:
    print_error('missing dependency "docopt"')
    sys.exit(5)


__all__ = []

KEY_SIZE = 512

def main(argv=sys.argv):
    arguments = docopt(__doc__, argv=argv[1:])
    verbose = arguments['--verbose']
    show_version = arguments['--version']
    if show_version:
        app_version = version('ContainerCryptoUtils')
        print(app_version)
        return
    subcommands = ('lock', 'unlock', 'init')
    command_str = next(cmd for cmd in subcommands if arguments[cmd])

    if command_str == 'unlock':
        cache_file = Path(arguments['<container_file>'])
        ensure_path_exists(cache_file, expect_file=True, name='Encrypted container')
        dev_dm = unlock(cache_file)
        mount_path = mount(dev_dm)
        if mount_path:
            print(mount_path)
    elif command_str == 'lock':
        cache_dir = Path(arguments['<mount_dir>'])
        ensure_path_exists(cache_dir, expect_dir=True, name='Mount directory')
        tear_down_volume(cache_dir, verbose=verbose)
    elif command_str == 'init':
        is_root = (os.getuid() == 0)
        if not is_root:
            sys.stderr.write('This command needs root-privileges. Please re-run this again using "sudo":\n')
            sys.stderr.write(f'$ sudo {shlex.join(argv)}\n')
            sys.exit(9)

        path_container = Path(arguments['<container_file>'])
        init_container(path_container, verbose=verbose)
    else:
        raise ValueError(f'unexpected subcommand "{command_str}"')


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


def unlock(cache_volume_img) -> str:
    if not cache_volume_img.exists() or not cache_volume_img.is_file():
        print_error('"%s" does not exist or is not a file' % cache_volume_img)
        return

    disk_id = get_disk_id(cache_volume_img)
    path_keyfile = find_keyfile(disk_id)
    if not path_keyfile:
        sys.stderr.write('borg key for disk %s does not exist.\n' % disk_id)
        sys.exit(11)

    loop_setup_cmd = ['/usr/bin/udisksctl', 'loop-setup', '--file=%s' % cache_volume_img, '--no-user-interaction']
    dev_loop = run_cmd(loop_setup_cmd, regex=udisksctl_as)

    unlock_cmd = ['/usr/bin/udisksctl', 'unlock', '--block-device='+dev_loop, '--key-file', path_keyfile, '--no-user-interaction']
    dev_dm = run_cmd(unlock_cmd, expected=(0, 1), regex=udisksctl_as)
    return dev_dm


def init_container(path_container, *, verbose=False):
    if path_container.exists():
        print_error(f'container path already exists: "{path_container}"')
        sys.exit(10)

    disk_id = get_disk_id(path_container)
    path_keyfile = find_keyfile(disk_id)
    if not path_keyfile:
        path_keyfile = expected_key_path(disk_id, prefer_sudo=True)
        sys.stderr.write('borg key for disk %s does not exist.\n' % disk_id)
        sys.stderr.write(f'  create key: dd if=/dev/urandom of="{str(path_keyfile)}" bs=1 count={KEY_SIZE}\n')
        sys.exit(11)

    size_gb = 20
    size_mb = size_gb * 1024
    cmd_dd_sparse = ['/bin/dd', 'if=/dev/zero', 'of=%s' % path_container, 'bs=1', 'count=0', 'seek=%dM' % size_mb]
    _run_cmd(cmd_dd_sparse)
    os.chmod(path_container, 0o600)

    username_sudo = os.getenv('SUDO_USER')
    if username_sudo:
        pwd_db_data = getpwnam(username_sudo)
        sudo_uid = pwd_db_data.pw_uid
        sudo_gid = pwd_db_data.pw_gid
        os.chown(path_container, sudo_uid, sudo_gid)

    if verbose:
        print(f'Initializing LUKS container at {str(path_container)}. This can take a few seconds...')
    cmd_luks_format = ['/usr/sbin/cryptsetup', '--batch-mode', '--cipher=aes-xts-plain64', f'--key-size={KEY_SIZE}', f'--key-file={path_keyfile}', 'luksFormat', str(path_container)]
    _run_cmd(cmd_luks_format)
    dev_dm = unlock(path_container)
    assert dev_dm and Path(dev_dm).is_block_device()

    uid, gid = detect_uid_gid_for_user()
    if verbose:
        print(f'Creating ext4 filesystem inside container with UID={uid}/GID={gid}')
    # unfortunately udisksctl does not allow to set the owner of a newly
    # created block device (in loop-setup/unlock) so we need root access to
    # run mkfs.
    cmd_mkfs = ['/usr/sbin/mkfs.ext4', '-E', f'root_owner={uid}:{gid}', dev_dm]
    _run_cmd(cmd_mkfs)

    dev_loop = get_dev_loop_for_luks_path(dev_dm)
    lock_loop_device(dev_loop)
    delete_loop_device(dev_loop)


def detect_uid_gid_for_user():
    os_username = os.getenv('SUDO_USER')
    if not os_username:
        uid = os.getuid()
        gid = os.getgid()
        return (uid, gid)

    pwd_db_data = getpwnam(os_username)
    return (pwd_db_data.pw_uid, pwd_db_data.pw_gid)


def find_keyfile(disk_id):
    key_path = _key_path(disk_id)
    if key_path.exists():
        return key_path

    os_username = os.getenv('SUDO_USER')
    if os_username:
        key_path = _key_path(disk_id, username=os_username)
        if key_path.exists():
            return key_path
    return None


def expected_key_path(disk_id: str, prefer_sudo):
    sudo_username = os.getenv('SUDO_USER')
    # username=None means "current" user for "_key_path()"
    username = sudo_username if prefer_sudo else None
    return _key_path(disk_id, username=username)

def _key_path(disk_id: str, *, username=None):
    disk_key = f'.config/borg/borg.cache-{disk_id}.key'
    home_path = Path('~' + (username or '')).expanduser()
    return home_path / disk_key


def tear_down_volume(cache_dir, *, verbose=False):
    luks_path = find_luks_path_for_mount_dir(cache_dir, verbose=verbose)
    if luks_path is None:
        print_error('no mount found for cache dir "%s"' % cache_dir)
        return

    dev_loop = get_dev_loop_for_luks_path(luks_path)
    unmount(luks_path)
    lock_loop_device(dev_loop)
    delete_loop_device(dev_loop)


def get_dev_loop_for_luks_path(luks_path: str):
    info_cmd = ['udisksctl', 'info', '--block-device='+luks_path]
    info_regex = re.compile(b"CryptoBackingDevice:\s+'/org/freedesktop/UDisks2/block_devices/(.+?)'")
    loop_name = run_cmd(info_cmd, regex=info_regex)
    dev_loop = '/dev/' + loop_name
    return dev_loop


def get_disk_id(img_path=None):
    for path in [Path(os.getcwd()), Path(__file__).parent]:
        disk_id = _disk_id_from_directory(path)
        if disk_id:
            return disk_id

    if img_path:
        path = img_path.absolute().parent
        while str(path) != '/':
            disk_id = _disk_id_from_directory(path)
            if disk_id:
                return disk_id
            path = path.parent
    raise ValueError('no disk ID found')

def _disk_id_from_directory(path):
    extension = '.DISK'
    disk_paths = tuple(path.glob('*' + extension))
    if not disk_paths:
        return None
    disk_file = disk_paths[0].name
    return disk_file[:-len(extension)]


if __name__ == '__main__':
    main()

