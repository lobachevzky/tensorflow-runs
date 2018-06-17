import re
from typing import List

from runs.database import DataBase
from runs.logger import Logger
from runs.util import RunPath, highlight


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'reproduce',
        help='Print commands to reproduce a run. This command '
        'does not have side-effects (besides printing).')
    parser.add_argument('patterns', nargs='+', type=RunPath)
    parser.add_argument(
        '--description',
        type=str,
        default=None,
        help="Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='If this flag is given, a timestamp will be '
        'appended to any new name that is already in '
        'the database.  Otherwise this entry will '
        'overwrite any entry with the same name. ')
    parser.add_argument(
        '--unless',
        nargs='*',
        type=RunPath,
        help='Print list of path names without tree '
             'formatting.')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath],
        db: DataBase, *args, **kwargs):
    db.logger.print(string(*patterns, unless=unless, db=db))


def string(*patterns, unless: List[RunPath], db: DataBase):
    for entry in db.descendants(*patterns, unless=unless):
        new_path = entry.path
        pattern = re.compile('(.*\.)(\d*)')
        matches = pattern.match(entry.path)
        if matches:
            trailing_number = int(matches[2]) + 1
            new_path = matches[1] + str(trailing_number)
        else:
            new_path += '.1'
        return '\n'.join([
            highlight('To reproduce:'), f'git checkout {entry.commit}\n',
            f"runs new {new_path} '{entry.input_command}' --description='Reproduce {new_path}. "
            f"Original description: {entry.description}'"
        ])
