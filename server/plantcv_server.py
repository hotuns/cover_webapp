# !/usr/bin/python
import sys, traceback
import cv2
import numpy as np
import argparse
import string
import json
import socket
from plantcv import plantcv as pcv
from flask import request, Flask
app = Flask(__name__)

@app.route('/')
def index():
    origin_path = request.args.get('originPath')
    processed_path = request.args.get('processedPath')
    try:
        re, output_image_name = compute_coverage(origin_path, processed_path)
        res = {'re': re, 'output_image_name': output_image_name}
    except Exception as e:
        res = {}
    return json.dumps(res)

@app.route('/version')
def version():
    return "hello cover"

def compute_coverage(input_image_name, output_image_name):
    # Read image
    img, path, filename = pcv.readimage(filename=input_image_name)
    img = cv2.resize(img, (1280,960), interpolation=cv2.INTER_AREA)
    #balance 
    img = pcv.white_balance(img, mode='hist')
    # Convert RGB to HSV and extract the saturation channel
    s = pcv.rgb2gray_hsv(rgb_img=img, channel='s')
    # Threshold the saturation image
    s_thresh = pcv.threshold.binary(gray_img=s, threshold=25, max_value=255, object_type='light')

    # Median Blur
    s_mblur = pcv.median_blur(gray_img=s_thresh, ksize=5)
    s_cnt = pcv.median_blur(gray_img=s_thresh, ksize=5)

    # Convert RGB to LAB and extract the Blue channel
    b = pcv.rgb2gray_lab(rgb_img=img, channel='b')

    # Threshold the blue image
    b_thresh = pcv.threshold.binary(gray_img=b, threshold=180, max_value=255, object_type='light')
    b_cnt = pcv.threshold.binary(gray_img=b, threshold=180, max_value=255, object_type='light')

    # Fill small objects
    # b_fill = pcv.fill(b_thresh, 10)

    # Join the thresholded saturation and blue-yellow images
    bs = pcv.logical_or(bin_img1=s_mblur, bin_img2=b_cnt)

    # Apply Mask (for VIS images, mask_color=white)
    masked = pcv.apply_mask(img=img, mask=bs, mask_color='white')

    # Convert RGB to LAB and extract the Green-Magenta and Blue-Yellow channels
    masked_a = pcv.rgb2gray_lab(rgb_img=masked, channel='a')
    masked_b = pcv.rgb2gray_lab(rgb_img=masked, channel='b')

    # Threshold the green-magenta and blue images
    maskeda_thresh = pcv.threshold.binary(gray_img=masked_a, threshold=95, max_value=255, object_type='dark')
    maskeda_thresh1 = pcv.threshold.binary(gray_img=masked_a, threshold=135, max_value=255, object_type='light')
    maskedb_thresh = pcv.threshold.binary(gray_img=masked_b, threshold=128, max_value=255, object_type='light')

    # Join the thresholded saturation and blue-yellow images (OR)
    ab1 = pcv.logical_or(bin_img1=maskeda_thresh, bin_img2=maskedb_thresh)
    ab = pcv.logical_or(bin_img1=maskeda_thresh1, bin_img2=ab1)

    # Fill small objects
    ab_fill = pcv.fill(bin_img=ab, size=200)

    # Apply mask (for VIS images, mask_color=white)
    masked2 = pcv.apply_mask(img=masked, mask=ab_fill, mask_color='white')
    # Identify objects
    id_objects, obj_hierarchy = pcv.find_objects(img=masked2, mask=ab_fill)

    # Define ROI
    roi1, roi_hierarchy= pcv.roi.rectangle(img=masked2, x=0, y=0, h=img.shape[0], w=img.shape[1])

    # Decide which objects to keep
    roi_objects, hierarchy3, kept_mask, obj_area = pcv.roi_objects(img=img, roi_contour=roi1, 
                                                               roi_hierarchy=roi_hierarchy, 
                                                               object_contour=id_objects, 
                                                               obj_hierarchy=obj_hierarchy,
                                                               roi_type='partial')

    # Object combine kept objects
    obj, mask = pcv.object_composition(img=img, contours=roi_objects, hierarchy=hierarchy3)
    count = 0
    [rows, cols] = mask.shape
    for i in range(rows):
        for j in range(cols):
            if mask[i,j]>128:
                count+=1
    re = float(count)/(rows*cols)
    cv2.imwrite(output_image_name, mask)
    return re, output_image_name

def main():
    parser = argparse.ArgumentParser(description="Imaging processing with opencv")
    parser.add_argument("-i", "--image", help="Input image file.", required=True)
    parser.add_argument("-o", "--outdir", help="Output directory for image files.", required=False)
    parser.add_argument("-r", "--result", help="result file.", required=False)
    parser.add_argument("-w", "--writeimg", help="write out images.", default=False, action="store_true")
    parser.add_argument("-f", "--fileout", help="output mask file path", required=True)
    parser.add_argument("-D", "--debug",
                        help="can be set to 'print' or None (or 'plot' if in jupyter) prints intermediate images.",
                        default=None)
    
    args = parser.parse_args()

    pcv.params.debug = args.debug  # set debug mode
    pcv.params.debug_outdir = args.outdir  # set output directory

    re, fileout = compute_coverage(args.image, args.fileout)
    print(re)

if __name__ == "__main__":
    app.debug=True
    hostname=socket.gethostname()
    ip=socket.gethostbyname(hostname)
    app.run(host=ip,port=9876)
