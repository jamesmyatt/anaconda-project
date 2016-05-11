# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2016, Continuum Analytics, Inc. All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# ----------------------------------------------------------------------------
"""The ``main`` function chooses and runs a subcommand."""
from __future__ import absolute_import, print_function

import os
import sys
from argparse import ArgumentParser, REMAINDER

from anaconda_project.commands.prepare_with_mode import UI_MODE_TEXT_ASSUME_YES_DEVELOPMENT, _all_ui_modes
from anaconda_project.version import version
from anaconda_project.project import ALL_COMMAND_TYPES
from anaconda_project.plugins.registry import PluginRegistry
from anaconda_project.plugins.requirements.download import _hash_algorithms
import anaconda_project.commands.init as init
import anaconda_project.commands.launch as launch
import anaconda_project.commands.prepare as prepare
import anaconda_project.commands.clean as clean
import anaconda_project.commands.activate as activate
import anaconda_project.commands.variable_commands as variable_commands
import anaconda_project.commands.download_commands as download_commands
import anaconda_project.commands.service_commands as service_commands
import anaconda_project.commands.environment_commands as environment_commands
import anaconda_project.commands.command_commands as command_commands


def _parse_args_and_run_subcommand(argv):
    parser = ArgumentParser(prog="anaconda-project", description="Actions on Anaconda projects.")

    # future: make setup.py store our version in a version.py then use that here
    # parser.add_argument('-v', '--version', action='version', version='0.1')

    subparsers = parser.add_subparsers(help="Sub-commands")

    parser.add_argument('-v', '--version', action='version', version=version)

    def add_project_arg(preset):
        preset.add_argument('--project',
                            metavar='PROJECT_DIR',
                            default='.',
                            help="Project directory containing project.yml (defaults to current directory)")

    def add_environment_arg(preset):
        preset.add_argument('--environment',
                            metavar='ENVIRONMENT_NAME',
                            default=None,
                            action='store',
                            help="An environment name from project.yml")

    def add_prepare_args(preset):
        add_project_arg(preset)
        add_environment_arg(preset)
        preset.add_argument('--mode',
                            metavar='MODE',
                            default=UI_MODE_TEXT_ASSUME_YES_DEVELOPMENT,
                            choices=_all_ui_modes,
                            action='store',
                            help="One of " + ", ".join(_all_ui_modes))

    def add_environment_name_arg(preset):
        preset.add_argument('-n',
                            '--name',
                            metavar='ENVIRONMENT_NAME',
                            action='store',
                            help="Name of the environment under PROJECT_DIR/envs")

    preset = subparsers.add_parser('init', help="Initialize a directory with default project configuration")
    add_project_arg(preset)
    preset.set_defaults(main=init.main)

    preset = subparsers.add_parser('launch', help="Run the project, setting up requirements first")
    add_prepare_args(preset)
    preset.add_argument('--command',
                        metavar="COMMAND_NAME",
                        default=None,
                        action="store",
                        help="A command name from project.yml")
    preset.add_argument('extra_args_for_command', metavar='EXTRA_ARGS_FOR_COMMAND', default=None, nargs=REMAINDER)
    preset.set_defaults(main=launch.main)

    preset = subparsers.add_parser('prepare', help="Set up the project requirements, but does not run the project")
    add_prepare_args(preset)
    preset.set_defaults(main=prepare.main)

    preset = subparsers.add_parser('clean',
                                   help="Removes generated state (stops services, deletes environment files, etc)")
    add_project_arg(preset)
    preset.set_defaults(main=clean.main)

    preset = subparsers.add_parser('activate',
                                   help="Set up the project and output shell export commands reflecting the setup")
    add_prepare_args(preset)
    preset.set_defaults(main=activate.main)

    preset = subparsers.add_parser('add-variable',
                                   help="Add an environment variable and add it to the project if not present")
    preset.add_argument('vars_to_add', metavar='VARS_TO_ADD', default=None, nargs=REMAINDER)
    add_project_arg(preset)
    preset.set_defaults(main=variable_commands.main, action="add")

    preset = subparsers.add_parser('remove-variable',
                                   help="Remove an environment variable and remove it from the project")
    add_project_arg(preset)
    preset.add_argument('vars_to_remove', metavar='VARS_TO_REMOVE', default=None, nargs=REMAINDER)
    preset.set_defaults(main=variable_commands.main, action="remove")

    preset = subparsers.add_parser('list-variables', help="List all variables on the project")
    add_project_arg(preset)
    preset.set_defaults(main=variable_commands.main_list)

    preset = subparsers.add_parser('add-download', help="Add a URL to be downloaded before running commands")
    add_project_arg(preset)
    preset.add_argument('filename_variable', metavar='ENV_VAR_FOR_FILENAME', default=None)
    preset.add_argument('download_url', metavar='DOWNLOAD_URL', default=None)
    preset.add_argument('--filename', help="The name to give the file/folder after downloading it", default=None)
    preset.add_argument('--hash-algorithm',
                        help="Defines which hash algorithm to use",
                        default=None,
                        choices=_hash_algorithms)
    preset.add_argument('--hash-value', help="The expected checksum hash of the downloaded file", default=None)
    preset.set_defaults(main=download_commands.main_add)

    preset = subparsers.add_parser('remove-download', help="Remove a download from the project and from the filesystem")
    add_project_arg(preset)
    preset.add_argument('filename_variable', metavar='ENV_VAR_FOR_FILENAME', default=None)
    preset.set_defaults(main=download_commands.main_remove)

    preset = subparsers.add_parser('list-downloads', help="List all downloads on the project")
    add_project_arg(preset)
    preset.set_defaults(main=download_commands.main_list)

    service_types = PluginRegistry().list_service_types()
    service_choices = list(map(lambda s: s.name, service_types))

    def add_service_variable_name(preset):
        preset.add_argument('--variable', metavar='ENV_VAR_FOR_SERVICE_ADDRESS', default=None)

    preset = subparsers.add_parser('add-service', help="Add a service to be available before running commands")
    add_project_arg(preset)
    add_service_variable_name(preset)
    preset.add_argument('service_type', metavar='SERVICE_TYPE', default=None, choices=service_choices)
    preset.set_defaults(main=service_commands.main_add)

    preset = subparsers.add_parser('remove-service', help="Remove a service from the project")
    add_project_arg(preset)
    add_service_variable_name(preset)
    preset.set_defaults(main=service_commands.main_remove)

    preset = subparsers.add_parser('list-services', help="List services present in the project")
    add_project_arg(preset)
    preset.set_defaults(main=service_commands.main_list)

    def add_package_args(preset):
        preset.add_argument('-c',
                            '--channel',
                            metavar='CHANNEL',
                            action='append',
                            help='Channel to search for packages')
        preset.add_argument('packages', metavar='PACKAGES', default=None, nargs=REMAINDER)

    preset = subparsers.add_parser('add-environment', help="Add a new environment to the project")
    add_project_arg(preset)
    add_package_args(preset)
    add_environment_name_arg(preset)
    preset.set_defaults(main=environment_commands.main_add)

    preset = subparsers.add_parser('remove-environment', help="Remove an environment from the project")
    add_project_arg(preset)
    add_environment_name_arg(preset)
    preset.set_defaults(main=environment_commands.main_remove)

    preset = subparsers.add_parser('list-environments', help="List all environments on the project")
    add_project_arg(preset)
    preset.set_defaults(main=environment_commands.main_list_environments)

    preset = subparsers.add_parser('add-dependencies', help="Add packages to one or all project environments")
    add_project_arg(preset)
    add_environment_arg(preset)
    add_package_args(preset)
    preset.set_defaults(main=environment_commands.main_add_dependencies)

    preset = subparsers.add_parser('remove-dependencies', help="Remove packages from one or all project environments")
    add_project_arg(preset)
    add_environment_arg(preset)
    preset.add_argument('packages', metavar='PACKAGE_NAME', default=None, nargs='+')
    preset.set_defaults(main=environment_commands.main_remove_dependencies)

    preset = subparsers.add_parser('list-dependencies', help="List dependencies for an environment on the project")
    add_project_arg(preset)
    add_environment_arg(preset)
    preset.set_defaults(main=environment_commands.main_list_dependencies)

    def add_command_name_arg(preset):
        preset.add_argument('name', metavar="NAME", help="Command name used to invoke it")

    preset = subparsers.add_parser('add-command', help="Add a new command to the project")
    add_project_arg(preset)
    command_choices = list(ALL_COMMAND_TYPES) + ['ask']
    command_choices.remove("conda_app_entry")  # conda_app_entry is sort of silly and may go away
    preset.add_argument('--type', action="store", choices=command_choices, help="Command type to add")
    add_command_name_arg(preset)
    preset.add_argument('command', metavar="COMMAND", help="Command line or app filename to add")
    preset.set_defaults(main=command_commands.main)

    preset = subparsers.add_parser('remove-command', help="Remove a command from the project")
    add_project_arg(preset)
    add_command_name_arg(preset)
    preset.set_defaults(main=command_commands.main_remove)

    preset = subparsers.add_parser('list-commands', help="List the commands on the project")
    add_project_arg(preset)
    preset.set_defaults(main=command_commands.main_list)

    # argparse doesn't do this for us for whatever reason
    if len(argv) < 2:
        print("Must specify a subcommand.", file=sys.stderr)
        parser.print_usage(file=sys.stderr)
        return 2  # argparse exits with 2 on bad args, copy that

    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as e:
        return e.code

    # 'project_dir' is used for all subcommands now, but may not be always
    if 'project' in args:
        args.project = os.path.abspath(args.project)
    return args.main(args)


def main():
    """anaconda-project command line tool Conda-style entry point.

    Conda expects us to take no args and return an exit code.
    """
    return _parse_args_and_run_subcommand(sys.argv)
