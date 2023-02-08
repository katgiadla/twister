import os
import subprocess
from unittest import mock

import pytest

from twister2.exceptions import TwisterBuildException, TwisterMemoryOverflowException


@pytest.fixture
def patched_cmake():
    with mock.patch('twister2.builder.cmake_builder.CMakeBuilder._get_cmake', return_value='cmake') as cmake:
        yield cmake


@mock.patch('twister2.builder.cmake_builder.CMakeBuilder._run_command_in_subprocess', return_value=None)
def test_if_run_cmake_stage_calls_run_command_in_subprocess_with_proper_arguments(
        patched_run_command_in_subprocess, patched_cmake, cmake_builder, build_config
):
    expected_command = [
        'cmake', f'-S{build_config.source_dir}', f'-B{build_config.build_dir}', '-GNinja',
        f'-DBOARD={build_config.platform_name}', '-DCONF_FILE=prj_single.conf',
    ]

    cmake_builder.run_cmake_stage(cmake_helper=False)
    patched_run_command_in_subprocess.assert_called_once_with(expected_command, action='CMake')


@mock.patch('twister2.builder.cmake_builder.CMakeBuilder._run_command_in_subprocess', return_value=None)
def test_if_run_cmake_stage_calls_run_command_in_subprocess_with_proper_arguments_for_cmake_helper_flag_set(
        patched_run_command_in_subprocess, patched_cmake, cmake_builder, build_config
):
    expected_command = [
        'cmake', f'-S{build_config.source_dir}', f'-B{build_config.build_dir}', '-GNinja',
        f'-DBOARD={build_config.platform_name}', '-DCONF_FILE=prj_single.conf',
        '-DMODULES=dts,kconfig', '-Pzephyr/cmake/package_helper.cmake'
    ]

    cmake_builder.run_cmake_stage(cmake_helper=True)
    patched_run_command_in_subprocess.assert_called_once_with(expected_command, action='CMake')


@mock.patch('twister2.builder.cmake_builder.CMakeBuilder._run_command_in_subprocess', return_value=None)
def test_if_run_build_generator_calls_run_command_with_proper_arguments(
        patched_run_command_in_subprocess, patched_cmake, cmake_builder, build_config
):
    expected_command = ['cmake', '--build', build_config.build_dir]

    cmake_builder.run_build_generator()
    patched_run_command_in_subprocess.assert_called_once_with(expected_command, action='building')


@mock.patch('shutil.which', return_value='cmake')
def test_if_get_cmake_returns_path_to_installed_cmake(patched_which, cmake_builder):
    assert cmake_builder._get_cmake() == 'cmake'


@mock.patch('shutil.which', return_value=None)
def test_if_get_cmake_raises_exception_when_cmake_is_not_installed(patched_which, cmake_builder):
    with pytest.raises(TwisterBuildException, match='cmake not found'):
        cmake_builder._get_cmake()


@mock.patch('subprocess.run', side_effect=subprocess.CalledProcessError(returncode=1, cmd='error message'))
def test_if_run_command_in_subprocess_handles_subprocess_process_error(patched_run, cmake_builder):
    with pytest.raises(TwisterBuildException, match='building error'):
        cmake_builder._run_command_in_subprocess(['dummie'], 'building')
    assert os.path.exists(cmake_builder.build_log_file.filename)
    with open(cmake_builder.build_log_file.filename, 'r') as file:
        assert file.readline() == "error message"


@mock.patch('subprocess.run')
def test_if_run_command_in_subprocess_handles_subprocess_return_code_zero_without_errors(
        patched_run, cmake_builder
):
    patched_run.return_value = mock.MagicMock(returncode=0, stdout="built successful".encode())
    cmake_builder._run_command_in_subprocess(['dummie'], 'building')
    assert os.path.exists(cmake_builder.build_log_file.filename)
    with open(cmake_builder.build_log_file.filename, 'r') as file:
        assert file.readline() == "built successful"


@mock.patch('subprocess.run')
def test_if_run_command_in_subprocess_handles_subprocess_non_zero_return_code(patched_run, cmake_builder):
    patched_run.return_value = mock.MagicMock(returncode=1, stdout='fake build output'.encode())
    msg = (
        f'Failed building {cmake_builder.build_config.source_dir} '
        f'for platform: {cmake_builder.build_config.platform_name}'
    )
    with pytest.raises(TwisterBuildException, match=msg):
        cmake_builder._run_command_in_subprocess(['dummie'], 'building')
    assert os.path.exists(cmake_builder.build_log_file.filename)
    with open(cmake_builder.build_log_file.filename, 'r') as file:
        assert file.readline() == "fake build output"


def test_if_overflow_exception_is_raised_when_memory_overflow_occurs(cmake_builder):
    build_output = 'region `FLASH\' overflowed by'.encode()
    exception_msg = 'Memory overflow during building source for platform: native_posix'
    with pytest.raises(TwisterMemoryOverflowException, match=exception_msg):
        cmake_builder._check_memory_overflow(cmake_builder.build_config, build_output)


def test_if_overflow_exception_is_raised_when_imgtool_memory_overflow_occurs(cmake_builder):
    build_output = 'Error: Image size (32) + trailer (2) exceeds requested size'.encode()
    exception_msg = 'Imgtool memory overflow during building source for platform: native_posix'
    with pytest.raises(TwisterMemoryOverflowException, match=exception_msg):
        cmake_builder._check_memory_overflow(cmake_builder.build_config, build_output)
