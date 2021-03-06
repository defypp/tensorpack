# -*- coding: UTF-8 -*-
# File: dump.py
# Author: Yuxin Wu <ppwwyyxx@gmail.com>

import os
import numpy as np

from .base import Callback
from ..utils import logger
from ..tfutils import get_op_tensor_name

__all__ = ['DumpParamAsImage']


class DumpParamAsImage(Callback):
    """
    Dump a tensor to image(s) to ``logger.LOG_DIR`` after every epoch.

    Note that it requires the tensor is directly evaluable, i.e. either inputs
    are not its dependency (e.g. the weights of the model), or the inputs are
    feedfree (in which case this callback will take an extra datapoint from
    the input pipeline).
    """

    def __init__(self, tensor_name, prefix=None, map_func=None, scale=255):
        """
        Args:
            tensor_name (str): the name of the tensor.
            prefix (str): the filename prefix for saved images. Defaults to the Op name.
            map_func: map the value of the tensor to an image or list of
                 images of shape [h, w] or [h, w, c]. If None, will use identity.
            scale (float): a multiplier on pixel values, applied after map_func.
        """
        op_name, self.tensor_name = get_op_tensor_name(tensor_name)
        self.func = map_func
        if prefix is None:
            self.prefix = op_name
        else:
            self.prefix = prefix
        self.log_dir = logger.LOG_DIR
        self.scale = scale

    def _before_train(self):
        # TODO might not work for multiGPU?
        self._tensor = self.graph.get_tensor_by_name(self.tensor_name)

    def _trigger(self):
        val = self.trainer.sess.run(self._tensor)
        if self.func is not None:
            val = self.func(val)
        if isinstance(val, list) or val.ndim == 4:
            for idx, im in enumerate(val):
                self._dump_image(im, idx)
        else:
            self._dump_image(val)
        self.trainer.monitors.put_image(self.prefix, val)

    def _dump_image(self, im, idx=None):
        assert im.ndim in [2, 3], str(im.ndim)
        fname = os.path.join(
            self.log_dir,
            self.prefix + '-ep{:03d}{}.png'.format(
                self.epoch_num, '-' + str(idx) if idx else ''))
        res = im * self.scale
        res = np.clip(res, 0, 255)
        cv2.imwrite(fname, res.astype('uint8'))


try:
    import cv2
except ImportError:
    from ..utils.develop import create_dummy_class
    DumpParamAsImage = create_dummy_class('DumpParamAsImage', 'cv2')  # noqa
