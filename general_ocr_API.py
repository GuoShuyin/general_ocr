import cv2
import numpy as np
import re
from paddleocr import PaddleOCR, PPStructure,save_structure_res
import pandas as pd
from bs4 import BeautifulSoup
import io
import xlsxwriter  # 导入 xlsxwriter 模块
from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes, convert_info_docx
import os
from docx import Document
import shutil
import sys
from contextlib import contextmanager
#from general_API_service import is_gpu
import common_func


from data.deploy import ocr_bank


# 确保 /app 和 /app/data 目录在 sys.path 中
app_path = "/app"
data_path = "/app/data"

if app_path not in sys.path:
    sys.path.insert(0, app_path)

if data_path not in sys.path:
    sys.path.insert(0, data_path)


from data.deploy import ocr_bank


gpu = True
#Initialize OCR for data types with text return values.
ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu = gpu)
print("gpu state", gpu)
def is_gpu(bool):
    gpu = bool

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

#calculate the average confidence of an ocr result 
def ocr_confidence(result):
    word_count = 0
    confidence_sum = 0
    for line in result[0]:
        confidence_sum += line[1][1]
        word_count += 1
    average_confidence = confidence_sum / word_count
    return average_confidence


#convert a pdf/image form document into docx form
def doc_ocr_helper(imgs):
    doc_paths = []
    img_paths = []
    folder_paths = []
    for i in range(len(imgs)):
        # Convert PIL image to NumPy array
        img_np = np.array(imgs[i])
        
        # Convert RGB (PIL) to BGR (OpenCV)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
       
        img_path = f'/tmp/{i}.jpg' 
        img_paths.append(img_path)
        folder_paths.append(f'/tmp/{i}')
        # Save the image in a temporary folder
        cv2.imwrite(img_path, img_bgr)
        doc_ocr(img_path, is_en = True)
        doc_paths.append(f'/tmp/{i}_ocr.docx')
    for i, doc_path in enumerate(doc_paths):
        if i > 0:
            merge_docx_files(doc_paths[0], doc_path, doc_paths[0])
        else:
            continue
    #delete all the temporary files in the temporary folder
    with open(doc_paths[0], 'rb') as f:
        docx_stream = io.BytesIO(f.read())
        for i in range(len(doc_paths)):
            os.remove(doc_paths[i])
            os.remove(img_paths[i])
            if os.path.exists(folder_paths[i]) and os.path.isdir(folder_paths[i]):
                try:
                    # recursively delete all the non-empty folders
                    shutil.rmtree(folder_paths[i])
                    print(f"非空文件夹 '{folder_paths[i]}' 及其内容已成功删除。")
                except Exception as e:
                    print(f"删除文件夹时出错: {e}")
        # return io.BytesIO instance
        return docx_stream


def doc_ocr(img_path, is_en = True):
    print("document_recognition")

    if is_en:
        # for English doc
        table_engine = PPStructure(recovery=True, lang='en', use_gpu = gpu)
    else:
        # for Chinese doc
        table_engine = PPStructure(recovery=True, use_gpu = gpu)

    save_folder = '/tmp'
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
        doc_ocr(img_path, is_en = False)
        print("chinese")
        return

    h, w, _ = img.shape
    res = sorted_layout_boxes(result, w)
    print("saved")
    try:
        convert_info_docx(img, res, save_folder, os.path.basename(img_path).split('.')[0])
    except IndexError:
        print("Index out of bounds")



def merge_docx_files(source_file1, source_file2, output_file):
    #open the first document
    doc1 = Document(source_file1)

    #open the second document
    doc2 = Document(source_file2)

    # Add the content of the second document to the end of the first document.
    for element in doc2.element.body:
        doc1.element.body.append(element)
    
    # save the merged document
    doc1.save(output_file)


def excel_ocr(img):
    if img is None:
        print("Failed to load image")
        return None

    # Initialize PP-Structure for table recognition
    table_engine = PPStructure(recovery=True, lang='ch',use_gpu = gpu)

    # Perform table recognition
    result = table_engine(img)

    # Check if the table was recognized
    for item in result:
        if item['type'] == 'table':
            html_content = item['res']['html']
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            df = pd.read_html(str(table))[0]

            # Save the DataFrame to an Excel file in memory
            output = io.BytesIO()  # use io.BytesIO() to create an in-memory binary stream.
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False)
            writer.save()
            output.seek(0)  # Move the pointer to the beginning of the stream
            return output

    return None

