# Copyright The PyTorch Lightning team.
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

from collections import namedtuple
from functools import partial

import numpy as np
import pytest
import torch

from torchmetrics.functional.regression.log_cosh import log_cosh_error
from torchmetrics.regression.log_cosh import LogCoshError
from unittests.helpers import seed_all
from unittests.helpers.testers import BATCH_SIZE, NUM_BATCHES, MetricTester

seed_all(42)

num_targets = 5

Input = namedtuple("Input", ["preds", "target"])

_single_target_inputs = Input(
    preds=torch.rand(NUM_BATCHES, BATCH_SIZE),
    target=torch.rand(NUM_BATCHES, BATCH_SIZE),
)

_multi_target_inputs = Input(
    preds=torch.rand(NUM_BATCHES, BATCH_SIZE, num_targets),
    target=torch.rand(NUM_BATCHES, BATCH_SIZE, num_targets),
)


def sk_log_cosh_error(preds, target):
    preds, target = preds.numpy(), target.numpy()
    diff = preds - target
    if diff.ndim == 1:
        return np.mean(np.log((np.exp(diff) + np.exp(-diff)) / 2))
    return np.mean(np.log((np.exp(diff) + np.exp(-diff)) / 2), axis=0)


@pytest.mark.parametrize(
    "preds, target",
    [
        (_single_target_inputs.preds, _single_target_inputs.target),
        (_multi_target_inputs.preds, _multi_target_inputs.target),
    ],
)
class TestLogCoshError(MetricTester):
    @pytest.mark.parametrize("ddp", [True, False])
    @pytest.mark.parametrize("dist_sync_on_step", [True, False])
    def test_log_cosh_error_class(self, ddp, dist_sync_on_step, preds, target):
        num_outputs = 1 if preds.ndim == 2 else num_targets
        print(preds.shape)
        self.run_class_metric_test(
            ddp=ddp,
            dist_sync_on_step=dist_sync_on_step,
            preds=preds,
            target=target,
            metric_class=LogCoshError,
            sk_metric=sk_log_cosh_error,
            metric_args={"num_outputs": num_outputs},
        )

    def test_log_cosh_error_functional(self, preds, target):
        self.run_functional_metric_test(
            preds=preds,
            target=target,
            metric_functional=log_cosh_error,
            sk_metric=sk_log_cosh_error,
        )

    def test_log_cosh_error_differentiability(self, preds, target):
        num_outputs = 1 if preds.ndim == 2 else num_targets
        self.run_differentiability_test(
            preds=preds,
            target=target,
            metric_module=partial(LogCoshError, num_outputs=num_outputs),
            metric_functional=log_cosh_error,
        )
