#!/usr/bin/env python3
"""
USB Camera Calibration using Chessboard

Pattern:
    8 x 11 internal corners
    14.3 mm square size

注意：
    OpenCV 的 PATTERN_SIZE 表示内部角点数，不是方格数。
    如果你的棋盘是 8x11 个方格，请改成 PATTERN_SIZE = (7, 10)
"""

import cv2
import numpy as np
import sys
from pathlib import Path


# ================= CONFIG =================
PATTERN_SIZE = (8, 11)        # 内部角点数量: (每行角点数, 每列角点数)
SQUARE_SIZE_MM = 14.3         # 每个棋盘格边长，单位 mm

CAMERA_ID = 2                 # 0=笔记本摄像头，2=USB 摄像头，可按实际修改
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

SAMPLE_COUNT = 25             # 建议 20~30 张
MIN_SAMPLE_COUNT = 8          # 少于这个数量不建议标定

OUTPUT_FILE = "calibration_chessboard_8x11_14p3mm.npz"
SAVE_CAPTURED_IMAGES = True
CAPTURE_DIR = Path("calibration_samples")
# ==========================================


def create_object_points(pattern_size, square_size_mm):
    """
    生成棋盘格在世界坐标系下的 3D 点。
    假设棋盘位于 z=0 平面。
    """
    cols, rows = pattern_size

    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= square_size_mm

    return objp


def find_chessboard_corners(gray, pattern_size):
    """
    优先使用 findChessboardCornersSB。
    如果当前 OpenCV 版本不支持，则回退到传统 findChessboardCorners。
    """
    found = False
    corners = None

    # 新版 OpenCV 更稳定的检测方法
    if hasattr(cv2, "findChessboardCornersSB"):
        flags_sb = (
            cv2.CALIB_CB_NORMALIZE_IMAGE
            + cv2.CALIB_CB_EXHAUSTIVE
            + cv2.CALIB_CB_ACCURACY
        )
        found, corners = cv2.findChessboardCornersSB(gray, pattern_size, flags_sb)

        if found:
            corners = corners.astype(np.float32)
            return True, corners

    # 传统方法作为 fallback
    flags = (
        cv2.CALIB_CB_ADAPTIVE_THRESH
        + cv2.CALIB_CB_NORMALIZE_IMAGE
        + cv2.CALIB_CB_FAST_CHECK
    )
    found, corners = cv2.findChessboardCorners(gray, pattern_size, flags)

    if found:
        criteria = (
            cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
            50,
            0.001
        )
        corners = cv2.cornerSubPix(
            gray,
            corners,
            winSize=(11, 11),
            zeroZone=(-1, -1),
            criteria=criteria
        )

    return found, corners


def compute_per_view_errors(obj_points, img_points, rvecs, tvecs, K, dist):
    """
    计算每一张图的重投影误差，方便判断哪些样本质量差。
    """
    errors = []

    for i in range(len(obj_points)):
        projected_points, _ = cv2.projectPoints(
            obj_points[i], rvecs[i], tvecs[i], K, dist
        )

        error = cv2.norm(img_points[i], projected_points, cv2.NORM_L2)
        error /= len(projected_points)
        errors.append(error)

    return np.array(errors)


