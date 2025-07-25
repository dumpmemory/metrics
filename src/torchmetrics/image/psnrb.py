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
from collections.abc import Sequence
from typing import Any, Optional, Union

import torch
from torch import Tensor, tensor

from torchmetrics.functional.image.psnrb import _psnrb_compute, _psnrb_update
from torchmetrics.metric import Metric
from torchmetrics.utilities.imports import _MATPLOTLIB_AVAILABLE
from torchmetrics.utilities.plot import _AX_TYPE, _PLOT_OUT_TYPE

if not _MATPLOTLIB_AVAILABLE:
    __doctest_skip__ = ["PeakSignalNoiseRatioWithBlockedEffect.plot"]


class PeakSignalNoiseRatioWithBlockedEffect(Metric):
    r"""Computes `Peak Signal to Noise Ratio With Blocked Effect`_ (PSNRB).

    .. math::
        \text{PSNRB}(I, J) = 10 * \log_{10} \left(\frac{\max(I)^2}{\text{MSE}(I, J)-\text{B}(I, J)}\right)

    Where :math:`\text{MSE}` denotes the `mean-squared-error`_ function. This metric is a modified version of PSNR that
    better supports evaluation of images with blocked artifacts, that oftens occur in compressed images.

    .. attention::
        Metric only supports grayscale images. If you have RGB images, please convert them to grayscale first.

    As input to ``forward`` and ``update`` the metric accepts the following input

    - ``preds`` (:class:`~torch.Tensor`): Predictions from model of shape ``(N,1,H,W)``
    - ``target`` (:class:`~torch.Tensor`): Ground truth values of shape ``(N,1,H,W)``

    As output of `forward` and `compute` the metric returns the following output

    - ``psnrb`` (:class:`~torch.Tensor`): float scalar tensor with aggregated PSNRB value

    Args:
        data_range: the range of the data. If a tuple is provided then the range is calculated as the difference and
            input is clamped between the values.
        block_size: integer indication the block size
        kwargs: Additional keyword arguments, see :ref:`Metric kwargs` for more info.

    Example:
        >>> from torch import rand
        >>> metric = PeakSignalNoiseRatioWithBlockedEffect(data_range=1.0)
        >>> preds = rand(2, 1, 10, 10)
        >>> target = rand(2, 1, 10, 10)
        >>> metric(preds, target)
        tensor(7.2893)

    """

    is_differentiable: bool = True
    higher_is_better: bool = True
    full_state_update: bool = False

    sum_squared_error: Tensor
    total: Tensor
    bef: Tensor
    data_range: Tensor

    def __init__(
        self,
        data_range: Union[float, tuple[float, float]],
        block_size: int = 8,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not isinstance(block_size, int) and block_size < 1:
            raise ValueError("Argument ``block_size`` should be a positive integer")
        self.block_size = block_size

        self.add_state("sum_squared_error", default=tensor(0.0), dist_reduce_fx="sum")
        self.add_state("total", default=tensor(0), dist_reduce_fx="sum")
        self.add_state("bef", default=tensor(0.0), dist_reduce_fx="sum")

        if isinstance(data_range, tuple):
            self.add_state("data_range", default=tensor(data_range[1] - data_range[0]), dist_reduce_fx="mean")
            self.clamping_fn = lambda x: torch.clamp(x, min=data_range[0], max=data_range[1])
        else:
            self.add_state("data_range", default=tensor(float(data_range)), dist_reduce_fx="mean")
            self.clamping_fn = None  # type: ignore[assignment]

    def update(self, preds: Tensor, target: Tensor) -> None:
        """Update state with predictions and targets."""
        if self.clamping_fn is not None:
            preds = self.clamping_fn(preds)
            target = self.clamping_fn(target)

        sum_squared_error, bef, num_obs = _psnrb_update(preds, target, block_size=self.block_size)
        self.sum_squared_error += sum_squared_error
        self.bef += bef
        self.total += num_obs

    def compute(self) -> Tensor:
        """Compute peak signal-to-noise ratio over state."""
        return _psnrb_compute(self.sum_squared_error, self.bef, self.total, self.data_range)

    def plot(
        self, val: Optional[Union[Tensor, Sequence[Tensor]]] = None, ax: Optional[_AX_TYPE] = None
    ) -> _PLOT_OUT_TYPE:
        """Plot a single or multiple values from the metric.

        Args:
            val: Either a single result from calling `metric.forward` or `metric.compute` or a list of these results.
                If no value is provided, will automatically call `metric.compute` and plot that result.
            ax: An matplotlib axis object. If provided will add plot to that axis

        Returns:
            Figure and Axes object

        Raises:
            ModuleNotFoundError:
                If `matplotlib` is not installed

        .. plot::
            :scale: 75

            >>> # Example plotting a single value
            >>> import torch
            >>> from torchmetrics.image import PeakSignalNoiseRatioWithBlockedEffect
            >>> metric = PeakSignalNoiseRatioWithBlockedEffect(data_range=1.0)
            >>> metric.update(torch.rand(2, 1, 10, 10), torch.rand(2, 1, 10, 10))
            >>> fig_, ax_ = metric.plot()

        .. plot::
            :scale: 75

            >>> # Example plotting multiple values
            >>> import torch
            >>> from torchmetrics.image import PeakSignalNoiseRatioWithBlockedEffect
            >>> metric = PeakSignalNoiseRatioWithBlockedEffect(data_range=1.0)
            >>> values = [ ]
            >>> for _ in range(10):
            ...     values.append(metric(torch.rand(2, 1, 10, 10), torch.rand(2, 1, 10, 10)))
            >>> fig_, ax_ = metric.plot(values)

        """
        return self._plot(val, ax)
