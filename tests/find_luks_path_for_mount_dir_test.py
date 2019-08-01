
import textwrap

from pythonic_testcase import *

from schwarz.containercrypto.system_commands import find_luks_path_for_mount_dir


class FindLUKSPathForMountDirTest(PythonicTestCase):
    def test_can_find_luks_path(self):
        mount_dir = '/run/media/user/9f4da36d-beab-4318-b849-24d6d5720496'
        luks_path = '/dev/mapper/luks-ac892918-d26d-4bf7-a03c-78af9f70b6f4'
        mount_output = f'''
            sysfs on /sys type sysfs (rw,nosuid,nodev,noexec,relatime,seclabel)
            proc on /proc type proc (rw,nosuid,nodev,noexec,relatime)
            devtmpfs on /dev type devtmpfs (rw,nosuid,seclabel,size=16424996k,nr_inodes=4106249,mode=755)
            securityfs on /sys/kernel/security type securityfs (rw,nosuid,nodev,noexec,relatime)
            tmpfs on /dev/shm type tmpfs (rw,nosuid,nodev,seclabel)
            efivarfs on /sys/firmware/efi/efivars type efivarfs (rw,nosuid,nodev,noexec,relatime)
            bpf on /sys/fs/bpf type bpf (rw,nosuid,nodev,noexec,relatime,mode=700)
            cgroup on /sys/fs/cgroup/devices type cgroup (rw,nosuid,nodev,noexec,relatime,seclabel,devices)
            /dev/mapper/luks-1cc49eaa-1afe-4a3b-ba9c-f5114bce074a on / type ext4 (rw,relatime,seclabel)
            selinuxfs on /sys/fs/selinux type selinuxfs (rw,relatime)
            mqueue on /dev/mqueue type mqueue (rw,relatime,seclabel)
            hugetlbfs on /dev/hugepages type hugetlbfs (rw,relatime,seclabel,pagesize=2M)
            systemd-1 on /proc/sys/fs/binfmt_misc type autofs (rw,relatime,fd=38,pgrp=1,timeout=0,minproto=5,maxproto=5,direct,pipe_ino=32203)
            debugfs on /sys/kernel/debug type debugfs (rw,relatime,seclabel)
            tmpfs on /tmp type tmpfs (rw,nosuid,nodev,seclabel)
            /dev/sda1 on /boot type ext4 (rw,relatime,seclabel)
            /dev/sda3 on /boot/efi type vfat (rw,relatime,fmask=0077,dmask=0077,codepage=437,iocharset=ascii,shortname=winnt,errors=remount-ro)
            sunrpc on /var/lib/nfs/rpc_pipefs type rpc_pipefs (rw,relatime)
            tmpfs on /run/user/1234 type tmpfs (rw,nosuid,nodev,relatime,seclabel,size=3295516k,mode=700,uid=1234,gid=1234)
            gvfsd-fuse on /run/user/1234/gvfs type fuse.gvfsd-fuse (rw,nosuid,nodev,relatime,user_id=1234,group_id=1234)
            fusectl on /sys/fs/fuse/connections type fusectl (rw,relatime)
            {luks_path} on {mount_dir} type ext4 (rw,nosuid,nodev,relatime,seclabel,uhelper=udisks2)
            /dev/fuse on /run/user/1234/doc type fuse (rw,nosuid,nodev,relatime,user_id=1234,group_id=1234)
        '''
        assert_equals(luks_path, _find_luks_path(mount_dir, mount_output))


def _find_luks_path(mount_dir, mount_output):
    if isinstance(mount_output, bytes):
        output_bytes = mount_output
    else:
        mount_output = textwrap.dedent(mount_output).strip()
        output_bytes = mount_output.encode('ASCII')
    return find_luks_path_for_mount_dir(mount_dir, _cmd_output=output_bytes)

