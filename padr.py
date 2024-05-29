import os
import cv2
import numpy as np
from paddleocr import PaddleOCR

# Initialize PaddleOCR with angle classification enabled
ocr = PaddleOCR(use_angle_cls=True, lang='ch')

# Function to correct the orientation of an image
def correct_orientation(image_path, save_path):
    image = cv2.imread(image_path)
    result = ocr.ocr(image_path, cls=True)
    angle = result[0][0][0][1]  # Extracting the angle from the result

    # Rotate the image based on the detected angle
    if angle == 90:
        rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        rotated = cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        rotated = image  # If the angle is 0 or any other value, keep the image as is

    # Save the corrected image
    cv2.imwrite(save_path, rotated)

# List of image paths to be processed
image_paths = [
    'images/1.jpg',
    'images/2.jpg',
    'images/12.jpg',
    'images/13.jpg',
    'images/14.jpg',
    'images/23.png',
    'images/23_rotate.png'
]

# Correct the orientation for each image
for i, img_path in enumerate(image_paths):
    save_path = f'corrected_images1/corrected_image_{i + 1}.png'
    correct_orientation(img_path, save_path)
    print(f'Corrected image saved to {save_path}')

