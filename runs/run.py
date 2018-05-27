import re
import subprocess
from datetime import datetime
from pathlib import Path

from anytree.exporter import DictExporter

from runs.db import no_match
from runs.db_path import DBPath
from runs.run_node import RunNode
from runs.util import COMMIT, DESCRIPTION, cmd, dirty_repo, get_permission, highlight, last_commit, prune_leaves, string_from_vim


class Run:
    """
    A Run aggregates the tmux process, the directories, and the db entry relating to a run.
    """
    def __init__(self, path: Path, root):
        self.path = DBPath(path)
        self.root = root

    def node(self):
        return self.path.node(self.root)

    def keys(self):
        return [
            'command' if k is '_input_command' else k
            for k in DictExporter().export(self.node()).keys()
        ]

    # Commands
    def new(self, command, description, assume_yes, flags):
        # Check if repo is dirty
        if dirty_repo():
            prompt = "Repo is dirty. You should commit before run. Run anyway?"
            if not (assume_yes or get_permission(prompt)):
                exit()

        # Check if path already exists
        if self.node() is not None:
            if assume_yes or get_permission(self.path,
                                            'already exists. Overwrite?'):
                self.remove()
            else:
                exit()

        # create directories
        self.mkdirs()

        # process info
        full_command = self.build_command(command, flags)

        prompt = 'Edit the description of this run: (Do not edit the line or above.)'
        if description is None:
            description = string_from_vim(prompt, description)
        if description == 'commit-message':
            description = cmd('git log -1 --pretty=%B'.split())

        # tmux
        self.new_tmux(description, full_command)

        # new db entry
        with self.open_root() as root:
            RunNode(
                name=self.head,
                full_command=full_command,
                commit=last_commit(),
                datetime=datetime.now().isoformat(),
                description=description,
                input_command=command,
                parent=self.parent.add_to_tree(root))

        # print result
        self.print(highlight('Description:'))
        self.print(description)
        self.print(highlight('Command sent to session:'))
        self.print(full_command)
        self.print(highlight('List active:'))
        self.print('tmux list-session')
        self.print(highlight('Attach:'))
        self.print('tmux attach -t', self.tmux_name(self.path))

    def build_command(self, command, flags):
        for flag in flags:
            flag = self.interpolate_keywords(flag)
            command += ' ' + flag
        return self.cfg.prefix + command

    def interpolate_keywords(self, string):
        keywords = dict(path=self.path, name=self.head)
        for match in re.findall('.*<(.*)>', string):
            assert match in keywords
        for word, replacement in keywords.items():
            string = string.replace('<' + word + '>', replacement)
        return string

    def remove(self):
        self.kill_tmux()
        self.rmdirs()
        with self.open() as node:
            if node:
                prune_leaves(node)

    def move(self, dest, kill_tmux):
        assert isinstance(dest, Run)
        self.mvdirs(dest)
        if kill_tmux:
            self.kill_tmux()
        else:
            self.rename_tmux(dest.head)
        with self.open_root() as root:
            node = self.node(root)
            node.name = dest.head
            old_parent = node.parent
            node.parent = dest.parent.add_to_tree(root)
            prune_leaves(old_parent)

    def lookup(self, key):
        if key == 'command':
            key = '_input_command'
        try:
            node = self.node()
            if node is None:
                no_match(self.path, db_path=self.cfg.db_path)
            return getattr(node, key)
        except AttributeError:
            self.exit("`{}` not a valid key. Valid keys are {}.".format(
                key, self.keys))

    # tmux
    @staticmethod
    def tmux_name(name):
        return name.replace('.', ',').replace(':', ';')

    def kill_tmux(self):
        cmd('tmux kill-session -t'.split() + [self.tmux_name(self.path)], fail_ok=True)

    def new_tmux(self, window_name, main_cmd):
        self.kill_tmux()
        tmux_sess_name = self.tmux_name(self.path)
        subprocess.check_call(
            'tmux new -d -s'.split() + [tmux_sess_name, '-n', window_name])
        cd_cmd = 'cd ' + str(Path.cwd())
        for command in [cd_cmd, main_cmd]:
            cmd('tmux send-keys -t'.split() + [tmux_sess_name, command, 'Enter'])

    def rename_tmux(self, new):
        names = [self.tmux_name(n) for n in [self.path, new]]
        cmd('tmux rename-session -t '.split() + names, fail_ok=True)

    def chdescription(self, new_description):
        with self.open() as node:
            if new_description is None:
                new_description = string_from_vim('Edit description',
                                                  node.description)
            node.description = new_description

    def reproduce(self, no_overwrite):
        path = self.path
        if no_overwrite:
            path += datetime.now().isoformat()
        return 'To reproduce:\n' + \
               highlight('git checkout {}\n'.format(self.lookup(COMMIT))) + \
               highlight("runs new {} '{}' --description='Reproduce {}. "
                         "Original description: {}'".format(
                             path, self.lookup('_input_command'), self.path, self.lookup(DESCRIPTION)))

    def pretty_print(self):
        return self.path + '\n' + \
            '=' * len(self.path) + """
Command
-------
{}
Commit
------
{}
Date/Time
---------
{}
Description
-----------
{}
""".format(*map(self.lookup, ['full_command', 'commit', 'datetime', 'description']))
