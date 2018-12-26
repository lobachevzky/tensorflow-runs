# stdlib

# first party
from collections import defaultdict
import json
import re
from typing import List, Set

from runs.arguments import add_query_args
from runs.command import Command
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.subcommands.from_spec import SpecObj
from runs.util import ARGS


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'to-spec',
        help='Print json spec that reproduces crossproduct '
             'of args in given patterns.')
    parser.add_argument(
        '--exclude', nargs='*', default=set(), help='Keys of args to exclude.')
    add_query_args(parser, with_sort=False)
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], logger: Logger, exclude: List[str], *_, **__):
    if not runs:
        logger.exit("No commands found.")

    exclude = set(exclude)
    commands = [Command.from_run(run) for run in runs]
    for command in commands:
        for group in command.arg_groups[1:]:
            if isinstance(group, list):
                logger.exit(f"Command {command} contains multiple positional argument "
                            f"groups. Currently reproduce-to-spec only supports one "
                            f"positional argument group")
    stems = {' '.join(command.stem) for command in commands}
    if len(stems) > 1:
        logger.exit(
            "Commands do not start with the same positional arguments:",
            *commands,
            sep='\n')
    spec_dict = get_spec_obj(commands, exclude).dict()
    spec_dict = {k: v for k, v in spec_dict.items() if v}
    print(json.dumps(spec_dict, sort_keys=True, indent=4))


def get_spec_obj(commands: List[Command], exclude: Set[str]):
    stem = ' '.join(commands[0].stem)

    def group(pairs):
        d = defaultdict(list)
        for k, v in pairs:
            d[k].append(v)
        return d

    def get_args(command: Command):
        try:
            nonpositionals = command.arg_groups[1]
            for arg in nonpositionals:
                match = re.match('(-{1,2}[^=]*)=[\'"]?([^"]*)[\'"]?', arg)
                if match is not None:
                    key, value = match.groups()
                    try:
                        value = float(value)
                        if value % 1. == 0:
                            value = int(value)
                    except ValueError:
                        pass
                    key = key.lstrip('--')
                else:
                    value, = re.match('(-{1,2}.*)', arg).groups()
                    value = value.lstrip('--')
                    key = None
                if key not in exclude:
                    yield key, value
        except IndexError:
            yield None, None

    def squeeze(x):
        if len(x) == 1:
            return x[0]
        return x

    def remove_duplicates(values):
        values = set(map(tuple, values))
        return list(map(list, values))

    command_args = [group(get_args(c)) for c in commands]
    keys = {k for args in command_args for k in args.keys()}
    for args in command_args:
        for k in keys:
            if k not in args:
                args[k] = [None]
    grouped_args = group((pair for args in command_args for pair in args.items()))
    flags = remove_duplicates(grouped_args.pop(None, []))

    args = {k: list(map(squeeze, v)) for k, v in grouped_args.items()}

    return SpecObj(command=stem, args=args, flags=flags or None)