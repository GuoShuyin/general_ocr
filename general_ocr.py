import math
import cv2
import numpy as np
import re
import os
import openpyxl
import pandas as pd
from paddleocr import PaddleOCR
#import dlib
#from mtcnn import MTCNN

choice = 0
#发票的预处理旋转
def rotate_image(image, angle):
    """
    Rotate the image by the specified angle without losing any part of the image.
    """
    (h, w) = image.shape[:2]
    center = (w / 2, h / 2)
    
    # Calculate the new bounding dimensions of the image
    new_w = int(w * abs(np.cos(np.radians(angle))) + h * abs(np.sin(np.radians(angle))))
    new_h = int(h * abs(np.cos(np.radians(angle))) + w * abs(np.sin(np.radians(angle))))
    
    # Adjust the rotation matrix to take into account the new dimensions
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    rotated = cv2.warpAffine(image, M, (new_w, new_h))
    return rotated

def correct_image_orientation(image):
    """
    Correct the orientation of the image.
    """
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

def correct_image_orientation_twice(image_path):
    """
    Correct the image orientation twice for better accuracy.
    """
    image = cv2.imread(image_path)
    image, angle1 = correct_image_orientation(image)
    corrected_image, angle2 = correct_image_orientation(image)
    return corrected_image, angle1 + angle2




#身份证的预处理旋转






def get_filelist(dir, Filelist):
    """
    获取目录下所有文件的路径
    """
    newDir = dir
    if os.path.isfile(dir):
        Filelist.append(dir)
    elif os.path.isdir(dir):
        for s in os.listdir(dir):
            newDir = os.path.join(dir, s)
            get_filelist(newDir, Filelist)
    return Filelist

def get_files(filelist, file_types):
    """
    根据文件类型过滤文件，返回文件路径和文件名
    """
    paths = []
    names = []
    for file in filelist:
        if any(file.lower().endswith(ft) for ft in file_types):
            paths.append(file)
            names.append(os.path.basename(file))
    return paths, names








def gocr(img_path, name, lang="ch"):
    dic = {}
    ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=True)



    # Correct image orientation
    if choice == '1':
      corrected_image, angle = correct_image_orientation_twice(img_path)
    elif choice == '2':
      corrected_image, angle = cv2.imread(img_path), 0
    else:
      corrected_image, angle = cv2.imread(img_path), 0


    result = ocr.ocr(corrected_image, cls=True)
    #result = ocr.ocr(img_path, cls=True)
    
    confidence = ocr_confidence(result)
    if confidence < 0.96:
        # Rotate the image 180 degrees and re-run OCR
        corrected_image = rotate_image(corrected_image, 180)
        result = ocr.ocr(corrected_image, cls=True)
    

    # Save corrected image（just for tesing）
    corrected_image_path = img_path.replace('images', 'corrected_images')
    cv2.imwrite(corrected_image_path, corrected_image)

    
    txts = [line[1][0] for line in result[0]]  # 确保从结果的正确层级提取文本
    
    #TODO delete this print
    print(txts)
    


    
    if choice == '1':
        return invoice_recognition(txts, dic, name)
    elif choice == '2':
        return id_card_recognition(txts, dic, name, ocr, corrected_image) 
    elif choice == '3':
        return license_plate_recognition(txts, dic, name)
    

def id_card_recognition(txts, dic, name, ocr, image):
    is_front_cover = False
    if "中华人民共和国" in txts:
        is_front_cover = True
    if is_front_cover:
        for item in txts:
            if item != "居民身份证" and item != "中华人民共和国" and item != "签发机关" and item != "有效期限":
                if is_date(item):
                    dic['有效期限'] = item
                elif "有效期限" in item:
                    dic['有效期限'] = item[4:]
                elif "签发机关" in item:
                    dic['签发机关'] = item[4:]
                else:
                    dic['签发机关'] = item
    else:
        corrected_image = image
        i = 0
        while "姓名" not in txts[0] and i < 5:
            corrected_image = rotate_image(corrected_image, 90)
            result = ocr.ocr(corrected_image, cls=True)
            txts = [line[1][0] for line in result[0]]
            i += 1
        if i == 5:
            print('识别失败：{}'.format(name))
        else:
           
            # 去除每个元素中的空格并合并为一个字符串
            text = ''.join([txt.replace(" ", "") for txt in txts])
            print(text)

            # 关键字列表
            keys = ["姓名", "性别", "民族", "出生", "住址", "公民身份号码"]
            

            # 遍历关键字并提取信息
            for i, key in enumerate(keys):
                start_index = text.find(key) + len(key)
                if i < len(keys) - 1:
                    end_index = text.find(keys[i + 1])
                else:
                    end_index = len(text)
                dic[key] = str(text[start_index:end_index].strip())

            # 对出生日期进行进一步处理
            birth_date = dic['出生']
            birth_date_parts = re.findall(r'\d+', birth_date)
            if len(birth_date_parts) == 3:
                dic['出生年月日'] = f"{birth_date_parts[0]}年{birth_date_parts[1]}月{birth_date_parts[2]}日"
            else:
                dic['出生年月日'] = birth_date

            # 移除原始出生字段
            del dic['出生']
    return dic

