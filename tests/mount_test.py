
from pathlib import Path
import textwrap

from ddt import data as ddt_data, ddt as DataDrivenTestCase
from pythonic_testcase import *

from schwarz.containercrypto.system_commands import mount


@DataDrivenTestCase
class MountTest(PythonicTestCase):
    @ddt_data(True, False)
    def test_can_run_mount(self, use_path):
        dev_str = '/dev/dm-6'
        dev_dm = Path(dev_str) if use_path else dev_str
        mount_dir = '/run/media/fs/c9236e4a-bb6e-4e3f-ad30-b72583484a22'
        mount_output = f'Mounted {dev_str} at {mount_dir}.'
        assert_equals(mount_dir, _mount(dev_dm, mount_output))

    def test_can_handle_already_mounted(self):
        dev_dm = '/dev/dm-6'
        mount_dir = '/run/media/fs/c9236e4a-bb6e-4e3f-ad30-b72583484a22'
        mount_output = (f"Error mounting {dev_dm}: GDBus.Error:org.freedesktop.UDisks2.Error.AlreadyMounted: "
            f"Device {dev_dm} is already mounted at `{mount_dir}'.")
        assert_equals(mount_dir, _mount(dev_dm, mount_output))



def _mount(dev_dm, mount_output):
    if isinstance(mount_output, bytes):
        output_bytes = mount_output
    else:
        mount_output = textwrap.dedent(mount_output).strip()
        output_bytes = mount_output.encode('ASCII')
    return mount(dev_dm, _cmd_output=output_bytes)

