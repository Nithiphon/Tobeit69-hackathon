from ultralytics import YOLO
import cv2
import numpy as np
import requests
import os
from datetime import datetime
import time

# LINE Messaging API settings
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "9g4Pb93Mqoqsws+zNfQWkLpWaHOkXdqg3ar7U3kL1f8O/OIwVLWtz4ctHsW6SELkOwaCQNRQSRKh8zATAydzWac6yRLzVLeSEYHEJsrkEPGhtu+Pxm+VkYA4VjnwZMGjdwsOoioH8+Uo0hnXWigcnAdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = os.getenv("LINE_USER_ID", "Ud0a320fd7f6668af93a78405ca8a08fa")

def push_line_text(token: str, to_user_id: str, message: str) -> bool:
    """ส่งข้อความตัวอักษรผ่าน LINE Messaging API (push message)"""
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": to_user_id,
            "messages": [
                {"type": "text", "text": message}
            ]
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            print("✅ ส่ง LINE ข้อความสำเร็จ")
            return True
        print(f"❌ ส่ง LINE ข้อความล้มเหลว: {resp.status_code} - {resp.text}")
        return False
    except Exception as e:
        print(f"❌ ข้อผิดพลาดส่ง LINE ข้อความ: {e}")
        return False

def point_in_polygon(point, polygon):
    """ตรวจสอบว่าจุดอยู่ในรูปหลายเหลี่ยมหรือไม่"""
    x, y = point
    polygon = np.array(polygon, dtype=np.int32)
    result = cv2.pointPolygonTest(polygon, (float(x), float(y)), False)
    return result >= 0

# 1. โหลดโมเดล YOLO
model = YOLO("yolov8n.pt")

# 2. เปิดกล้อง
cap = cv2.VideoCapture("Video/Videotest2.mp4")

# ⭐ กำหนดโซนเป็นรูปหลายเหลี่ยม (Polygon) - รูปเดียวหลายจุด
# คุณสามารถเพิ่มจุดได้ตามต้องการ เพื่อครอบคลุมพื้นที่ที่ซับซ้อน
zone_polygon = np.array([
    [9, 275],   # จุดที่ 1 (ซ้ายล่าง)
    [433, 258],   # จุดที่ 2
    [557, 350],   # จุดที่ 3
    [1234, 689],   # จุดที่ 4
    [549, 715],   # จุดที่ 5
    [430, 572],   # จุดที่ 6
    [1, 608],   # จุดที่ 7 (ขวาล่าง)
    [7, 449]   # จุดที่ 8
], dtype=np.int32)



# ตัวแปรสำหรับป้องกันการแจ้งเตือนซ้ำ
last_notify_time = 0
notify_cooldown = 5  # เว้นช่วงแจ้งเตือน 5 วินาที

print("🚀 กำลังรันระบบ Elder Ma Nee Ma (Polygon Zone)")
print("📍 โซนตรวจจับ: รูปหลายเหลี่ยม 9 จุด")
print("กด 'q' เพื่อออกจากโปรแกรม\n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ วิดีโอจบแล้ว หรืออ่านเฟรมไม่ได้")
        break

    # วาดโซนตรวจจับ (รูปหลายเหลี่ยม)
    cv2.polylines(frame, [zone_polygon], isClosed=True, color=(0, 255, 255), thickness=3)
    # เติมสีโปร่งแสงในโซน
    overlay = frame.copy()
    cv2.fillPoly(overlay, [zone_polygon], color=(0, 255, 255))
    frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)

    # ตรวจจับวัตถุด้วย YOLO
    results = model(frame, verbose=False)

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            label = model.names[cls]
            
            if label == "person":
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                # ตรวจสอบว่าจุดศูนย์กลางอยู่ในโซนหรือไม่
                inside_zone = point_in_polygon((center_x, center_y), zone_polygon)

                # ถ้าอยู่ในโซนและความมั่นใจสูงพอ
                if inside_zone and conf > 0.5:
                    current_time = time.time()
                    if current_time - last_notify_time > notify_cooldown:
                        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        text_msg = (
                            f"⚠️ ตรวจพบไอแก่หนีออกจากบ้าน รีบไปตามไอควาย\n"
                            f"โปรดระวัง\n"
                            f"📍 ตำแหน่ง: ({center_x:.1f}, {center_y:.1f})\n"
                            f"⏰ เวลา: {timestamp}\n"
                            f"📊 ความมั่นใจ: {conf:.2%}"
                        )
                        push_line_text(LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, text_msg)
                        last_notify_time = current_time
                        print(f"🔔 แจ้งเตือนส่งแล้ว! (เวลา: {timestamp})")

                # วาดกรอบและจุดศูนย์กลาง
                color = (0, 0, 255) if inside_zone else (0, 255, 0)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.circle(frame, (int(center_x), int(center_y)), 10, color, -1)
                
                tag = f"{label} {conf:.2f}"
                if inside_zone:
                    tag += " ⚠️ IN-ZONE"
                cv2.putText(frame, tag, (int(x1), int(y1)-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # แสดงข้อมูลเพิ่มเติม
    cv2.putText(frame, "Elder Ma Nee Ma - Polygon Detection", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"Zone: Polygon ({len(zone_polygon)} points)", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # แสดงภาพ
    cv2.imshow("YOLO Detection - Polygon Zone", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("ปิดโปรแกรมเรียบร้อย")