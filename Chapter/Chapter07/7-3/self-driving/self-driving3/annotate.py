import cv2
import numpy as np
import os
import json

VIDEO_DIR = r"C:\Users\user\Desktop\self-driving\video"
OUTPUT_JSON = r"C:\Users\user\Desktop\self-driving\annotations.json"
DISPLAY_W = 960
WINDOW = "Annotator"

LINE_KEYS = {
    ord('1'): "left_inner",
    ord('2'): "left_outer",
    ord('3'): "right_inner",
    ord('4'): "right_outer",
}
LINE_COLORS = {
    "left_inner": (0, 255, 0),
    "left_outer": (0, 200, 0),
    "right_inner": (0, 0, 255),
    "right_outer": (0, 0, 200),
}
LINE_LABELS = {
    "left_inner": "L1",
    "left_outer": "L2",
    "right_inner": "R1",
    "right_outer": "R2",
}

point1 = None
point2 = None
temp_lines = {}
scale = 1.0
base_img = None
msg = ""


def redraw():
    img = base_img.copy()
    for side, pts in temp_lines.items():
        color = LINE_COLORS.get(side, (255, 255, 255))
        p1 = (int(pts[0][0] * scale), int(pts[0][1] * scale))
        p2 = (int(pts[1][0] * scale), int(pts[1][1] * scale))
        cv2.line(img, p1, p2, color, 2)
        cv2.circle(img, p1, 5, color, -1)
        cv2.circle(img, p2, 5, color, -1)
        label = LINE_LABELS.get(side, side)
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        cv2.putText(img, label, (mx - 10, my - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    if point1 and not point2:
        cv2.circle(img, point1, 5, (0, 255, 255), -1)
    if point1 and point2:
        cv2.line(img, point1, point2, (0, 255, 255), 2)
        cv2.circle(img, point1, 5, (0, 255, 255), -1)
        cv2.circle(img, point2, 5, (0, 255, 255), -1)

    h, w = base_img.shape[:2]
    marked = [LINE_LABELS.get(k, k) for k in temp_lines.keys()]
    info1 = f"Points: {'2/2' if point2 else '1/2' if point1 else '0/2'}  |  Lines: {', '.join(marked) or 'none'}"
    cv2.putText(img, info1, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    if msg:
        cv2.putText(img, msg, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    help_text = "1=L1(in) 2=L2(out) 3=R1(in) 4=R2(out) S=save C=clear N=next P=prev Q=quit"
    cv2.putText(img, help_text, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.imshow(WINDOW, img)


def mouse_cb(event, x, y, flags, param):
    global point1, point2
    if event == cv2.EVENT_LBUTTONDOWN:
        if point1 is None:
            point1 = (x, y)
            print(f"  [CLICK] Point 1: ({x},{y})")
        else:
            point2 = (x, y)
            print(f"  [CLICK] Point 2: ({x},{y}) - Now press 1/2/3/4")
        redraw()


def main():
    global point1, point2, temp_lines, scale, base_img, msg

    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r") as f:
            all_ann = json.load(f)
    else:
        all_ann = {}

    files = sorted([f for f in os.listdir(VIDEO_DIR)
                    if f.startswith("train_") and f.endswith(".png")])
    if not files:
        print("No images")
        return

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, DISPLAY_W, 700)
    cv2.setMouseCallback(WINDOW, mouse_cb)

    idx = 0
    need_reload = True

    print("\n=== 4-Line Annotation ===")
    print("Click 2 points, then:")
    print("  1 = L1 (left inner)")
    print("  2 = L2 (left outer)")
    print("  3 = R1 (right inner)")
    print("  4 = R2 (right outer)")
    print("S=save  C=clear  N=next  P=prev  Q=quit\n")

    while idx < len(files):
        if need_reload:
            fname = files[idx]
            frame = cv2.imread(os.path.join(VIDEO_DIR, fname))
            if frame is None:
                idx += 1
                continue

            h, w = frame.shape[:2]
            scale = DISPLAY_W / w
            display_h = int(h * scale)
            base_img = cv2.resize(frame, (DISPLAY_W, display_h))

            point1 = None
            point2 = None
            temp_lines = all_ann.get(fname, {}).copy()
            msg = ""

            cv2.setWindowTitle(WINDOW, f"[{idx+1}/{len(files)}] {fname}")
            redraw()
            need_reload = False

        key = cv2.waitKey(0) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('n'):
            idx += 1
            need_reload = True
        elif key == ord('p'):
            idx = max(0, idx - 1)
            need_reload = True
        elif key == ord('c'):
            point1 = None
            point2 = None
            msg = "Cleared"
            print("  [CLEAR]")
            redraw()
        elif key in LINE_KEYS:
            if point1 and point2:
                line_name = LINE_KEYS[key]
                temp_lines[line_name] = [
                    [int(point1[0]/scale), int(point1[1]/scale)],
                    [int(point2[0]/scale), int(point2[1]/scale)]
                ]
                msg = f"{LINE_LABELS[line_name]} registered"
                print(f"  [{LINE_LABELS[line_name]}] {temp_lines[line_name]}")
                point1 = None
                point2 = None
                redraw()
            else:
                msg = "Need 2 points first!"
                print(f"  [{LINE_LABELS.get(LINE_KEYS[key], '?')}] FAILED - need 2 points")
                redraw()
        elif key == ord('s'):
            all_ann[fname] = temp_lines.copy()
            with open(OUTPUT_JSON, "w") as f:
                json.dump(all_ann, f, indent=2)
            msg = f"SAVED -> {list(temp_lines.keys())}"
            print(f"  [SAVE] {fname}: {list(temp_lines.keys())}")
            redraw()

    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_ann, f, indent=2)
    print(f"\nTotal saved: {len(all_ann)}")
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
