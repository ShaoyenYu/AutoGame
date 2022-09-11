from typing import Tuple, Any

import cv2
import numpy as np
from Levenshtein import ratio
from cv2 import TM_CCOEFF_NORMED, TM_SQDIFF, TM_SQDIFF_NORMED, TM_CCORR_NORMED
from matplotlib import pyplot as plt
from scipy.spatial import distance_matrix


def binarize(image: np.ndarray, thresh=127, maxval=255, type=cv2.THRESH_BINARY_INV):
    image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, image_bin = cv2.threshold(image_gray, thresh, maxval, type)
    return image_bin


def slice_image(image, redundant_pixel=5):
    left = image.argmin(axis=1)
    right = image[:, ::-1].argmin(axis=1)
    left = left[left > 0].min() - redundant_pixel
    right = image.shape[1] - right[right > 0].min() + redundant_pixel
    return image[:, left: right]


def debug_show(f):
    def wrapper(img_ori, img_tem, *args, **kwargs):
        locs = f(img_ori, img_tem, *args, **kwargs)

        img_cp = img_ori.copy()
        w, h = img_tem.shape[:2][::-1]
        for pt in locs:
            print(pt)
            cv2.rectangle(img_cp, tuple(pt), (pt[0] + w, pt[1] + h), (255, 0, 0), 5)
        plt.imshow(img_cp)
        plt.show()

        return locs

    return wrapper


def find_most_match(text, phrases):
    val_max = 0
    most_match = None
    for phrase in phrases:
        if (val_cur := ratio(text, phrase)) >= val_max:
            val_max = val_cur
            most_match = phrase
    return most_match, val_max


def combine_similar_points(points, threshold=50):
    points = np.array(points)
    points_sorted = points[np.lexsort((points[:, 1], points[:, 0]))]
    dm = distance_matrix(points_sorted, points_sorted)
    return points_sorted[np.unique((dm < threshold).argmax(axis=0))]


def match_multi_template(img_ori: np.ndarray, img_tem: np.ndarray, method=TM_CCOEFF_NORMED, thresh=.8, thresh_dedup=0):
    res = cv2.matchTemplate(img_ori, img_tem, method)
    if method in (TM_SQDIFF, TM_SQDIFF_NORMED):
        loc = np.where(res <= thresh)
    else:
        loc = np.where(res >= thresh)
    locs = np.array([loc[1], loc[0]]).T

    if thresh_dedup > 0 and len(locs) > 0:
        locs = combine_similar_points(locs, threshold=thresh_dedup)

    return list(locs)


def match_single_template(origin: np.ndarray, template: np.ndarray, method=TM_CCORR_NORMED, debug=True) -> Tuple[Any, Any, Any, Any]:
    result = cv2.matchTemplate(origin, template, method)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if debug:
        origin_copy = origin.copy()
        width, height = template.shape[:2][::-1]
        top_left = max_loc
        bottom_right = (top_left[0] + width, top_left[1] + height)
        cv2.rectangle(origin_copy, top_left, bottom_right, (255, 255, 255), 2)
        plt.imshow(origin_copy)
        plt.show()
    return min_val, max_val, min_loc, max_loc
