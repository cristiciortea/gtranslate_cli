#! ../.venv/bin/python
import argparse
import sys
import colorama
from colorama import Fore, Style
import pathlib
import Pyro5.api

import log

AVAILABLE_LANGUAGES = ["en", "it", "de"]

# Logger set up
logger = log.setup_custom_logger('root')

# Colorama initialization for Windows.
# Other platforms doesn't need initialization and init will have no effect
colorama.init()


# Customize argument parser
class CustomizedArgumentParser(argparse.ArgumentParser):

    def format_help(self):
        formatter = self._get_formatter()

        # description
        formatter.add_text(self.description)

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups, prefix='Usage: ')

        # positionals, optionals and user-defined groups
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def error(self, message):
        sys.stderr.write(Fore.RED + f'Error: {message}\n' + Style.RESET_ALL)
        self.print_usage()
        sys.exit(2)


class CustomizedHelpFormatter(argparse.HelpFormatter):
    def format_help(self):
        help = self._root_section.format_help()
        if help:
            help = self._long_break_matcher.sub('\n\n', help)
            help = help.strip('\n').replace('\n\n', '\n')
        return help

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        usage = usage + '\n'
        return super(CustomizedHelpFormatter, self).add_usage(
            usage, actions, groups, prefix)


# Create the customized argument parser
cli_parser = CustomizedArgumentParser(prog='gtranslate',
                                      usage='%(prog)s -f <filename> -l <lang>',
                                      description='gtanslate 1.0: command line utility for translating text',
                                      formatter_class=CustomizedHelpFormatter,
                                      add_help=False)

# Add a group arg to the argument parser
arg_group = cli_parser.add_argument_group('Parameters')
arg_group.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
arg_group.add_argument('-f',
                       help='path to input filename to be translated',
                       required=True,
                       type=str,
                       metavar='<filename>:',
                       dest='filename'
                       )
arg_group.add_argument('-l',
                       help='output language, can be one of "en", "it" or "de"',
                       required=True,
                       type=str,
                       metavar='<lang>:',
                       dest='language')


def main():
    # Parse user arguments
    args = cli_parser.parse_args()

    # Arguments validity checks
    file_name = args.filename
    file_path = pathlib.Path(file_name)

    language = args.language

    if not file_path.exists():
        raise FileNotFoundError(Fore.RED + f'File: {file_name} not found in path: {file_path.parent}' + Style.RESET_ALL)

    if language not in AVAILABLE_LANGUAGES:
        raise NotImplementedError(Fore.RED + f'Language "{language}" is not a valid language, please use one of the '
                                             f'languages available: {AVAILABLE_LANGUAGES}' + Style.RESET_ALL)

    # Interact with the python daemon
    # try the connection maybe the daemon is not started
    translate_queue = Pyro5.api.Proxy("PYRONAME:translate.queue")
    print(translate_queue.get_translated_items())


if __name__ == '__main__':
    main()
