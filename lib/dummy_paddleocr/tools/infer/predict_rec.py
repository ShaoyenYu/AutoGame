from paddleocr.tools.infer.predict_rec import TextRecognizer

from lib.dummy_paddleocr.postprocess import build_custom_post_process


class CustomTextRecognizer(TextRecognizer):
    def __init__(self, args, **kwargs):
        super().__init__(args)
        valid_chars = kwargs.get("valid_chars", "")

        if self.rec_algorithm == "RARE":
            postprocess_params = {
                'name': 'CustomAttnLabelDecode',
                "character_dict_path": args.rec_char_dict_path,
                "use_space_char": args.use_space_char,
                "valid_chars": valid_chars
            }
            self.postprocess_op = build_custom_post_process(postprocess_params)

    def set_valid_chars(self, chars: str):
        self.postprocess_op.set_valid_chars(chars)

    def __call__(self, img_list):
        if not isinstance(img_list, list):
            img_list = [img_list]
        return super().__call__(img_list)[0]
