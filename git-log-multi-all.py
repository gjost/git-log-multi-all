#!/usr/bin/env python

#
# git-log-multi-all.py
#

DESCRIPTION = """Lists commits on all branches within specified period across multiple Git repositories"""

EPILOG = """
Useful for filling out timesheets.  Note that dates reflect the time
*commits* were made rather than when the actual work was performed.

Specify a list of Git repositories. The script will list all commits
on all branches in all of the specified repositories during the
specified time.  Useful for getting a good picture of activity across
projects.

Filename must contain list of absolute paths to Git repositories you
with to read, one per line.  Comments using '#' are understood.

INSTALL

    source $VIRTUALENV
    pip install blessings dateutil gitpython

EXAMPLES

    python timesheets.py $LISTOFREPOS --start=2017-05-01 --end=2017-05-31
    python timesheets.py $LISTOFREPOS --month=2017-05
"""

import argparse
import calendar
from datetime import date,datetime
import os

from blessings import Terminal
import git
from dateutil import parser

TERM = Terminal()

TEMPLATE = '{ts} ' \
           '{t.yellow}{commit}{t.normal} ' \
           '{t.green}({author}){t.normal} ' \
           '{t.yellow}{repo}{t.normal} ' \
           '{t.red}[{branch}]{t.normal} ' \
           '{subject}'

def get_repos_list(filename):
    with open(filename, 'r') as f:
        return [
            line
            for line in f.read().splitlines()
            if not (line.find('#') == 0)
        ]

def get_start_end(start=None, end=None, month=None):
    """
    @param start: str
    @param end: str
    @param month: str
    """
    if start and end:
        start = parser.parse(start)
        end = parser.parse(end)
    elif month:
        start = parser.parse(month)
        end = date(
            start.year,
            start.month,
            calendar.monthrange(start.year, start.month)[1]
        )
    return start,end

def get_repo(path):
    return git.Repo(path)

def repo_commits(repo, since, until):
    """
    @param repo: git.Repo
    @param start: datetime
    @param end: datetime
    """
    repo_name = os.path.basename(repo.working_dir)
    # git log --all --since=2017-05-01 --until=2017-05-31 --no-merges --pretty=format:"%h|%ci|%ce|%d|%s" --reverse
    raw = repo.git.log(
        '--all',
        '--no-merges',
        '--since=%s' % since.strftime('%Y-%m-%d'),
        '--until=%s' % until.strftime('%Y-%m-%d'),
        '--pretty=format:"%h|%ci|%cn|%d|%s"',
    )
    commits = []
    branch = ''
    for line in raw.splitlines():
        commit,rawdate,email,refname,subject = line.strip().replace('"','').split('|')
        # branch in every commit
        if refname:
            # strip out parens, keep only final branch name
            branch = refname.strip().replace('(','').replace(')','') # .split(',')[-1].strip()
        ts = parser.parse(rawdate)
        commits.append({
            'repo': repo_name,
            'commit': commit,
            'date': rawdate,
            'ts': ts,
            'author': email,
            'branch': branch,
            'subject': subject
        })
    sorted(commits, key=lambda commit: commit['ts'])
    commits.reverse()
    return commits

def assign_to_date(commits, dates):
    """Add each commit to a list according to date
    
    @param commits: list of commit dicts
    @param dates: dict of commit dicts by date '%Y-%m-%d'
    @returns: dict of lists by dates
    """
    for commit in commits:
        d = commit['ts'].strftime('%Y-%m-%d')
        if not dates.get(d):
            dates[d] = []
        dates[d].append(commit)
    return dates

def print_commits(commits, template):
    """Print list of commits
    """
    sorted(commits, key=lambda commit: commit['ts'])
    commits.reverse()
    for c in commits:
        print(template.format(
            t=TERM,
            commit=c['commit'],
            ts=c['ts'].strftime('%H:%M:%S'),
            repo=c['repo'],
            branch=c['branch'],
            author=c['author'],
            subject=c['subject'],
        ))

def print_day(dstr, commits, template):
    day = parser.parse(dstr)
    print('------------------------------------------------------------------------')
    print(day.strftime('%Y-%m-%d %A'))
    print_commits(commits, template)
    print('')


def main():
    
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    #parser.add_argument('pos', help='Positional arg')
    parser.add_argument('filename', help='Filename containing list of abs paths to repositories.')
    parser.add_argument('-s', '--start', help='Start date (ex: "2017-05-01")')
    parser.add_argument('-e', '--end', help='End date (ex: "2017-05-31")')
    parser.add_argument('-m', '--month', help='Month (ex: "2017-05")')
    args = parser.parse_args()

    if not (args.month or (args.start and args.end)):
        raise Exception('Enter start/end dates or a month.')

    start,end = get_start_end(start=args.start, end=args.end, month=args.month)
    print('start: %s' % start)
    print('  end: %s' % end)
    print('')
    
    commits_by_date = {}
    
    print('Reading list...')
    REPOS = get_repos_list(args.filename)
    
    print('Gathering data...')
    for path in REPOS:
        print(path)
        repo = get_repo(path)
        commits = repo_commits(repo, start, end)
        commits_by_date = assign_to_date(commits, commits_by_date)
    print('')

    dates = commits_by_date.keys()
    dates.sort()

    for d in dates:
        commits = commits_by_date[d]
        print_day(d, commits, TEMPLATE)
    

if __name__ == '__main__':
    main()
