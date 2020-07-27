[![OS Compatibility][platform-badge]](#prerequisites)
[![Python Compatibility][python-badge]][python-dl]
[![pre-commit][pre-commit-badge]][pre-commit]
[![Code validation](https://github.com/ComplianceAsCode/auditree-prune/workflows/format%20%7C%20lint%20%7C%20test/badge.svg)][lint-test]
[![Upload Python Package](https://github.com/ComplianceAsCode/auditree-prune/workflows/PyPI%20upload/badge.svg)][pypi-upload]

# auditree-prune

The Auditree evidence removal tool.

## Introduction

Auditree `prune` is a command line tool that assists in managing evidence locker
abandoned evidence.  It provides a thoughtful way to remove evidence from an
evidence locker while retaining the evidence metadata so that, if necessary,
retrieving the removed evidence from git history is made easier.  Auditree `prune`
does this by handling the removal of the evidence file(s) from an evidence locker
git repository and providing "tombstoned" metadata that can be used to map back to
a point in time where the evidence still existed in the evidence locker.

## Prerequisites

- Supported for execution on OSX and LINUX.
- Supported for execution with Python 3.6 and above.

Python 3 must be installed, it can be downloaded from the [Python][python-dl]
site or installed using your package manager.

Python version can be checked with:

```sh
python --version
```

or

```sh
python3 --version
```

The `prune` tool is available for download from [PyPI](https://pypi.org/project/auditree-prune/).

## Installation

It is best practice, but not mandatory, to run `prune` from a dedicated Python
virtual environment.  Assuming that you have the Python [virtualenv][virtual-env]
package already installed, you can create a virtual environment named `venv` by
executing `virtualenv venv` which will create a `venv` folder at the location of
where you executed the command.  Alternatively you can use the python `venv` module
to do the same.

```sh
python3 -m venv venv
```

Assuming that you have a virtual environment and that virtual environment is in
the current directory then to install a new instance of `prune`, activate
your virtual environment and use `pip` to install `prune` like so:

```sh
. ./venv/bin/activate
pip install auditree-prune
```

As we add new features to `prune` you will want to upgrade your `prune`
package.  To upgrade `prune` to the most recent version do:

```sh
. ./venv/bin/activate
pip install auditree-prune --upgrade
```

See [pip documentation][pip-docs] for additional options when using `pip`.

## Configuration

Since Auditree `prune` interacts with Git repositories, it requires Git remote
hosting service credentials in order to do its thing.  Auditree `prune` will by
default look for a `username` and `token` in a `~/.credentials` file.  You can
override the credentials file location by using the `--creds` option on a `prune`
CLI execution. Valid section headings include `github`, `github_enterprise`, `bitbucket`,
and `gitlab`.  Below is an example of the expected credentials entry.

```ini
[github]
username=your-gh-username
token=your-gh-token
```

## Execution

Auditree `prune` is a simple CLI that performs the function of archiving off
abandoned evidence.  As such, it has two execution modes; a `push-remote` mode and
a `dry-run` mode.  Both modes will clone a git repository and place it into the
`$TMPDIR/prune` folder.  Both modes will also provide handy progress output as
`prune` processes the abandoned evidence.  The final step in both modes is to remove
the locally cloned repository from the temp directory.  However, `push-remote` will
push the changes to the remote repository before removing the locally cloned copy
whereas `dry-run` will not.

As most CLIs, Auditree `prune` comes with a help facility.

```sh
prune -h
```

```sh
prune push-remote -h
```

```sh
prune dry-run -h
```

### push-remote mode

Use the `push-remote` mode when you want your changes to be applied to the remote
evidence locker.  You can provide as many _evidence path_/_reason for removal_
key/value pairs as you need as part of the `--config` or as contents of your
`--config-file`.

```sh
prune push-remote https://github.com/org-foo/repo-bar --config '{"raw/foo/bar.json":"bar.json is abandoned",...}'
```

```sh
prune push-remote https://github.com/org-foo/repo-bar --config-file ./path/to/my/prune/evidence.json
```

### dry-run mode

Use the `dry-run` mode when you want don't your changes to be applied to the remote
evidence locker and are just interested in seeing what effect the execution will have
on our evidence locker before you commit to pushing your changes to the remote repository.
You can provide as many _evidence path_/_reason for removal_ key/value pairs as you
need as part of the `--config` or as contents of your `--config-file`.

```sh
prune dry-run https://github.com/org-foo/repo-bar --config '{"raw/foo/bar.json":"bar.json is abandoned",...}'
```

```sh
prune dry-run https://github.com/org-foo/repo-bar --config-file ./path/to/my/prune/evidence.json
```


[platform-badge]: https://img.shields.io/badge/platform-osx%20|%20linux-orange.svg
[python-badge]: https://img.shields.io/badge/python-v3.6+-blue.svg
[pre-commit-badge]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
[python-dl]: https://www.python.org/downloads/
[pre-commit]: https://github.com/pre-commit/pre-commit
[pip-docs]: https://pip.pypa.io/en/stable/reference/pip/
[virtual-env]: https://pypi.org/project/virtualenv/
[lint-test]: https://github.com/ComplianceAsCode/auditree-prune/actions?query=workflow%3A%22format+%7C+lint+%7C+test%22
[pypi-upload]: https://github.com/ComplianceAsCode/auditree-prune/actions?query=workflow%3A%22PyPI+upload%22
