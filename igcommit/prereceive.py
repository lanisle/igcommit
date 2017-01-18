"""igcommit - Pre-receive hook routines

Copyright (c) 2016, InnoGames GmbH
"""

from collections import defaultdict
from fileinput import input
from time import sleep

from igcommit.base_check import CheckState, prepare_checks
from igcommit.config import checks
from igcommit.git import Commit
from igcommit.utils import iter_buffer


class Runner(object):
    def __init__(self):
        self.state = CheckState.new
        self.checked_commit_ids = set()
        self.changed_file_checks = defaultdict(list)

    def run(self):
        # We are buffering the checks to let them run parallel in
        # the background.  Parallelization only applies to the CheckCommands.
        # It has no overhead, because we have to run those commands the same
        # way externally, anyway.  We only have a limit to avoid consuming
        # too many processes.
        for check in iter_buffer(self.expand_checks(checks), 16):
            if check:
                check.print_problems()
                assert check.state >= CheckState.done
                self.state = max(self.state, check.state)

        if self.state >= CheckState.failed:
            raise SystemExit('Checks failed')

    def expand_checks(self, checks):
        next_checks = []
        for check in prepare_checks(checks, None, next_checks):
            yield check

        for line in input():
            for check in self.expand_checks_to_input(next_checks, line):
                yield check

    def expand_checks_to_input(self, checks, line):
        line_split = line.split()
        commit = Commit(line_split[1])
        if not commit:
            return

        commit_list = commit.get_new_commit_list(line_split[2])

        # Appending the actual commit on the list to the new ones makes
        # testing easier.
        if commit not in commit_list:
            commit_list.append(commit)

        for check in self.expand_checks_to_commit_list(checks, commit_list):
            yield check

    def expand_checks_to_commit_list(self, checks, commit_list):
        next_checks = []
        for check in prepare_checks(checks, commit_list, next_checks):
            yield check

        for commit in commit_list:
            if commit.commit_id not in self.checked_commit_ids:
                for check in self.expand_checks_to_commit(next_checks, commit):
                    yield check
                self.checked_commit_ids.add(commit.commit_id)

    def expand_checks_to_commit(self, checks, commit):
        next_checks = []
        for check in prepare_checks(checks, commit, next_checks):
            yield check

        for changed_file in commit.get_changed_files():
            for check in self.expand_checks_to_file(next_checks, changed_file):
                yield check

    def expand_checks_to_file(self, checks, changed_file):
        for check in self.changed_file_checks[changed_file.path]:
            assert check.state >= CheckState.cloned
            # Wait for the check to run
            while check.state < CheckState.done:
                yield None
                sleep(0.1)
            if check.state >= CheckState.failed:
                return

        for check in prepare_checks(checks, changed_file):
            yield check
            self.changed_file_checks[changed_file.path].append(check)


def main():
    Runner().run()