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
"""Prune Locker."""

import json
import time

from compliance.locker import Locker
from compliance.utils.data_parse import format_json


class PruneLocker(Locker):
    """Provide prune specific locker functionality."""

    def __init__(self, *args, **kwargs):
        """Prune locker constructor to add evidences pruned."""
        super().__init__(*args, **kwargs)
        self.pruned = []

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Override check in routine with a custom prune commit message."""
        if exc_type:
            self.logger.error(' '.join([str(exc_type), str(exc_val)]))
        pruned_files = '\n'.join(self.pruned)
        self.checkin(
            (
                'Pruned abandoned evidence at local time '
                f'{time.ctime(time.time())}\n\n{pruned_files}'
            )
        )
        if self.repo_url_with_creds:
            self.push()
        return

    def remove_evidence(self, evidence, reason, pruner):
        """
        Remove the evidence file(s) and update the evidence metadata.

        :param evidence: the evidence object
        :param reason: a string giving the reason for evidence removal
        :param pruner: a string providing the email of the git user
        """
        with self.lock:
            index_file = self.get_index_file(evidence)
            metadata = json.loads(open(index_file).read())
            ev_meta = metadata.get(evidence.name, {})
            tombstone_args = [evidence.name, ev_meta, reason]
            if getattr(evidence, 'is_partitioned', False):
                parts = ev_meta.get('partitions', {}).keys()
                self.remove_partitions(evidence, parts)
                tombstone_args[0] = parts
            else:
                self.repo.index.remove(
                    [self.get_file(evidence.path)], working_tree=True
                )
            self.pruned.append(evidence.path)
            metadata[evidence.name] = {
                'description': evidence.description,
                'pruned_by': pruner,
                'tombstones': self.create_tombstone_metadata(*tombstone_args)
            }
            with open(index_file, 'w') as f:
                f.write(format_json(metadata))
            self.repo.index.add([index_file])
