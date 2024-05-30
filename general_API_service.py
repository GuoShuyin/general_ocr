from flask import Flask, request, jsonify, make_response
import numpy as np
import cv2
import urllib.parse
import json
from general_ocr_API import id_ocr, fp_ocr, cp_ocr

API_service = Flask(__name__)

def get_specific_data(image, category, doc_type):
    if doc_type == '身份证':
        data = id_ocr(image)
    elif doc_type == '车牌':
        data = cp_ocr(image)
    elif doc_type == '发票':
        data = fp_ocr(image)
    else:
        return {'error': 'Invalid document type'}
    
    return {category: data.get(category, 'Category not found')}

@API_service.route('/ocr', methods=['POST'])
def ocr_endpoint():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    category = request.args.get('category', 'text')  # ??????,???'text'
    doc_type = request.args.get('type')  # ????????

    if not doc_type:
        return jsonify({'error': 'No document type provided'}), 400

    # Decode the category parameter assuming it is UTF-8 encoded
    category = category.encode('latin1').decode('utf-8')
    doc_type = doc_type.encode('latin1').decode('utf-8')
    print("Decoded category:", category)
    print("Decoded document type:", doc_type)

    image = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    result = get_specific_data(image, category, doc_type)
    print("OCR result:", result)
    
    response = make_response(json.dumps(result, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

if __name__ == '__main__':
    API_service.run(debug=True, host='0.0.0.0', port=5000)
