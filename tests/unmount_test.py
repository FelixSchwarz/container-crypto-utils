
from pathlib import Path
import textwrap

from ddt import data as ddt_data, ddt as DataDrivenTestCase
from pythonic_testcase import *

from schwarz.containercrypto.system_commands import unmount


@DataDrivenTestCase
class UnmountTest(PythonicTestCase):
    @ddt_data(True, False)
    def test_can_run_unmount(self, use_path):
        luks_dir = '/dev/mapper/luks-ac892918-d26d-4bf7-a03c-78af9f70b6f4'
        luks_path = Path(luks_dir) if use_path else luks_dir
        mount_output = 'Unmounted /dev/dm-6.'
        assert_equals('/dev/dm-6', _unmount(luks_path, mount_output))


def _unmount(luks_path, mount_output):
    if isinstance(mount_output, bytes):
        output_bytes = mount_output
    else:
        mount_output = textwrap.dedent(mount_output).strip()
        output_bytes = mount_output.encode('ASCII')
    return unmount(luks_path, _cmd_output=output_bytes)

