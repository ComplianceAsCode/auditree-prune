# -*- mode:python; coding:utf-8 -*-
# Copyright (c) 2020 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Prune CLI tests."""

import json
import logging
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from prune.cli import Prune


class TestPruneCLI(unittest.TestCase):
    """Test Prune CLI execution."""

    def setUp(self):
        """Initialize supporting test objects before each test."""
        logging.disable(logging.CRITICAL)
        self.prune = Prune()
        self.grc_patcher = patch('git.Repo.clone_from')
        self.git_repo_clone_from_mock = self.grc_patcher.start()
        self.git_remote_push_mock = MagicMock()
        git_remote_mock = MagicMock()
        git_remote_mock.push = self.git_remote_push_mock
        git_remotes_mock = MagicMock()
        git_remotes_mock.__getitem__ = MagicMock(return_value=git_remote_mock)
        git_config_parser_mock = MagicMock()
        git_config_parser_mock.get_value = MagicMock(return_value='finkel')
        repo_mock = MagicMock()
        repo_mock.config_reader = MagicMock(
            return_value=git_config_parser_mock
        )
        repo_mock.remotes = git_remotes_mock
        self.git_repo_clone_from_mock.return_value = repo_mock
        self.lic_patcher = patch('compliance.locker.Locker.init_config')
        self.locker_init_config_mock = self.lic_patcher.start()
        self.lci_patcher = patch('compliance.locker.Locker.checkin')
        self.locker_checkin_mock = self.lci_patcher.start()
        self.plre_patcher = patch('prune.locker.PruneLocker.remove_evidence')
        self.prune_locker_remove_evidence_mock = self.plre_patcher.start()
        self.lge_patcher = patch('compliance.locker.Locker.get_evidence')
        self.locker_get_evidence_mock = self.lge_patcher.start()
        self.locker_get_evidence_mock.return_value = 'Remove me!!'
        self.srm_patcher = patch('prune.cli.shutil.rmtree')
        self.shutil_rmtree_mock = self.srm_patcher.start()
        self.dry_run = [
            'dry-run',
            'https://github.com/foo/bar',
            '--creds',
            './test/fixtures/faux_creds.ini'
        ]
        self.push_remote = ['push-remote'] + self.dry_run[1:]

    def tearDown(self):
        """Cleanup supporting test objects after each test."""
        logging.disable(logging.NOTSET)
        self.grc_patcher.stop()
        self.lic_patcher.stop()
        self.lci_patcher.stop()
        self.plre_patcher.stop()
        self.lge_patcher.stop()
        self.srm_patcher.stop()

    def test_no_config_validation(self):
        """Ensures processing stops when no evidence config is provided."""
        self.prune.run(self.push_remote)
        self.git_repo_clone_from_mock.assert_not_called()
        self.locker_init_config_mock.assert_not_called()
        self.locker_get_evidence_mock.assert_not_called()
        self.prune_locker_remove_evidence_mock.assert_not_called()
        self.locker_checkin_mock.assert_not_called()
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_not_called()

    def test_multiple_config_validation(self):
        """Ensures processing stops when both config and path provided."""
        self.prune.run(
            self.push_remote + [
                '--config',
                json.dumps({'foo': 'bar'}),
                '--config-file',
                'foo/bar/baz_cfg.json'
            ]
        )
        self.git_repo_clone_from_mock.assert_not_called()
        self.locker_init_config_mock.assert_not_called()
        self.locker_get_evidence_mock.assert_not_called()
        self.prune_locker_remove_evidence_mock.assert_not_called()
        self.locker_checkin_mock.assert_not_called()
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_not_called()

    def test_multiple_git_config_validation(self):
        """Ensures processing stops when both git-config and path provided."""
        self.prune.run(
            self.push_remote + [
                '--git-config',
                json.dumps({'foo': 'bar'}),
                '--git-config-file',
                'foo/bar/baz_cfg.json'
            ]
        )
        self.git_repo_clone_from_mock.assert_not_called()
        self.locker_init_config_mock.assert_not_called()
        self.locker_get_evidence_mock.assert_not_called()
        self.prune_locker_remove_evidence_mock.assert_not_called()
        self.locker_checkin_mock.assert_not_called()
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_not_called()

    def test_dry_run_config(self):
        """Ensures dry-run mode works when config JSON is provided."""
        config = {'raw/foo/bar.json': 'A good reason'}
        self.prune.run(self.dry_run + ['--config', json.dumps(config)])
        self.git_repo_clone_from_mock.assert_called_once_with(
            'https://1a2b3c4d5e6f7g8h9i0@github.com/foo/bar',
            f'{tempfile.gettempdir()}/prune',
            branch='master'
        )
        self.locker_init_config_mock.assert_called_once_with()
        self.locker_get_evidence_mock.assert_called_once_with(
            'raw/foo/bar.json', ignore_ttl=True
        )
        self.prune_locker_remove_evidence_mock.assert_called_once_with(
            'Remove me!!', 'A good reason', 'finkel'
        )
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_called_once_with(
            f'{tempfile.gettempdir()}/prune'
        )

    def test_dry_run_config_file(self):
        """Ensures dry-run mode works when a config file is provided."""
        config_file = './test/fixtures/faux_config.json'
        self.prune.run(self.dry_run + ['--config-file', config_file])
        self.git_repo_clone_from_mock.assert_called_once_with(
            'https://1a2b3c4d5e6f7g8h9i0@github.com/foo/bar',
            f'{tempfile.gettempdir()}/prune',
            branch='master'
        )
        self.locker_init_config_mock.assert_called_once_with()
        self.locker_get_evidence_mock.assert_called_once_with(
            'raw/foo/bar.json', ignore_ttl=True
        )
        self.prune_locker_remove_evidence_mock.assert_called_once_with(
            'Remove me!!', 'A good reason', 'finkel'
        )
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_called_once_with(
            f'{tempfile.gettempdir()}/prune'
        )

    def test_dry_run_git_config(self):
        """Ensures dry-run mode works when a git config is provided."""
        config = {'raw/foo/bar.json': 'A good reason'}
        git_config = {
            'commit': {
                'gpgsign': True
            },
            'user': {
                'signingKey': '...', 'email': '...', 'name': '...'
            }
        }
        self.prune.run(
            self.dry_run + [
                '--config',
                json.dumps(config),
                '--git-config',
                json.dumps(git_config)
            ]
        )
        self.git_repo_clone_from_mock.assert_called_once_with(
            'https://1a2b3c4d5e6f7g8h9i0@github.com/foo/bar',
            f'{tempfile.gettempdir()}/prune',
            branch='master'
        )
        self.locker_init_config_mock.assert_called_once_with()
        self.locker_get_evidence_mock.assert_called_once_with(
            'raw/foo/bar.json', ignore_ttl=True
        )
        self.prune_locker_remove_evidence_mock.assert_called_once_with(
            'Remove me!!', 'A good reason', 'finkel'
        )
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_called_once_with(
            f'{tempfile.gettempdir()}/prune'
        )

    def test_dry_run_git_config_file(self):
        """Ensures dry-run mode works when a git config file is provided."""
        config = {'raw/foo/bar.json': 'A good reason'}
        self.prune.run(
            self.dry_run + [
                '--config',
                json.dumps(config),
                '--git-config-file',
                './test/fixtures/faux_git_config.json'
            ]
        )
        self.git_repo_clone_from_mock.assert_called_once_with(
            'https://1a2b3c4d5e6f7g8h9i0@github.com/foo/bar',
            f'{tempfile.gettempdir()}/prune',
            branch='master'
        )
        self.locker_init_config_mock.assert_called_once_with()
        self.locker_get_evidence_mock.assert_called_once_with(
            'raw/foo/bar.json', ignore_ttl=True
        )
        self.prune_locker_remove_evidence_mock.assert_called_once_with(
            'Remove me!!', 'A good reason', 'finkel'
        )
        self.git_remote_push_mock.assert_not_called()
        self.shutil_rmtree_mock.assert_called_once_with(
            f'{tempfile.gettempdir()}/prune'
        )

    def test_push_remote(self):
        """
        Ensures push-remote mode works as expected.

        No other tests needed for push-remote since push-remote and dry-run
        use the same core prune command logic.
        """
        config = {'raw/foo/bar.json': 'A good reason'}
        self.prune.run(self.push_remote + ['--config', json.dumps(config)])
        self.git_repo_clone_from_mock.assert_called_once_with(
            'https://1a2b3c4d5e6f7g8h9i0@github.com/foo/bar',
            f'{tempfile.gettempdir()}/prune',
            branch='master'
        )
        self.locker_init_config_mock.assert_called_once_with()
        self.locker_get_evidence_mock.assert_called_once_with(
            'raw/foo/bar.json', ignore_ttl=True
        )
        self.prune_locker_remove_evidence_mock.assert_called_once_with(
            'Remove me!!', 'A good reason', 'finkel'
        )
        self.git_remote_push_mock.assert_called_once_with()
        self.shutil_rmtree_mock.assert_called_once_with(
            f'{tempfile.gettempdir()}/prune'
        )
