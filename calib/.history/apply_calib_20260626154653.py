#!/usr/bin/env python3
"""
Load saved calibration and apply undistortion to live camera feed or an image.
Usage:
  python apply_calib.py                    # live camera
  python apply_calib.py --image path.jpg    # single image
  python apply_calib.py --video path.mp4    # video file
"""

import cv2
import numpy as np
import sys

CALIB_FILE = "calibration_data.npz"


def load_calibration(path=CALIB_FILE):
    data = np.load(path, allow_pickle=True)
    K = data["K"]
    dist = data["dist"]
    return K, dist, data


def main():
    try:
        K, dist, _ = load_calibration()
    except FileNotFoundError:
        print(f"Error: {CALIB_FILE} not found. Run calibrate.py first.")
        sys.exit(1)

    print(f"Loaded calibration: K =\n{K}")
    print(f"dist = {dist.ravel()}")

    # Determine input source
    if "--image" in sys.argv:
        idx = sys.argv.index("--image") + 1
        src = cv2.imread(sys.argv[idx])
        if src is None:
            print(f"Error: cannot read {sys.argv[idx]}")
            sys.exit(1)
        h, w = src.shape[:2]
        new_K, roi = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), 1, (w, h))
        undist = cv2.undistort(src, K, dist, None, new_K)
        x, y, roi_w, roi_h = roi
        if roi_w > 0 and roi_h > 0:
            undist = undist[y:y+roi_h, x:x+roi_w]
        cv2.imshow("Original", src)
        cv2.imshow("Undistorted", undist)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        out_name = "undistorted_" + sys.argv[idx].rsplit("/", 1)[-1]
        cv2.imwrite(out_name, undist)
        print(f"Saved to {out_name}")
        return

    if "--video" in sys.argv:
        idx = sys.argv.index("--video") + 1
        cap = cv2.VideoCapture(sys.argv[idx])
    else:
        cap = cv2.VideoCapture(0)  # live camera

    if not cap.isOpened():
        print("Error: cannot open video source")
        sys.exit(1)

    ret, frame = cap.read()
    if not ret:
        print("Error: cannot read first frame")
        sys.exit(1)

    h, w = frame.shape[:2]
    new_K, roi = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), 1, (w, h))
    x, y, roi_w, roi_h = roi

    out_writer = None
    if "--video" in sys.argv:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_writer = cv2.VideoWriter("undistorted_output.mp4",
                                     fourcc, 30, (w, h))

    print("Press ESC to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        undist = cv2.undistort(frame, K, dist, None, new_K)
        display_undist = undist
        if roi_w > 0 and roi_h > 0:
            display_undist = undist[y:y+roi_h, x:x+roi_w]

        if out_writer:
            out_writer.write(undist)

        side = cv2.resize(frame, (320, 240))
        us = cv2.resize(display_undist, (320, 240))
        cv2.imshow("Undistorted (ESC to quit)", np.hstack((side, us)))

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    if out_writer:
        out_writer.release()
        print("Saved to undistorted_output.mp4")
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
