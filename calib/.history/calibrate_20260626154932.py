#!/usr/bin/env python3
"""
USB Camera Calibration using Chessboard
Pattern: 8x11 internal corners, 20mm square size
"""

import cv2
import numpy as np
import os
import sys

# === CONFIG ===
PATTERN_SIZE = (8, 11)   # (internal corners per row, per column)
SQUARE_SIZE_MM = 20.0    # chessboard square side length in mm
CAMERA_ID = 2            # 0=laptop, 2=USB camera (XC-TECH)
SAMPLE_COUNT = 20        # number of good frames to capture
OUTPUT_FILE = "calibration_data.npz"
# ==============


def main():
    # 3D object points for the chessboard (z=0 plane)
    pattern_points = np.zeros((PATTERN_SIZE[0] * PATTERN_SIZE[1], 3), np.float32)
    pattern_points[:, :2] = np.mgrid[0:PATTERN_SIZE[0],
                                     0:PATTERN_SIZE[1]].T.reshape(-1, 2)
    pattern_points *= SQUARE_SIZE_MM

    obj_points = []   # 3D points in world space
    img_points = []   # 2D points in image plane

    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print(f"Error: Cannot open camera {CAMERA_ID}")
        print("Try: ls /dev/video*  to list available cameras")
        sys.exit(1)

    # Try to set higher resolution for better calibration
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f"Camera opened ({CAMERA_ID})")
    print(f"Board: {PATTERN_SIZE[0]}x{PATTERN_SIZE[1]} internal corners, "
          f"{SQUARE_SIZE_MM}mm squares")
    print(f"Target: {SAMPLE_COUNT} samples")
    print()
    print("Controls:")
    print("  SPACE  - capture current frame (board must be detected)")
    print("  ESC    - finish & calibrate with captured samples")
    print("  r      - reset all captured samples")
    print()

    collected = 0
    while collected < SAMPLE_COUNT:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]

        # Find chessboard corners
        found, corners = cv2.findChessboardCorners(
            gray, PATTERN_SIZE,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
        )

        display = frame.copy()

        if found:
            # Refine corner positions to sub-pixel accuracy
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                        30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                       criteria)
            cv2.drawChessboardCorners(display, PATTERN_SIZE, corners, found)
            msg = f"Board detected! SPACE to capture [{collected}/{SAMPLE_COUNT}]"
            color = (0, 255, 0)
        else:
            msg = f"No board [{collected}/{SAMPLE_COUNT}]"
            color = (0, 0, 255)

        cv2.putText(display, msg, (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(display, f"Res: {w}x{h}", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("Calibration", display)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:   # ESC
            print("User interrupted.")
            break
        elif key == ord(' ') and found:
            obj_points.append(pattern_points)
            img_points.append(corners)
            collected += 1
            print(f"  Captured {collected}/{SAMPLE_COUNT}")
        elif key == ord('r'):
            obj_points.clear()
            img_points.clear()
            collected = 0
            print("  Reset all samples.")

    cv2.destroyWindow("Calibration")

    if len(obj_points) < 5:
        print(f"Not enough samples ({len(obj_points)}). Need at least 5.")
        cap.release()
        sys.exit(1)

    print(f"\n=== Calibrating with {len(obj_points)} samples ===")

    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, (w, h), None, None
    )

    print(f"\nReprojection error: {ret:.4f} pixels")
    print(f"\nCamera Matrix (3x3):\n{np.array2string(K, precision=4, suppress_small=True)}")
    print(f"\nDistortion coefficients (5x1):\n{dist.ravel()}")

    # Save calibration data
    np.savez(OUTPUT_FILE,
             K=K, dist=dist,
             rvecs=np.array(rvecs, dtype=object),
             tvecs=np.array(tvecs, dtype=object),
             pattern_size=PATTERN_SIZE,
             square_size_mm=SQUARE_SIZE_MM,
             image_size=(w, h),
             reproj_error=ret)
    print(f"\nCalibration saved to {OUTPUT_FILE}")

    # === Live undistort preview ===
    print("\n=== Undistorted live view (ESC to quit) ===")
    new_K, roi = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), 1, (w, h))
    x, y, roi_w, roi_h = roi

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        undist = cv2.undistort(frame, K, dist, None, new_K)

        # Crop to valid ROI
        if roi_w > 0 and roi_h > 0:
            undist = undist[y:y+roi_h, x:x+roi_w]

        side = cv2.resize(frame, (320, 240))
        undist_small = cv2.resize(undist, (320, 240))

        combined = np.hstack((side, undist_small))
        cv2.putText(combined, "Original", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(combined, "Undistorted", (330, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imshow("Result: Original vs Undistorted", combined)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()
