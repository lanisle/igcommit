"""igcommit - Utility functions

Copyright (c) 2016, InnoGames GmbH
"""

from __future__ import unicode_literals

from os import environ, access, X_OK, getcwd
from os.path import basename, dirname
from subprocess import check_output, CalledProcessError, Popen, PIPE, STDOUT

import igcommit.config


def target_files(all_files):
    repos_root = getcwd()
    group_name = basename(dirname(repos_root))
    repos_name = basename(repos_root).split('.')[0]

    filemap = {}
    for file in all_files:
        filemap[file.path] = file

    p = Popen([igcommit.config.target_inquery_api, '{}/{}'.format(group_name, repos_name)], stdin=PIPE, stdout=PIPE)
    lines = '\n'.join([f.path for f in all_files])
    p.stdin.write(lines.encode()) # python 3 compatible
    p.stdin.close()

    ret = []
    for line in p.stdout.read().splitlines():
        path, result = line.decode().split()
        if result == 'yes':
            ret.append(filemap[path])

    return ret


def get_exe_path(exe):
    if exe.find('/') >= 0:
        if access(exe, X_OK):
            return exe
        else:
            return None

    for dir_path in environ['PATH'].split(':'):
        path = dir_path.strip('"') + '/' + exe
        if access(path, X_OK):
            return path

    return None


def iter_buffer(iterable, amount):
    assert amount > 1
    memo = []
    for elem in iterable:
        if elem is not None:
            memo.append(elem)
            if len(memo) < amount:
                continue
        yield memo.pop(0)

    for elem in memo:
        yield elem