def is_date(date_string):
    pattern = r'^\d{4}\.\d{2}\.\d{2}-\d{4}\.\d{2}\.\d{2}$'
    if re.match(pattern, date_string):
        return True
    else:
        return False
        



        
def license_plate_recognition(txts, dic, name):  
    provinces = ["皖", "沪", "津", "渝", "冀", "晋", "蒙", "辽", "吉", "黑", "苏", "浙", "京", "闽", "赣", "鲁", "豫", "鄂", "湘", "粤", "桂", "琼", "川", "贵", "云", "藏", "陕", "甘", "青", "宁", "新", "警", "学"]
    specials  =  ["WJ", "军","警","使", "领"]
    alphabets = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W','X', 'Y', 'Z', 'O'] 
    for i in range(len(txts)):
        item = txts[i]
        if any(province in item for province in provinces) and any(alphabet in item for alphabet in alphabets) or any(special in item for special in specials) and any(alphabet in item for alphabet in alphabets):
            if len(item) < 4:
                item = item + txts[i+1]
            print(item)
            dic['车牌号'] = item
            print('已识别完成：{}'.format(name))
            break
    return dic
    
    

def invoice_recognition(txts, dic, name):
    for i in range(len(txts)):
      txts[i] = txts[i].replace(" ","")
    text = ' '.join(txts)

    gongsi = re.findall(r'[一-龟]+公司|个人', text)
    gongsi = [g for g in gongsi if '银行' not in g]
    
    dic['文件名'] = name
    dic['发票代码'] = re.findall(r'\d{12}', text)[0] if re.findall(r'\d{12}', text) else ''
    dic['发票号码'] = re.findall(r'\d{8}', text)[0] if re.findall(r'\d{8}', text) else ''
    dic['开票日期'] = re.findall(r'[\d ]+年[\d ]+月[\d ]+日', text)[0] if re.findall(r'[\d ]+年[\d ]+月[\d ]+日', text) else ''
    dic['校验码'] = re.findall(r'[\d ]{20,30}', text)[0] if re.findall(r'[\d ]{20,30}', text) else ''
    dic['税率'] = re.findall(r'免税|不征税|1{0,1}[1369]%', text)[-1] if re.findall(r'免税|不征税|1{0,1}[1369]%', text) else ''
    dic['价税合计(小写)'] = re.findall(r'[¥|￥]{0,1}\d+\.\d+', text)[-1] if re.findall(r'[¥|￥]{0,1}\d+\.\d+', text) else ''
    dic['购买方名称'] = gongsi[0] if gongsi else ''
    dic['销售方名称'] = gongsi[-1] if gongsi else ''

    

    # 提取购买方和销售方纳税人识别号
    tax_ids = re.findall(r'\b[0-9A-Z]{15,18}\b', text)

    if len(tax_ids) > 0:
        dic['购买方纳税人识别号'] = f'"{tax_ids[0]}"'
    else:
        dic['购买方纳税人识别号'] = ''
    
    if len(tax_ids) > 1:
        dic['销售方纳税人识别号'] = f'"{tax_ids[1]}"'
    else:
        dic['销售方纳税人识别号'] = ''
	


    # 提取购买方和销售方开户行及账号
    bank_accounts = re.findall(r'[一-龟]+银行[一-龟\d]*[\dA-Z]*', text)
    #test
    print(bank_accounts)
    # 找到"售"和"销"字在文本中的位置
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
    
    print('已识别完成：{}'.format(name))
    return dic

def process_files(rootDir, file_types=['jpg', 'png'], lang="ch"):

    #输出cv2图片测试
    if not os.path.exists('corrected_images'):
        os.makedirs('corrected_images')



    filelist = get_filelist(rootDir, [])
    paths, names = get_files(filelist, file_types)
    data = []
    for n in range(len(paths)):
        dic = gocr(paths[n], names[n], lang)
        data.append(dic)
    
    # 使用 pandas 保存到 CSV
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(rootDir, "识别文字.csv"), index=False, encoding='utf-8-sig')

    
    print('一共识别完{}张图片'.format(len(paths)))
    print("谢谢使用本脚本:树荫", "\n")

#flip an image if it's ocr confidence is low    
def ocr_confidence(result):
    """
    输出OCR识别结果的置信度
    """
    word_count = 0
    confidence_sum = 0
    for line in result:
        for word_info in line:
            text = word_info[1][0]
            confidence_sum += word_info[1][1]
            word_count += 1
    ave_confidence = confidence_sum / word_count
    print("average_confidence" + str(ave_confidence))
    return ave_confidence
  

if __name__ == "__main__":
    rootDir = os.path.join(os.getcwd(), 'images')
        #ask what type of files are these
    print("请选择要进行的识别类型：")
    print("1. 发票识别")
    print("2. 身份证识别")
    print("3. 车牌识别")
    make_choice = False
    while not make_choice:
        choice = input("请输入1, 2或3: ")
        if choice != '1' and choice != '2' and choice != '3':
            print("无效输入，请输入1, 2或3")
        else:
            make_choice = True
    process_files(rootDir, ['jpg', 'png'], lang="ch")

