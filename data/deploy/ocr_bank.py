# -*- coding:utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import os
import sys

# 需要设置的起始路径
desired_path = "/app/data"

# 将所需路径添加到 sys.path 的开头
if desired_path not in sys.path:
    sys.path.insert(0, desired_path)
#sys.path.insert(0, ".")
print(sys.path)
import copy

import time

import cv2
import numpy as np

from tools.infer.predict_system import TextSystem
from tools.infer.utility import parse_args
from deploy.params import read_params

import requests


class OCRBank(object):

    def __init__(self, args):
        # for element in sys.path:
        #     print(element)
        """
        initialize with the necessary elements
        """
        cfg = self.merge_configs()

        cfg.use_gpu = args["use_gpu"]
        if cfg.use_gpu:
            try:
                _places = os.environ["CUDA_VISIBLE_DEVICES"]
                int(_places[0])
                print("use gpu: ", cfg.use_gpu)
                print("CUDA_VISIBLE_DEVICES: ", _places)
                cfg.gpu_mem = 8000
            except:
                raise RuntimeError(
                    "Environment Variable CUDA_VISIBLE_DEVICES is not set correctly. If you wanna use gpu, please set CUDA_VISIBLE_DEVICES via export CUDA_VISIBLE_DEVICES=cuda_device_id."
                )
        cfg.ir_optim = True
        cfg.enable_mkldnn = args["enable_mkldnn"]
        print("Current working directory:", os.getcwd())
        with open('./inference/bank.json', encoding="utf-8") as file:
            self.bank = json.load(file)
        self.text_sys = TextSystem(cfg)

    def merge_configs(self, ):
        # deafult cfg
        backup_argv = copy.deepcopy(sys.argv)
        sys.argv = sys.argv[:1]
        cfg = parse_args()

        update_cfg_map = vars(read_params())

        for key in update_cfg_map:
            cfg.__setattr__(key, update_cfg_map[key])

        sys.argv = copy.deepcopy(backup_argv)
        return cfg

    def read_images(self, paths=[]):
        images = []
        for img_path in paths:
            assert os.path.isfile(
                img_path), "The {} isn't a valid file.".format(img_path)
            img = self.read_image(img_path)
            images.append(img)
        return images

    def read_image(self, img_path):
        assert os.path.isfile(
            img_path), "The {} isn't a valid file.".format(img_path)
        img = cv2.imread(img_path)
        if img is None:
            return None
        return img

    def predict(self, image=None, path="", **kwargs):
        if image is not None:
            predicted_data = image
        elif path != "":
            predicted_data = self.read_image(path)
        else:
            raise TypeError("The input data is inconsistent with expectations.")
        dt_boxes, rec_res, _ = self.text_sys(predicted_data)

        dt_num = len(dt_boxes)
        if dt_num > 0:
            rec_res_final = dict()
            text, score = rec_res[0]
            rec_res_final.update({
                'bank_card_number': text,
                'score': float(score),
                'location': dt_boxes[0].astype(np.int).tolist()
            })

            url = "https://ccdcapi.alipay.com/validateAndCacheCardInfo.json?cardNo=" + rec_res_final[
                "bank_card_number"] + "&cardBinCheck=true"
            r = requests.get(url=url)
            res = r.json()
            if res["validated"]:
                card_types = {
                    "DC": "借记卡",
                    "CC": "信用卡",
                    "SCC": "准贷记卡",
                    "PC": "预付费卡"
                }
                if res["cardType"] in card_types:
                    card_type = card_types[res["cardType"]]
                else:
                    card_type = "未知卡类型【" + res["cardType"] + "】"

                if res["bank"] in self.bank:
                    bank_name = self.bank[res["bank"]]
                else:
                    bank_name = "未知银行"

                rec_res_final.update({
                    "card_type": card_type,
                    "bank_name": bank_name
                })
            else:
                rec_res_final.update({
                    "card_type": "未知卡类型",
                    "bank_name": "未知银行"
                })

            return rec_res_final
        else:
            return "nothing returned"

    def serving_method(self, image=None, **kwargs):
        if image is not None:
            image_decode = self.base64_to_cv2(image)
            return self.predict(image=image_decode, **kwargs)
        else:
            return ""

    def base64_to_cv2(self, b64str):
        import base64
        if ';base64,' in b64str:
            arr = b64str.split(',')
            b64str = arr[1]
        data = base64.b64decode(b64str.encode('utf8'))
        data = np.fromstring(data, np.uint8)
        data = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return data


if __name__ == '__main__':
    args = {
        "use_gpu": False,
        "enable_mkldnn": True
    }
    ocr_bank = OCRBank(args=args)
    print(ocr_bank.predict(None, "1.jpg"))
    

#python tools/infer/predict_det.py --det_algorithm="DB" --det_model_dir="./inference/det/" --image_dir="1.jpg" --use_gpu=False --det_db_unclip_ratio=2.5
