import os
from unittest import mock

import pytest

from twister2.device.hardware_adapter import HardwareAdapter
from twister2.device.hardware_map import HardwareMap
from twister2.exceptions import TwisterFlashException
from twister2.log_files.log_file import DeviceLogFile, HandlerLogFile
from twister2.twister_config import TwisterConfig


@pytest.fixture(name='device')
def fixture_adapter(resources) -> HardwareAdapter:
    return HardwareAdapter(
        TwisterConfig(zephyr_base=str(resources)),
        hardware_map=HardwareMap(
            id='test',
            product='product',
            platform='platform',
            runner='runner',
            connected=True
        )
    )


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_1(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == ['west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'runner']


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_2(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'pyocd'
    device.hardware_map.probe_id = 'p_id'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'pyocd', '--', '--board-id', 'p_id'
    ]


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_raise_exception_if_west_is_not_installed(patched_which, device) -> None:
    patched_which.return_value = None
    with pytest.raises(TwisterFlashException, match='west not found'):
        device.generate_command('src')


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_3(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'nrfjprog'
    device.hardware_map.probe_id = 'p_id'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'nrfjprog', '--', '--dev-id', 'p_id'
    ]


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_4(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'openocd'
    device.hardware_map.product = 'STM32 STLink'
    device.hardware_map.probe_id = 'p_id'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'openocd',
        '--', '--cmd-pre-init', 'hla_serial p_id'
    ]


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_5(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'openocd'
    device.hardware_map.product = 'EDBG CMSIS-DAP'
    device.hardware_map.probe_id = 'p_id'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'openocd',
        '--', '--cmd-pre-init', 'cmsis_dap_serial p_id'
    ]


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_6(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'jlink'
    device.hardware_map.probe_id = 'p_id'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'jlink',
        '--tool-opt=-SelectEmuBySN p_id'
    ]


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_7(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'stm32cubeprogrammer'
    device.hardware_map.probe_id = 'p_id'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src', '--runner', 'stm32cubeprogrammer',
        '--tool-opt=sn=p_id'
    ]


@mock.patch('twister2.device.hardware_adapter.shutil.which')
def test_if_get_command_returns_proper_string_8(patched_which, device) -> None:
    patched_which.return_value = 'west'
    device.hardware_map.runner = 'openocd'
    device.hardware_map.product = 'STLINK-V3'
    device.generate_command('src')
    assert isinstance(device.command, list)
    assert device.command == [
        'west', 'flash', '--skip-rebuild', '--build-dir', 'src',
        '--runner', 'openocd', '--', '--cmd-pre-init', 'hla_serial test'
    ]


def test_if_hardware_adapter_raises_exception_empty_command(device) -> None:
    device.command = []
    exception_msg = 'Flash command is empty, please verify if it was generated properly.'
    with pytest.raises(TwisterFlashException, match=exception_msg):
        device.flash_and_run(timeout=0.1)


def test_handler_and_device_log_correct_initialized_on_hardware(device, tmp_path) -> None:
    device.initialize_log_files(tmp_path)
    assert isinstance(device.handler_log_file, HandlerLogFile)
    assert isinstance(device.device_log_file, DeviceLogFile)
    assert device.handler_log_file.filename.endswith('handler.log')  # type: ignore[union-attr]
    assert device.device_log_file.filename.endswith('device.log')  # type: ignore[union-attr]


@mock.patch('twister2.device.hardware_adapter.subprocess.Popen')
def test_device_log_correct_error_handle(patched_popen, device, tmp_path) -> None:
    popen_mock = mock.Mock()
    popen_mock.communicate.return_value = (b'', b'flashing error')
    patched_popen.return_value = popen_mock

    device.initialize_log_files(tmp_path)
    device.command = [
        'west', 'flash', '--skip-rebuild', '--build-dir', str(tmp_path),
        '--runner', 'nrfjprog', '--', '--dev-id', 'p_id'
    ]
    with pytest.raises(expected_exception=TwisterFlashException, match='Could not flash device test'):
        device.flash_and_run()
    assert os.path.isfile(device.device_log_file.filename)
    with open(device.device_log_file.filename, 'r') as file:
        assert 'flashing error' in file.readlines()
