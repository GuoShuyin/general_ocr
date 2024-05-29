import cv2
import numpy as np
import re
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang="ch")

def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h))
    return rotated

def correct_image_orientation(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    if lines is not None:
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            angles.append(angle)
        median_angle = np.median(angles)
        rotated_image = rotate_image(image, median_angle)
        return rotated_image, median_angle
    else:
        return image, 0

def correct_image_orientation_twice(image):
    image, angle1 = correct_image_orientation(image)
    corrected_image, angle2 = correct_image_orientation(image)
    return corrected_image, angle1 + angle2

def ocr_confidence(result):
    word_count = 0
    confidence_sum = 0
    for line in result[0]:
        confidence_sum += line[1][1]
        word_count += 1
    average_confidence = confidence_sum / word_count
    return average_confidence

def fp_ocr(image):
    corrected_image, angle = correct_image_orientation_twice(image)
    result = ocr.ocr(corrected_image, cls=True)
    confidence = ocr_confidence(result)
    if confidence < 0.96:
        corrected_image = rotate_image(corrected_image, 180)
        result = ocr.ocr(corrected_image, cls=True)
    
    txts = [line[1][0] for line in result[0]]
    for i in range(len(txts)):
        txts[i] = txts[i].replace(" ", "")
    text = ' '.join(txts)

    dic = {}
    dic['text'] = text
    dic['confidence'] = confidence

    gongsi = re.findall(r'[一-龟]+公司|个人', text)
    gongsi = [g for g in gongsi if '银行' not in g]

    dic['文件名'] = ''
    dic['发票代码'] = re.findall(r'\d{12}', text)[0] if re.findall(r'\d{12}', text) else ''
    dic['发票号码'] = re.findall(r'\d{8}', text)[0] if re.findall(r'\d{8}', text) else ''
    dic['开票日期'] = re.findall(r'[\d ]+年[\d ]+月[\d ]+日', text)[0] if re.findall(r'[\d ]+年[\d ]+月[\d ]+日', text) else ''
    dic['校验码'] = re.findall(r'[\d ]{20,30}', text)[0] if re.findall(r'[\d ]{20,30}', text) else ''
    dic['税率'] = re.findall(r'免税|不征税|1{0,1}[1369]%', text)[-1] if re.findall(r'免税|不征税|1{0,1}[1369]%', text) else ''
    dic['价税合计(小写)'] = re.findall(r'[¥|￥]{0,1}\d+\.\d+', text)[-1] if re.findall(r'[¥|￥]{0,1}\d+\.\d+', text) else ''
    dic['购买方名称'] = gongsi[0] if gongsi else ''
    dic['销售方名称'] = gongsi[-1] if gongsi else ''

    tax_ids = re.findall(r'\b[0-9A-Z]{15,18}\b', text)
    dic['购买方纳税人识别号'] = f'"{tax_ids[0]}"' if len(tax_ids) > 0 else ''
    dic['销售方纳税人识别号'] = f'"{tax_ids[1]}"' if len(tax_ids) > 1 else ''

    bank_accounts = re.findall(r'[一-龟]+银行[一-龟\d]*[\dA-Z]*', text)
    shou_index = text.find('售')
    xiao_index = text.find('销')
    dic['购买方开户行及账号'] = ''
    dic['销售方开户行及账号'] = ''
    for account in bank_accounts:
        account_index = text.find(account)
        if (shou_index != -1 and account_index > shou_index) or (xiao_index != -1 and account_index > xiao_index):
            dic['销售方开户行及账号'] = account
        else:
            dic['购买方开户行及账号'] = account

    dic['开票日期'] = re.sub(r'年|月|日| ', '', dic['开票日期'])
    dic['校验码'] = dic['校验码'].replace(' ', '')

    return dic
