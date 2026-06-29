#!/usr/bin/env python3
"""
Load camera calibration data and undistort live USB camera images.

Usage:
    python3 undistort_camera.py
"""

import cv2
import numpy as np
import sys


# =============== CONFIG ===============
CALIB_FILE = "calibration_chessboard_8x11_14p3mm.npz"
CAMERA_ID = 2

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

ALPHA = 1
# ALPHA = 0: 裁掉黑边，画面更满
# ALPHA = 1: 保留全部视野，可能有黑边
# ======================================


def load_calibration(calib_file):
    data = np.load(calib_file, allow_pickle=True)

    K = data["K"]
    dist = data["dist"]
    image_size = tuple(data["image_size"])

    print("Loaded calibration file:", calib_file)
    print()
    print("Camera Matrix K:")
    print(K)
    print()
    print("Distortion coefficients:")
    print(dist.ravel())
    print()
    print("Calibration image size:", image_size)

    return K, dist, image_size


def main():
    K, dist, calib_image_size = load_calibration(CALIB_FILE)

    cap = cv2.VideoCapture(CAMERA_ID)

    if not cap.isOpened():
        print(f"Error: Cannot open camera {CAMERA_ID}")
        print("Try: ls /dev/video*")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    ret, frame = cap.read()
    if not ret:
        print("Error: Cannot read camera frame")
        cap.release()
        sys.exit(1)

    h, w = frame.shape[:2]
    current_image_size = (w, h)

    print("Current camera image size:", current_image_size)

    if current_image_size != calib_image_size:
        print()
        print("Warning:")
        print("Current image size is different from calibration image size.")
        print("Calibration result is best used at the same resolution.")
        print(f"Calibration size: {calib_image_size}")
        print(f"Current size:     {current_image_size}")
        print()

    new_K, roi = cv2.getOptimalNewCameraMatrix(
        K,
        dist,
        current_image_size,
        ALPHA,
        current_image_size
    )

    map1, map2 = cv2.initUndistortRectifyMap(
        K,
        dist,
        None,
        new_K,
        current_image_size,
        cv2.CV_16SC2
    )

    print()
    print("Press ESC to quit.")
    print("Press s to save current undistorted frame.")
    print()

    save_id = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to read frame.")
            break

        undistorted = cv2.remap(
            frame,
            map1,
            map2,
            interpolation=cv2.INTER_LINEAR
        )

        original_small = cv2.resize(frame, (480, 270))
        undistorted_small = cv2.resize(undistorted, (480, 270))

        combined = np.hstack([original_small, undistorted_small])

        cv2.putText(
            combined,
            "Original",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            combined,
            "Undistorted",
            (500, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow("Original vs Undistorted", combined)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

        elif key == ord("s"):
            save_path = f"undistorted_{save_id:03d}.png"
            cv2.imwrite(save_path, undistorted)
            print(f"Saved: {save_path}")
            save_id += 1

    cap.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()