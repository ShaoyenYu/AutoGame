import numpy as np
import paddle
from paddleocr.ppocr.postprocess.rec_postprocess import AttnLabelDecode


class CustomAttnLabelDecode(AttnLabelDecode):
    """ Convert between text-label and text-index """

    def __init__(self, character_dict_path=None, use_space_char=False, **kwargs):
        super(CustomAttnLabelDecode, self).__init__(character_dict_path, use_space_char, **kwargs)
        self.valid_chars, self.valid_char_idx = "", {}
        self.set_valid_chars(kwargs.get("valid_chars", ""))

    def set_valid_chars(self, valid_chars: str):
        self.valid_chars = [*valid_chars]
        self.valid_chars = self.add_special_char(self.valid_chars)
        self.valid_char_idx = {c: self.dict[c] for c in self.valid_chars}

    def __call__(self, preds, label=None, *args, **kwargs):
        """
        text = self.decode(text)
        if label is None:
            return text
        else:
            label = self.decode(label, is_remove_duplicate=False)
            return text, label
        """
        if isinstance(preds, paddle.Tensor):
            preds = preds.numpy()

        # hack this part to implement custom valid characters, see the original implementation below:

        # preds_idx = preds.argmax(axis=2)
        # preds_prob = preds.max(axis=2)
        # text = self.decode(preds_idx, preds_prob, is_remove_duplicate=False)

        nd = np.array([0, *sorted(self.valid_char_idx.values())[1:-1]])  # zero is the default value for unmatched char
        # find index of character which has the max prediction confidence in the **subset** of the original characters
        # then map the index of char in subset, with its index in the original char dict
        sub_preds_idx = preds[:, :, nd].argmax(axis=2)
        sub_preds_idx = np.apply_along_axis(lambda x: nd[x], arr=sub_preds_idx, axis=1)
        # and get the prediction confidence
        sub_preds_prob = preds[:, :, nd].max(axis=2)

        text = self.decode(sub_preds_idx, sub_preds_prob, is_remove_duplicate=False)

        if label is None:
            return text
        label = self.decode(label, is_remove_duplicate=False)
        return text, label