def main():
    objp = create_object_points(PATTERN_SIZE, SQUARE_SIZE_MM)

    obj_points = []
    img_points = []
    saved_frames = []

    if SAVE_CAPTURED_IMAGES:
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(CAMERA_ID)

    if not cap.isOpened():
        print(f"Error: Cannot open camera {CAMERA_ID}")
        print("Try: ls /dev/video*")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    print("========== Camera Calibration ==========")
    print(f"Camera ID: {CAMERA_ID}")
    print(f"Pattern size: {PATTERN_SIZE[0]} x {PATTERN_SIZE[1]} internal corners")
    print(f"Square size: {SQUARE_SIZE_MM} mm")
    print(f"Target samples: {SAMPLE_COUNT}")
    print()
    print("Controls:")
    print("  SPACE  - capture current valid frame")
    print("  r      - reset captured samples")
    print("  ESC    - finish and calibrate")
    print("========================================")
    print()

    collected = 0
    last_frame_size = None

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Failed to read frame")
            break

        h, w = frame.shape[:2]
        last_frame_size = (w, h)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        found, corners = find_chessboard_corners(gray, PATTERN_SIZE)

        display = frame.copy()

        if found:
            cv2.drawChessboardCorners(display, PATTERN_SIZE, corners, found)
            status_text = f"Detected | SPACE to capture [{collected}/{SAMPLE_COUNT}]"
            status_color = (0, 255, 0)
        else:
            status_text = f"Not detected [{collected}/{SAMPLE_COUNT}]"
            status_color = (0, 0, 255)

        cv2.putText(
            display,
            status_text,
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            status_color,
            2
        )

        cv2.putText(
            display,
            f"Resolution: {w}x{h}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (220, 220, 220),
            1
        )

        cv2.imshow("Chessboard Calibration", display)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            print("Finish capturing.")
            break

        elif key == ord("r"):
            obj_points.clear()
            img_points.clear()
            saved_frames.clear()
            collected = 0
            print("Reset all samples.")

        elif key == ord(" ") and found:
            obj_points.append(objp.copy())
            img_points.append(corners.reshape(-1, 1, 2).copy())

            collected += 1
            print(f"Captured {collected}/{SAMPLE_COUNT}")

            if SAVE_CAPTURED_IMAGES:
                save_path = CAPTURE_DIR / f"sample_{collected:03d}.png"
                cv2.imwrite(str(save_path), frame)
                saved_frames.append(str(save_path))

            if collected >= SAMPLE_COUNT:
                print("Target sample count reached.")
                break

    cv2.destroyWindow("Chessboard Calibration")

    if len(obj_points) < MIN_SAMPLE_COUNT:
        print()
        print(f"Not enough samples: {len(obj_points)}")
        print(f"Need at least {MIN_SAMPLE_COUNT} samples.")
        cap.release()
        sys.exit(1)

    if last_frame_size is None:
        print("No valid frame size.")
        cap.release()
        sys.exit(1)

    print()
    print(f"========== Calibrating with {len(obj_points)} samples ==========")

    image_size = last_frame_size

    rms_error, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points,
        img_points,
        image_size,
        None,
        None
    )

    per_view_errors = compute_per_view_errors(
        obj_points, img_points, rvecs, tvecs, K, dist
    )

    print()
    print(f"RMS reprojection error: {rms_error:.6f} pixels")
    print(f"Mean per-view error: {per_view_errors.mean():.6f} pixels")
    print(f"Max per-view error: {per_view_errors.max():.6f} pixels")
    print()

    print("Camera Matrix K:")
    print(np.array2string(K, precision=6, suppress_small=True))
    print()

    print("Distortion coefficients:")
    print(np.array2string(dist.ravel(), precision=8, suppress_small=True))
    print()

    print("Per-view reprojection errors:")
    for i, err in enumerate(per_view_errors, start=1):
        print(f"  sample_{i:03d}: {err:.6f} px")

    np.savez(
        OUTPUT_FILE,
        K=K,
        dist=dist,
        rvecs=np.asarray(rvecs, dtype=np.float64),
        tvecs=np.asarray(tvecs, dtype=np.float64),
        pattern_size=np.array(PATTERN_SIZE),
        square_size_mm=SQUARE_SIZE_MM,
        image_size=np.array(image_size),
        rms_error=rms_error,
        per_view_errors=per_view_errors,
        saved_frames=np.array(saved_frames, dtype=object)
    )

    print()
    print(f"Calibration saved to: {OUTPUT_FILE}")

    # ========== Live Undistortion Preview ==========
    print()
    print("========== Live Undistortion Preview ==========")
    print("Press ESC to quit.")

    w, h = image_size
    new_K, roi = cv2.getOptimalNewCameraMatrix(
        K,
        dist,
        image_size,
        alpha=1,
        newImgSize=image_size
    )

    map1, map2 = cv2.initUndistortRectifyMap(
        K,
        dist,
        None,
        new_K,
        image_size,
        cv2.CV_16SC2
    )

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        undistorted = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)

        original_small = cv2.resize(frame, (480, 270))
        undist_small = cv2.resize(undistorted, (480, 270))

        combined = np.hstack([original_small, undist_small])

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

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Done.")


if __name__ == "__main__":
    main()