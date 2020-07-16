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
"""Prune locker tests."""

import json
import logging
import tempfile
import unittest
from unittest.mock import MagicMock, call, create_autospec, mock_open, patch

from compliance.evidence import RawEvidence
from compliance.utils.exceptions import EvidenceNotFoundError

from prune.locker import PruneLocker


class TestPruneLocker(unittest.TestCase):
    """Test PruneLocker."""

    def setUp(self):
        """Initialize supporting test objects before each test."""
        logging.disable(logging.CRITICAL)
        self.mock_logger_error = MagicMock()
        self.mock_logger = create_autospec(logging.Logger)
        self.mock_logger.error = self.mock_logger_error
        self.ctime_patcher = patch('prune.locker.time.ctime')
        self.ctime_mock = self.ctime_patcher.start()
        self.ctime_mock.return_value = 'NOW'
        self.push_patcher = patch('compliance.locker.Locker.push')
        self.push_mock = self.push_patcher.start()
        self.checkin_patcher = patch('compliance.locker.Locker.checkin')
        self.checkin_mock = self.checkin_patcher.start()
        self.init_patcher = patch('compliance.locker.Locker.init')
        self.init_mock = self.init_patcher.start()

    def tearDown(self):
        """Cleanup supporting test objects after each test."""
        logging.disable(logging.NOTSET)
        self.ctime_patcher.stop()
        self.push_patcher.stop()
        self.checkin_patcher.stop()
        self.init_patcher.stop()

    def test_constructor(self):
        """Ensures a pruned list is added as an attribute."""
        locker = PruneLocker('repo-foo')
        self.assertEqual(locker.pruned, [])

    def test_custom_exit_no_push(self):
        """Ensures that the context manager exit routine does not run push."""
        with PruneLocker('repo-foo') as locker:
            locker.logger = self.mock_logger
            locker.pruned = ['foo', 'bar', 'baz']
        self.mock_logger_error.assert_not_called()
        self.checkin_mock.assert_called_once_with(
            'Pruned abandoned evidence at local time NOW\n\nfoo\nbar\nbaz'
        )
        self.push_mock.assert_not_called()

    def test_custom_exit_push(self):
        """Ensures that the context manager exit routine runs push."""
        with PruneLocker('repo-foo') as locker:
            locker.logger = self.mock_logger
            locker.pruned = ['foo', 'bar', 'baz']
            locker.repo_url_with_creds = 'my repo'
        self.mock_logger_error.assert_not_called()
        self.checkin_mock.assert_called_once_with(
            'Pruned abandoned evidence at local time NOW\n\nfoo\nbar\nbaz'
        )
        self.push_mock.assert_called_once()

    def test_custom_exit_error_logging(self):
        """Ensures that the context manager exit routine logs an exception."""
        with self.assertRaises(EvidenceNotFoundError):
            with PruneLocker('repo-foo') as locker:
                locker.logger = self.mock_logger
                locker.pruned = ['foo', 'bar', 'baz']
                locker.repo_url_with_creds = 'repo-foo-url'
                raise EvidenceNotFoundError('meh')
        self.mock_logger_error.assert_called_once_with(
            "<class 'compliance.utils.exceptions.EvidenceNotFoundError'> meh"
        )
        self.checkin_mock.assert_called_once_with(
            'Pruned abandoned evidence at local time NOW\n\nfoo\nbar\nbaz'
        )
        self.push_mock.assert_called_once()

    @patch('prune.locker.format_json')
    @patch('compliance.locker.Locker.remove_partitions')
    def test_remove_unpartitioned_evidence(
        self, mock_remove_parts, mock_format
    ):
        """Ensures that removing unpartitioned evidence works."""
        m = mock_open(
            read_data=json.dumps(
                {
                    'foo.json': {
                        'description': 'Foo evidence',
                        'last_update': 'a long time ago',
                        'ttl': 86400
                    }
                }
            )
        )
        with patch('builtins.open', m):
            evidence = RawEvidence(
                'foo.json', 'bar', description='Foo evidence'
            )
            with PruneLocker('repo-foo') as locker:
                mock_repo_index_add = MagicMock()
                mock_repo_index_remove = MagicMock()
                mock_repo_index = MagicMock()
                mock_repo_index.add = mock_repo_index_add
                mock_repo_index.remove = mock_repo_index_remove
                mock_repo = MagicMock()
                mock_repo.index = mock_repo_index
                locker.repo = mock_repo
                self.assertEqual(locker.pruned, [])
                locker.remove_evidence(evidence, 'Just cuz', 'finkel')
                mock_remove_parts.assert_not_called()
                mock_repo_index_remove.assert_called_once_with(
                    [f'{tempfile.gettempdir()}/repo-foo/raw/bar/foo.json'],
                    working_tree=True
                )
                self.assertEqual(locker.pruned, ['raw/bar/foo.json'])
                mock_format.assert_called_once_with(
                    {
                        'foo.json': {
                            'description': 'Foo evidence',
                            'pruned_by': 'finkel',
                            'tombstones': {
                                'foo.json': [
                                    {
                                        'eol': locker.commit_date,
                                        'last_update': 'a long time ago',
                                        'reason': 'Just cuz'
                                    }
                                ]
                            }
                        }
                    }
                )
                mock_repo_index_add.assert_called_once_with(
                    [f'{tempfile.gettempdir()}/repo-foo/raw/bar/index.json']
                )
        handle = m()
        self.assertEqual(handle.read.call_count, 1)
        self.assertIn(
            call(f'{tempfile.gettempdir()}/repo-foo/raw/bar/index.json'),
            m.mock_calls
        )
        self.assertEqual(handle.write.call_count, 1)
        self.assertIn(
            call(f'{tempfile.gettempdir()}/repo-foo/raw/bar/index.json', 'w'),
            m.mock_calls
        )

    @patch('prune.locker.format_json')
    @patch('compliance.locker.Locker.remove_partitions')
    def test_remove_partitioned_evidence(self, mock_remove_parts, mock_format):
        """Ensures that removing partitioned evidence works."""
        m = mock_open(
            read_data=json.dumps(
                {
                    'foo.json': {
                        'description': 'Foo evidence',
                        'last_update': 'a long time ago',
                        'ttl': 86400,
                        'partition_fields': ['whatever'],
                        'partition_root': None,
                        'partitions': {
                            'part-1': ['foo'], 'part-2': ['bar']
                        }
                    }
                }
            )
        )
        with patch('builtins.open', m):
            evidence = RawEvidence(
                'foo.json',
                'bar',
                description='Foo evidence',
                partition={'fields': ['whatever']}
            )
            with PruneLocker('repo-foo') as locker:
                mock_repo_index_add = MagicMock()
                mock_repo_index_remove = MagicMock()
                mock_repo_index = MagicMock()
                mock_repo_index.add = mock_repo_index_add
                mock_repo_index.remove = mock_repo_index_remove
                mock_repo = MagicMock()
                mock_repo.index = mock_repo_index
                locker.repo = mock_repo
                self.assertEqual(locker.pruned, [])
                locker.remove_evidence(evidence, 'Just cuz', 'finkel')
                mock_remove_parts.assert_called_once_with(
                    evidence, {
                        'part-1': ['foo'], 'part-2': ['bar']
                    }.keys()
                )
                mock_repo_index_remove.assert_not_called()
                self.assertEqual(locker.pruned, ['raw/bar/foo.json'])
                mock_format.assert_called_once_with(
                    {
                        'foo.json': {
                            'description': 'Foo evidence',
                            'pruned_by': 'finkel',
                            'tombstones': {
                                'part-1': [
                                    {
                                        'eol': locker.commit_date,
                                        'last_update': 'a long time ago',
                                        'partition_fields': ['whatever'],
                                        'partition_root': None,
                                        'partition_key': ['foo'],
                                        'reason': 'Just cuz'
                                    }
                                ],
                                'part-2': [
                                    {
                                        'eol': locker.commit_date,
                                        'last_update': 'a long time ago',
                                        'partition_fields': ['whatever'],
                                        'partition_root': None,
                                        'partition_key': ['bar'],
                                        'reason': 'Just cuz'
                                    }
                                ]
                            }
                        }
                    }
                )
                mock_repo_index_add.assert_called_once_with(
                    [f'{tempfile.gettempdir()}/repo-foo/raw/bar/index.json']
                )
        handle = m()
        self.assertEqual(handle.read.call_count, 1)
        self.assertIn(
            call(f'{tempfile.gettempdir()}/repo-foo/raw/bar/index.json'),
            m.mock_calls
        )
        self.assertEqual(handle.write.call_count, 1)
        self.assertIn(
            call(f'{tempfile.gettempdir()}/repo-foo/raw/bar/index.json', 'w'),
            m.mock_calls
        )
