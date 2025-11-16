from ultralytics import YOLO
import cv2
import numpy as np
import requests
import os
from datetime import datetime
import time

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1439169769688272987/_rZ69D8DUPRQ940w8_kbJPWLdCZyQ5TtRciU_Z5B0Z9-gm6VK6d-bh-bd1H_KqxWwx7K"
ALERT_FOLDER = "alert_images"
os.makedirs(ALERT_FOLDER, exist_ok=True)

def send_discord_webhook(webhook_url: str, message: str, image_paths=None):
    try:
        if image_paths is None:
            resp = requests.post(webhook_url, json={"content": message})
            return resp.status_code in (200, 204)
        files = []
        for i, img in enumerate(image_paths):
            files.append(("file{}".format(i), (os.path.basename(img), open(img, "rb"), "image/jpeg")))
        resp = requests.post(webhook_url, data={"content": message}, files=files)
        return resp.status_code in (200, 204)
    except Exception as e:
        print("❌ Discord Error:", e)
        return False

def point_in_polygon(point, polygon):
    x, y = point
    polygon = np.array(polygon, dtype=np.int32)
    return cv2.pointPolygonTest(polygon, (float(x), float(y)), False) >= 0

# ===================== #
# CAMERA HEALTH CHECKS   #
# ===================== #
def is_black_frame(frame, black_threshold=20):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_val = np.mean(gray)
    return mean_val < black_threshold

def is_too_dark(frame, dark_threshold=50):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_val = np.mean(gray)
    return mean_val < dark_threshold

def is_obstructed(frame, edge_threshold=50):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return np.count_nonzero(edges) < edge_threshold

# ===================== #
# MOTION DETECTION       #
# ===================== #
def detect_motion(prev_frame, curr_frame, motion_threshold=5000):
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(prev_gray, curr_gray)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    motion_level = np.sum(thresh) / 255
    return motion_level > motion_threshold

# ===================== #
# AUTO BRIGHTNESS / GAMMA
# ===================== #
def adjust_brightness_gamma(frame, target_mean=100):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_val = np.mean(gray)
    if mean_val == 0:
        mean_val = 1
    gamma = np.log(target_mean/255.0) / np.log(mean_val/255.0)
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(frame, table)

# ===================== #
# MAIN CODE             #
# ===================== #
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("⚠️ เปิดกล้องไม่ได้")
    exit()

zone_polygon = None
zone_initialized = False
last_notify_time = 0
notify_cooldown = 5
last_health_alert = 0
health_alert_cooldown = 10  # แจ้งเตือนกล้องทุก 10 วินาที
prev_frame = None

print("ระบบเริ่มทำงานแล้ว...\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    original_frame = frame.copy()
    now = time.time()
    health_issue = None

    # ===================== #
    # CAMERA HEALTH ALERTS  #
    # ===================== #
    if now - last_health_alert > health_alert_cooldown:
        if is_black_frame(frame):
            health_issue = "📷 กล้องจับภาพดำ (Black frame)"
        elif is_too_dark(frame):
            health_issue = "💡 ภาพมืดเกินไป (Too dark)"
        elif is_obstructed(frame):
            health_issue = "✋ มีสิ่งปิดกล้อง (Obstruction)"

        if health_issue:
            send_discord_webhook(DISCORD_WEBHOOK, f"⚠️ Camera Health Alert!\n{health_issue}\n⏰ เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            last_health_alert = now
            cv2.putText(frame, health_issue, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    # ===================== #
    # INITIALIZE ZONE       #
    # ===================== #
    if not zone_initialized:
        h, w = frame.shape[:2]
        box_w = int(w * 0.4)
        box_h = int(h * 0.4)
        x1 = w // 2 - box_w // 2
        y1 = h // 2 - box_h // 2
        x2 = x1 + box_w
        y2 = y1 + box_h
        zone_polygon = np.array([[x1,y1],[x2,y1],[x2,y2],[x1,y2]], np.int32)
        zone_initialized = True

    # วาดโซน
    cv2.polylines(frame, [zone_polygon], True, (0,255,255), 3)

    # ถ้ามีปัญหากล้อง → skip YOLO
    if health_issue:
        cv2.imshow("YOLO Multi-Person Alert", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        continue

    # ===================== #
    # MOTION DETECTION       #
    # ===================== #
    motion_detected = True
    if prev_frame is not None:
        motion_detected = detect_motion(prev_frame, frame)
    prev_frame = frame.copy()

    if not motion_detected:
        cv2.putText(frame, "No motion detected - Skipping YOLO", (10, 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imshow("YOLO Multi-Person Alert", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        continue

    # ===================== #
    # AUTO BRIGHTNESS/GAMMA #
    # ===================== #
    frame = adjust_brightness_gamma(frame, target_mean=100)

    # ===================== #
    # YOLO DETECTION         #
    # ===================== #
    results = model(frame, verbose=False)
    inzone_people = []

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            if model.names[cls] != "person":
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            inside_zone = point_in_polygon((cx, cy), zone_polygon)
            if inside_zone and conf > 0.5:
                inzone_people.append([x1, y1, x2, y2, conf])

            color = (0,0,255) if inside_zone else (0,255,0)
            cv2.rectangle(frame, (int(x1),int(y1)), (int(x2),int(y2)), color, 2)

    # ===================== #
    # MULTI-PERSON ALERT     #
    # ===================== #
    if len(inzone_people) > 0:
        if now - last_notify_time > notify_cooldown:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            saved_paths = []

            for idx, (x1, y1, x2, y2, conf) in enumerate(inzone_people):
                margin = 30
                cx1 = max(0, int(x1) - margin)
                cy1 = max(0, int(y1) - margin)
                cx2 = min(original_frame.shape[1], int(x2) + margin)
                cy2 = min(original_frame.shape[0], int(y2) + margin)

                crop_img = original_frame[cy1:cy2, cx1:cx2]
                path = os.path.join(ALERT_FOLDER, f"group_person{idx}_{timestamp}.jpg")
                cv2.imwrite(path, crop_img)
                saved_paths.append(path)

            text_msg = (
                f"⚠️ ตรวจพบ **{len(inzone_people)} คน** ภายในเขตเฝ้าระวัง!\n"
                f"⏰ เวลา: {timestamp}\n"
                f"📸 ส่งรูปทุกคนในเฟรมแล้ว"
            )
            send_discord_webhook(DISCORD_WEBHOOK, text_msg, saved_paths)
            last_notify_time = now

    # ===================== #
    # SHOW FRAME             #
    # ===================== #
    cv2.imshow("YOLO Multi-Person Alert", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("ระบบปิดแล้ว")