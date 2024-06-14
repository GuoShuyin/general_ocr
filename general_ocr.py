import math
import cv2
import numpy as np
import re
import os
import openpyxl
import pandas as pd
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from matplotlib import pyplot as plt
from table.predict_table import TableSystem,to_excel
from utility import init_args
from paddleocr import PPStructure, draw_structure_result
from paddleocr.ppstructure.table.tablepyxl import tablepyxl
from bs4 import BeautifulSoup
from PIL import Image
from paddleocr import PPStructure,save_structure_res
from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes, convert_info_docx
import logging
import paddleocr
import sys

from contextlib import contextmanager


# 确保 /app 和 /app/data 目录在 sys.path 中
app_path = "/app"
data_path = "/app/data"

if app_path not in sys.path:
    sys.path.insert(0, app_path)

if data_path not in sys.path:
    sys.path.insert(0, data_path)




from data.deploy import ocr_bank


# 确保 /app 和 /app/data 目录在 sys.path 中
app_path = "/app"
data_path = "/app/data"

if app_path not in sys.path:
    sys.path.insert(0, app_path)

if data_path not in sys.path:
    sys.path.insert(0, data_path)




from data.deploy import ocr_bank

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
    如果是PDF文件，则将其转换为PNG格式
    """
    paths = []
    names = []
    for file in filelist:
        if file.lower().endswith('.pdf'):
            # 将PDF文件的所有页面转换为图像
            images = convert_from_path(file)
            if images:
                for i, img in enumerate(images):
                    # 保存每页图像
                    png_file = f"{file.replace('.pdf', '')}_{i + 1}.png"
                    img.save(png_file, 'PNG')
                    
                    # 添加路径和文件名到列表中
                    paths.append(png_file)
                    names.append(os.path.basename(png_file))
        elif any(file.lower().endswith(ft) for ft in file_types):
            paths.append(file)
            names.append(os.path.basename(file))

    return paths, names








def gocr(img_path, name, lang="ch"):
    dic = {}
    ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=True)

    print(paddleocr.__version__)
    logging.basicConfig(level=logging.INFO)

    if int(choice) < 4:
        # Correct image orientation
        if choice == '1':
            corrected_image, angle = correct_image_orientation_twice(img_path)
        elif choice == '2':
            corrected_image, angle = cv2.imread(img_path), 0
        elif choice == '3':
            corrected_image, angle = cv2.imread(img_path), 0

        result = ocr.ocr(corrected_image, cls=True)
        #result = ocr.ocr(img_path, cls=True)
        
        confidence = ocr_confidence(result)
        if confidence < 0.96:
            # Rotate the image 180 degrees and re-run OCR
            corrected_image = rotate_image(corrected_image, 180)
            result = ocr.ocr(corrected_image, cls=True)
        

        #锐化和灰度化处理
        corrected_image = process_image(corrected_image)
        # Save corrected image（just for tesing）
        corrected_image_path = img_path.replace('images', 'corrected_images')
        cv2.imwrite(corrected_image_path, corrected_image)

        
        txts = [line[1][0] for line in result[0]]  # 确保从结果的正确层级提取文本
        
    
    
        if choice == '1':
            return invoice_recognition(txts, dic, name)
        elif choice == '2':
            return id_card_recognition(txts, dic, name, ocr, corrected_image) 
        elif choice == '3':
            return license_plate_recognition(txts, dic, name)
    elif choice == '4':
        table_recognition(img_path)
        return dic 
    elif choice == '5':
        document_recognition(img_path)
        return dic
    elif choice == '6':
        return bank_card_recognition(img_path, dic, name)


def bank_card_recognition(img_path, dic, name):
    
    img = cv2.imread(img_path)
    #img = process_bank_card_image(img)

    args = {
        "use_gpu": False,
        "enable_mkldnn": True
    }



    original_paths = sys.path
    paths = [
    "/app/data",
    "/app/data",
    "/app/data",
    "/app/data",
    "/app/data",
    "/app/data/deploy",
    "/usr/local/lib/python37.zip",
    "/usr/local/lib/python3.7",
    "/usr/local/lib/python3.7/lib-dynload",
    "/usr/local/lib/python3.7/site-packages",
    "/app/data/tools/infer",
    "/app/data/tools/infer",
    "/app/data/tools/infer",
    "/app/data/tools/infer"
    ]
    sys.path = paths
    #sys.path = move_b_to_first(sys.path, '/app/data')
    # for element in sys.path:
    #     print(element)

    print("Original Directory:", os.getcwd())

    dic['文件名'] = name
    with change_working_directory('/app/data'):
        print("Changed Directory:", os.getcwd())
        # 在新目录中执行你的代码
        ocr_b = ocr_bank.OCRBank(args=args)
        print("initialization complete")
        print(img_path)
        tmp_dic = ocr_b.predict(None, img_path)
        dic["银行卡号"] = tmp_dic['bank_card_number']
        dic['银行名称'] = tmp_dic['bank_name']
        dic['卡类型'] = tmp_dic['card_type']
        print(dic)

    print("Restored Directory:", os.getcwd())

    return dic
    

    
    
# def move_b_to_first(arr, b):
#     # 找到等于 b 的元素的索引
#     try:
#         b_index = arr.index(b)
#     except ValueError:
#         # 如果没有找到等于 b 的元素，返回原数组
#         return arr
    
#     # 移动等于 b 的元素到第一位
#     b_element = arr.pop(b_index)
#     arr.insert(0, b_element)
    
#     return arr

@contextmanager
def change_working_directory(new_dir):
    original_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        yield
    finally:
        os.chdir(original_dir)


# def process_bank_card_image(image):
#     gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

#     # 使用Canny边缘检测算法识别卡号边缘
#     edges = cv2.Canny(gray_image, 100, 200)

#     # 使用形态学操作填充边缘
#     kernel = np.ones((3, 3), np.uint8)
#     dilated_edges = cv2.dilate(edges, kernel, iterations=1)
#     filled_edges = cv2.morphologyEx(dilated_edges, cv2.MORPH_CLOSE, kernel)

#     # 手动选择银行卡号区域（此处假设银行卡号位于图像的中间部分）
#     mask = np.zeros_like(gray_image)
#     h, w = gray_image.shape
#     mask[int(h*0.4):int(h*0.6), int(w*0.2):int(w*0.8)] = 255

#     # 使用掩膜增强对比度
#     alpha = 0.5  # 对比度控制 (1.0-3.0)
#     beta = 0     # 亮度控制 (0-100)
#     enhanced_image = cv2.convertScaleAbs(gray_image, alpha=alpha, beta=beta)

#     # 将掩膜应用到原始灰度图像上
#     enhanced_part = cv2.bitwise_and(enhanced_image, enhanced_image, mask=mask)
#     final_image = cv2.addWeighted(gray_image, 1, enhanced_part, 1, 0)
#     return final_image

def document_recognition(img_path, is_en = True):
    print("document_recognition")

    if is_en:
        # 英文测试图
        table_engine = PPStructure(recovery=True, lang='en')
    else:
        # 中文测试图
        table_engine = PPStructure(recovery=True)

    save_folder = './images/recovered_documents'
    img = cv2.imread(img_path)
    result = table_engine(img)
    save_structure_res(result, save_folder, os.path.basename(img_path).split('.')[0])

    total_confidence = 0
    count = 0
    print(len(result))
    for line in result:
        line.pop('img')
        if 'res' in line:
            for res_item in line['res']:
                if 'confidence' in res_item:
                    total_confidence += res_item['confidence']
                    count += 1
    print(result)
    if count > 0:
        average_confidence = total_confidence / count
        print("Average Confidence:", average_confidence)
    else:
        print("No confidence values found.")
        

    if (count <= 0 or average_confidence < 0.7) and is_en != False:
        document_recognition(img_path, is_en = False)
        print("chinese")
        return

    h, w, _ = img.shape
    res = sorted_layout_boxes(result, w)
    print("saved")
    try:
        convert_info_docx(img, res, save_folder, os.path.basename(img_path).split('.')[0])
    except IndexError:
        print("Index out of bounds")




def table_recognition(img_path):
    # Load the image
    img = cv2.imread(img_path)
    if img is None:
        print("Failed to load image")
        return

    # Initialize PP-Structure for table recognition
    table_engine = PPStructure(recovery=True, lang='ch')

    # Perform table recognition
    result = table_engine(img)

    # Debugging: Print the result to understand its structure
    #print("Recognition result:", result)

    # Ensure the output directory exists
    output_dir = 'images'
    os.makedirs(output_dir, exist_ok=True)

    # Extract the base name of the image file
    base_name = os.path.splitext(os.path.basename(img_path))[0]

    # Save the recognized table to an Excel file directly in the images directory
    for item in result:
        if item['type'] == 'table':
            html_content = item['res']['html']
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            df = pd.read_html(str(table))[0]
            excel_path = os.path.join(output_dir, f"{base_name}_table.xlsx")
            df.to_excel(excel_path, index=False)
            print(f"Table saved to {excel_path}")

    # Check if files are saved correctly
    saved_files = os.listdir(output_dir)
    if saved_files:
        print(f"Files saved in {output_dir}: {saved_files}")
    else:
        print(f"No files saved in {output_dir}. Please check the save process.")

    print(f"Saved to {output_dir} successfully")





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
        

def process_image(image):
    # 将图像转换为灰度图像
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 创建锐化滤波器
    kernel = np.array([[0, -1, 0],
                    [-1, 5,-1],
                    [0, -1, 0]])

    # 应用锐化滤波器
    sharpened_image = cv2.filter2D(gray_image, -1, kernel)

    # 创建CLAHE对象
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    # 应用CLAHE增强对比度
    contrast_image = clahe.apply(sharpened_image)

    # 调整对比度和亮度
    alpha = 1.5  # 对比度控制 (1.0-3.0)
    beta = -50   # 亮度控制 (-100 to 100)

    adjusted_image = cv2.convertScaleAbs(contrast_image, alpha=alpha, beta=beta)
    return adjusted_image

        
def license_plate_recognition(txts, dic, name):  
    provinces = ["皖", "沪", "津", "渝", "冀", "晋", "蒙", "辽", "吉", "黑", "苏", "浙", "京", "闽", "赣", "鲁", "豫", "鄂", "湘", "粤", "桂", "琼", "川", "贵", "云", "藏", "陕", "甘", "青", "宁", "新", "警", "学"]
    specials  =  ["WJ", "军","警","使", "领"]
    alphabets = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W','X', 'Y', 'Z', 'O'] 
    for i in range(len(txts)):
        item = txts[i]
        if any(province in item for province in provinces) and any(alphabet in item for alphabet in alphabets) or any(special in item for special in specials) and any(alphabet in item for alphabet in alphabets):
            if len(item) < 4:
                if i+1 in range(len(txts)):
                    item = item + txts[i+1]
                else:
                    item = item + txts[i-1]
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

def process_files(rootDir, file_types=['jpg', 'png','pdf'], lang="ch"):

    #输出cv2图片测试
    if not os.path.exists('corrected_images'):
        os.makedirs('corrected_images')



    filelist = get_filelist(rootDir, [])
    paths, names = get_files(filelist, file_types)
    data = []
    for n in range(len(paths)):
        if not paths[n].lower().endswith('.pdf'):
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
    print("4. 表格识别")
    print("5. 文档识别")
    print("6. 银行卡识别")
    make_choice = False
    while not make_choice:
        choice = input("请输入1~5中的一个数: ")
        if choice != '1' and choice != '2' and choice != '3' and choice != '4' and choice != '5' and choice != '6':
            print("无效输入，请输入1~6中的一个数")
        else:
            make_choice = True
    process_files(rootDir, ['jpg', 'png','pdf'], lang="ch")

