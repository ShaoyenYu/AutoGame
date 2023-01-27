from argparse import Namespace
from pathlib import Path

import paddleocr

from lib.dummy_paddleocr.tools.infer.predict_rec import CustomTextRecognizer

DIR_PROJECT = Path(__file__).parent.parent.parent
DIR_PADDLEOCR = Path(paddleocr.__file__).parent


def prepare_default_args(lang="chinese_cht", rec_algo="RARE") -> Namespace:
    if lang == "chinese_cht":
        det_model_dir = f"{DIR_PROJECT}/lib/dummy_paddleocr/inferences/chinese_cht/ch_ppocr_mobile_v3.0_det_infer"
        rec_model_dir = f"{DIR_PROJECT}/lib/dummy_paddleocr/inferences/chinese_cht/ch_ppocr_mobile_v3.0_rec_infer"
        cls_model_dir = f"{DIR_PROJECT}/lib/dummy_paddleocr/inferences/chinese_cht/ch_ppocr_mobile_v2.0_cls_infer"

        rec_char_dict_path = f"{DIR_PADDLEOCR}/ppocr/utils/dict/chinese_cht_dict.txt"
        vis_font_path = f"{DIR_PADDLEOCR}/doc/fonts/simfang.ttf"
        e2e_char_dict_path = f'{DIR_PADDLEOCR}/ppocr/utils/ic15_dict.txt'

        default_text_recognizer_args = Namespace(
            use_gpu=False, use_npu=False, use_xpu=False, ir_optim=True, use_tensorrt=False, min_subgraph_size=15, precision='fp32', gpu_mem=500,
            det_model_dir=det_model_dir,
            det_algorithm='DB',
            det_limit_side_len=960, det_limit_type='max', det_db_thresh=0.3, det_db_box_thresh=0.6,
            det_db_unclip_ratio=1.5, max_batch_size=10, use_dilation=False, det_db_score_mode='fast',
            det_east_score_thresh=0.8, det_east_cover_thresh=0.1, det_east_nms_thresh=0.2, det_sast_score_thresh=0.5,
            det_sast_nms_thresh=0.2, det_sast_polygon=False, det_pse_thresh=0, det_pse_box_thresh=0.85,
            det_pse_min_area=16, det_pse_box_type='box', det_pse_scale=1,

            rec_model_dir=rec_model_dir,
            rec_algorithm=rec_algo,
            rec_char_dict_path=rec_char_dict_path, use_space_char=True,
            rec_image_shape='3, 32, 320', rec_batch_num=6, max_text_length=25,

            vis_font_path=vis_font_path, drop_score=0.5, e2e_algorithm='PGNet',
            e2e_model_dir=None,
            e2e_limit_side_len=768, e2e_limit_type='max', e2e_pgnet_score_thresh=0.5,
            e2e_char_dict_path=e2e_char_dict_path, e2e_pgnet_valid_set='totaltext',
            e2e_pgnet_mode='fast',

            cls_model_dir=cls_model_dir,
            use_angle_cls=False, cls_image_shape='3, 48, 192', label_list=['0', '180'], cls_batch_num=6, cls_thresh=0.9,
            enable_mkldnn=False, cpu_threads=10, use_pdserving=False, warmup=False,
            draw_img_save_dir='./inference_results', save_crop_res=False, use_mp=False,
            total_process_num=1, process_id=0, benchmark=False, show_log=True, use_onnx=False,

        )
    else:
        raise NotImplementedError
    return default_text_recognizer_args


def load_recognizer():
    args = prepare_default_args(lang="chinese_cht", rec_algo="RARE")
    return CustomTextRecognizer(args)
