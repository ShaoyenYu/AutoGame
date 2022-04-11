from paddleocr.ppocr.postprocess import *

from lib.dummy_paddleocr.postprocess.rec_postprocess import CustomAttnLabelDecode


def build_custom_post_process(config, global_config=None):
    module_name = config.get("name")
    try:
        return build_post_process(config, global_config)
    except Exception:
        custom_support_dict = ["CustomAttnLabelDecode", ]
        assert module_name in custom_support_dict, Exception(f"custom post process only support {module_name}")
        module_class = eval(module_name)(**config)
        return module_class
