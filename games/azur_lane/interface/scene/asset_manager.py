import itertools
from functools import lru_cache
from typing import List, Tuple

import cv2
import numpy as np

from games.azur_lane.config import CONFIG_SCENE, DIR_BASE
from util.io import load_yaml


class AssetManager:
    ASSETS = load_yaml(CONFIG_SCENE)

    @staticmethod
    def recur_resolve(dict_, keys):
        res = None
        for key in keys:
            res = dict_ = dict_[key]
        return res

    @classmethod
    def resolve(cls, asset_name, asset_type=None):
        """

        Args:
            asset_name:
            asset_type: str, optional {"Eigen", "Image", "ImageRect", "ImageRect", "RelImageRect",}

        Returns:

        """
        res = cls.recur_resolve(cls.ASSETS, asset_name.split("."))
        if asset_type is None:
            return res
        return res[f"__{asset_type}"]

    @classmethod
    @lru_cache(maxsize=10)
    def rel_image_rect(cls, asset_name: str):
        return cls.resolve(asset_name, "RelImageRect")

    @classmethod
    def image(cls, asset_name: str):
        return cls.resolve(asset_name, "Image")

    @classmethod
    def image_rect(cls, asset_name: str):
        return cls.resolve(asset_name, "ImageRect")

    @classmethod
    def get_image_xywh(cls, asset_name):
        lt, rb = (point[:2] for point in cls.image_rect(asset_name))
        return lt[0], lt[1], rb[0] - lt[0], rb[1] - lt[1]

    @classmethod
    def rect(cls, asset_name: str) -> List:
        return cls.resolve(asset_name, "Rect")[:2]

    @classmethod
    def eigen(cls, asset_name: str) -> Tuple[int, int, int]:
        return cls.resolve(asset_name, "Eigen")

    @classmethod
    def eigens(cls, *objects):
        if isinstance(objects, str):
            objects = [objects]
        it = itertools.chain.from_iterable((cls.eigen(xy_rgb) for xy_rgb in objects))
        return np.asarray(list(it), dtype=np.int32)

    @classmethod
    @lru_cache(maxsize=10)
    def template(cls, asset_name: str):
        """

        Args:
            asset_name: str
                "/a/b/c", or "a.b.c"

        Returns:

        """
        file_path_relative = cls.image(asset_name) if not asset_name.startswith("/") else asset_name
        return cv2.imread(f"{DIR_BASE}{file_path_relative}")[:, :, ::-1]


am = AssetManager
