from flask import Flask, request, jsonify, make_response, send_file
import numpy as np
import cv2
import urllib.parse
import json
from general_ocr_API import id_ocr, fp_ocr, cp_ocr, excel_ocr, doc_ocr, doc_ocr_helper, bc_ocr, is_gpu
from pdf2image import convert_from_bytes
import io


#translation of document types and categories to Chinese
trans = {
    "bank_card": "银行卡",
    "bank_card_number": "银行卡号",
    "bank_name": "银行名称",
    "card_type": "卡类型",
    "invoice": "发票",
    "license_plate": "车牌",
    "id_card": "身份证",
    "excel": "表格",
    "file_name": "文件名",
    "license_no": "车牌号",
    "name": "姓名",
    "invoice_code": "发票代码",
    "gender": "性别",
    "invoice_no": "发票号码",
    "ethnicity": "民族",
    "invoice_date": "开票日期",
    "birthdate": "出生年月日",
    "verification_code": "效验码",
    "address": "住址",
    "tax_rate": "税率",
    "id_number": "公民身份号码",
    "total_amount_with_tax": "价税合计(小写)",
    "issuing_authority": "签发机关",
    "buyer_taxpayer_identification_no": "购买方纳税人识别号",
    "validity_period": "有效期限",
    "seller_taxpayer_identification_no": "销售方纳税人识别号",
    "buyer_name": "购买方名称",
    "seller_name": "销售方名称",
    "buyer_bank_and_account_no": "购买方开户行及账户",
    "seller_bank_and_account_no": "销售方开户行及账户",
}





API_service = Flask(__name__)

# return text-based ocr result in dictionary form
def get_specific_data(image, category, doc_type):
    print("Document type inside get_specific_data:", doc_type)
    for k, v in trans.items():
        if v == doc_type:
           doc_type = k
    if doc_type == 'id_card':
        data = id_ocr(image)
    elif doc_type == 'license_plate':
        data = cp_ocr(image)
    elif doc_type == 'invoice':
        data = fp_ocr(image)
    elif doc_type == 'bank_card':
        data = bc_ocr(image)
    else:
        return {'error': 'Invalid document type'}
    
    #modify the category's value to english
    category_zh = ""
    for k, v in trans.items():
        if k == category:
           category_zh = v
        elif v == category:
            category_zh = category
            category = k


    #determine if all the dictionary values should be returned
    if len(category) == 0:
        new_dic = {}
        for k1, v1 in data.items():
            for k, v in trans.items():
                if v == k1:
                    new_dic[k] = v1
        return new_dic
    else:
        new_dic = {category:data.get(category_zh, {'error': 'Category not found'})}
        return new_dic
    



@API_service.route('/ocr', methods=['POST'])
def ocr_endpoint():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    #parameters transformed via API connection
    category = request.args.get('category', 'text') 
    doc_type = request.args.get('type')  
    use_gpu = request.args.get('use_gpu', 'false').lower() == 'true'
    is_gpu(use_gpu)
    if not doc_type:
        return jsonify({'error': 'No document type provided'}), 400

    try:
        # Decode the parameters assuming they are UTF-8 encoded
        category = category.encode('latin1').decode('utf-8')
        doc_type = doc_type.encode('latin1').decode('utf-8')
        print("Decoded category:", category)
        print("Decoded document type:", doc_type)
    except UnicodeDecodeError:
        return jsonify({'error': 'Error decoding parameters'}), 400

    try:
        if file.filename.lower().endswith('.pdf'):
            # Convert PDF to image
            pdf_bytes = file.read()
            images = convert_from_bytes(pdf_bytes)
            if images:
                image = np.array(images[0])
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # Convert from PIL to OpenCV format
            else:
                return jsonify({'error': 'Error converting PDF to image'}), 400
        else:
            # Process image file
            image = np.frombuffer(file.read(), np.uint8)
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400
    if doc_type == 'excel':
        excel_stream = excel_ocr(image)
        if excel_stream:
            return send_file(excel_stream, download_name="result_table.xlsx", as_attachment=True)
        else:
            return jsonify({"error": "Failed to process image"}), 500
    print("just before identifying doc type")
    
    # return file-based ocr result in dictionary form
    if doc_type == 'document':
        print("recognized doc_type")
        if file.filename.lower().endswith('.pdf'):
            doc_stream = doc_ocr_helper(images)
        else:
            images = []
            images.append(image)
            doc_stream = doc_ocr_helper(images)
        print(doc_stream)
        if doc_stream:
            print('file sent')
            return send_file(doc_stream, download_name="result_doc.docx", as_attachment=True)
        else:
            return jsonify({"error": "Failed to process image"}), 500
    
    result = get_specific_data(image, category, doc_type)
    print("OCR result:", result)
    
    response = make_response(json.dumps(result, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

if __name__ == '__main__':
    API_service.run(debug=True, host='0.0.0.0', port=5000)




