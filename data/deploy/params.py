# -*- coding:utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class Config(object):
    pass


def read_params():
    cfg = Config()

    # params for text detector
    cfg.det_algorithm = "DB"
    cfg.det_model_dir = "./inference/det/"
    cfg.det_limit_side_len = 960
    cfg.det_limit_type = 'resize_long'

    # DB parmas
    cfg.det_db_thresh = 0.3
    cfg.det_db_box_thresh = 0.5
    cfg.det_db_unclip_ratio = 2.5
    cfg.use_dilation = False
    cfg.det_db_score_mode = "fast"

    # params for text recognizer
    cfg.rec_algorithm = "CRNN"
    cfg.rec_model_dir = "./inference/rec/"

    cfg.rec_image_shape = "3, 32, 320"
    cfg.rec_char_type = 'ch'
    cfg.rec_batch_num = 30
    cfg.max_text_length = 25
    cfg.rec_char_dict_path = "./deploy/ppocr_keys_bank.txt"
    cfg.use_space_char = False

    # params for text classifier
    cfg.use_angle_cls = False
    cfg.cls_model_dir = "./inference/cls/"
    cfg.cls_image_shape = "3, 48, 192"
    cfg.label_list = ['0', '180']
    cfg.cls_batch_num = 30
    cfg.cls_thresh = 0.9

    cfg.use_pdserving = False
    cfg.use_tensorrt = False
    cfg.drop_score = 0.7

    return cfg
