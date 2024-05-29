from flask import Flask, request, jsonify
import numpy as np
import cv2
from fpocr_API import fp_ocr

API_service = Flask(__name__)

def get_specific_data(image, category):
    data = fp_ocr(image)
    return {category: data.get(category, 'Category not found')}

@API_service.route('/ocr', methods=['POST'])
def ocr_endpoint():
    print(1)
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    print(2)
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    print(3)
    category = request.args.get('category', 'text')  # 获取类别参数，默认是'text'

    image = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    result = get_specific_data(image, category)
    return jsonify(result)

if __name__ == '__main__':
    print(4)
    API_service.run(debug=True)
    print(5)
