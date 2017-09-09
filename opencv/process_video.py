from __future__ import print_function, with_statement, division

import argparse

import cv2
import numpy as np

from image_processing import processImage

thresholds = {
    'lower_white': np.array([0, 0, 0]),
    'upper_white': np.array([90, 213, 249])
}

# Arrow keys
UP_KEY = 82
DOWN_KEY = 84
RIGHT_KEY = 83
LEFT_KEY = 81
ENTER_KEY = 10
EXIT_KEYS = [113, 27]  # Escape and q
M_KEY = 109
L_KEY = 108

parser = argparse.ArgumentParser(description='White Lane Detection for a batch of images')
parser.add_argument('-i','--input_video', help='Input Video',  default="debug/robot_vue.mp4", type=str)
parser.add_argument('-r','--regions', help='ROI',  default=1, type=int)
args = parser.parse_args()

video_file = args.input_video
cap = cv2.VideoCapture(video_file)

# Creating a window for later use
cv2.namedWindow('result')

def nothing(x):
    pass

h_min, s_min, v_min = thresholds['lower_white']
h_max, s_max, v_max = thresholds['upper_white']
# Creating track bar
cv2.createTrackbar('h_min', 'result', 0, 179, nothing)
cv2.createTrackbar('s_min', 'result', 0, 255, nothing)
cv2.createTrackbar('v_min', 'result', 0, 255, nothing)

cv2.createTrackbar('h_max', 'result', h_max, 179, nothing)
cv2.createTrackbar('s_max', 'result', s_max, 255, nothing)
cv2.createTrackbar('v_max', 'result', v_max, 255, nothing)

def getThresholds():
    # get info from track bar
    h_min = cv2.getTrackbarPos('h_min','result')
    s_min = cv2.getTrackbarPos('s_min','result')
    v_min = cv2.getTrackbarPos('v_min','result')

    h_max = cv2.getTrackbarPos('h_max','result')
    s_max = cv2.getTrackbarPos('s_max','result')
    v_max = cv2.getTrackbarPos('v_max','result')

    # Normal masking algorithm
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])
    thresholds = {
        'lower_white': lower,
        'upper_white': upper
    }
    return thresholds

current_idx = cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)
n_frames = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
print("{} frames".format(n_frames))
while True:
    while True:
        flag, img = cap.read()
        if flag:
            break
        else:
            # The next frame is not ready, so we try to read it again
            cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, current_idx - 1)
            cv2.waitKey(1000)

    regions = None
    if args.regions == 0:
        regions = [[0, 0, img.shape[1], img.shape[0]]]
    processImage(img, debug=True, regions=regions, thresholds=thresholds)

    key = cv2.waitKey(0) & 0xff
    if key in EXIT_KEYS:
        cv2.destroyAllWindows()
        exit()
    elif key in [LEFT_KEY, RIGHT_KEY]:
        current_idx += 1 if key == RIGHT_KEY else -1
        current_idx = np.clip(current_idx, 0, n_frames-1)
    thresholds = getThresholds()
    cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, current_idx)