#bank card ocr recognition
def bc_ocr(img):
    dic = {}
    
    img_path = f'/tmp/1.jpg'  
    cv2.imwrite(img_path, img)

    args = {
        "use_gpu": gpu,
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

    dic['文件名'] = ''
    with change_working_directory('/app/data'):
        print("Changed Directory:", os.getcwd())
        ocr_b = ocr_bank.OCRBank(args=args)
        print("initialization complete")
        print(img_path)
        tmp_dic = ocr_b.predict(None, img_path)
        dic["银行卡号"] = tmp_dic['bank_card_number']
        dic['银行名称'] = tmp_dic['bank_name']
        dic['卡类型'] = tmp_dic['card_type']
        print(dic)

    print("Restored Directory:", os.getcwd())
    os.remove(img_path)

    return dic
    


@contextmanager
def change_working_directory(new_dir):
    original_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        yield
    finally:
        os.chdir(original_dir)



#invoice ocr recognition
def fp_ocr(image):
    corrected_image, angle = correct_image_orientation_twice(image)
    #TODO
    corrected_image = process_image(corrected_image)
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

#car plate ocr recognition
def cp_ocr(image):
    corrected_image, angle = image, 0
    result = ocr.ocr(corrected_image, cls=True)
    confidence = ocr_confidence(result)
    if confidence < 0.96:
        corrected_image = rotate_image(corrected_image, 180)
        result = ocr.ocr(corrected_image, cls=True)
    
    txts = [line[1][0] for line in result[0]]
    for i in range(len(txts)):
        txts[i] = txts[i].replace(" ", "")
    dic = {}
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
            break
    return dic

#identification card ocr recognition 
def id_ocr(image):
    corrected_image, angle = image, 0
    corrected_image = process_image(corrected_image)
    result = ocr.ocr(corrected_image, cls=True)
    txts = [line[1][0] for line in result[0]]
    for i in range(len(txts)):
        txts[i] = txts[i].replace(" ", "")
    dic = {}
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
            print(txts)
        if i == 5:
            print('识别失败：{}'.format("name"))
        else:
           
            # Remove the spaces from each element and merge them into a single string.
            text = ''.join([txt.replace(" ", "") for txt in txts])
            print(text)
            print(txts)

            #dictionary words
            keys = ["姓名", "性别", "民族", "出生", "住址", "公民身份号码"]
            

            # extract useful information from the text
            for i, key in enumerate(keys):
                start_index = text.find(key) + len(key)
                if i < len(keys) - 1:
                    end_index = text.find(keys[i + 1])
                else:
                    end_index = len(text)
                dic[key] = str(text[start_index:end_index].strip())
            
            
            
            #Further process the date of birth
            birth_date = dic['出生']
            birth_date_parts = re.findall(r'\d+', birth_date)
            if len(birth_date_parts) == 3:
                dic['出生年月日'] = f"{birth_date_parts[0]}年{birth_date_parts[1]}月{birth_date_parts[2]}日"
            else:
                dic['出生年月日'] = birth_date

            #Remove the original birth field
            del dic['出生']
            
    return dic

def is_date(date_string):
    pattern = r'^\d{4}\.\d{2}\.\d{2}-\d{4}\.\d{2}\.\d{2}$'
    if re.match(pattern, date_string):
        return True
    else:
        return False
    
# image pre processing
def process_image(image):
    # Convert the image to a grayscale image
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Create a sharpening filter
    kernel = np.array([[0, -1, 0],
                    [-1, 5,-1],
                    [0, -1, 0]])

    # apply the sharpening filter onto the image
    sharpened_image = cv2.filter2D(gray_image, -1, kernel)

    # create a CLAHE instance
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    #apply CLAHE to increase the image's contrast
    contrast_image = clahe.apply(sharpened_image)

    # adjust contrast and brightness
    alpha = 1.5  # contrast control (1.0-3.0)
    beta = -50   # brightness control (-100 to 100)

    adjusted_image = cv2.convertScaleAbs(contrast_image, alpha=alpha, beta=beta)
    return adjusted_image