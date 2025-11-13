from ultralytics import YOLO
import cv2
import numpy as np
import requests
import os
from datetime import datetime
import time
import base64

# LINE Messaging API settings
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "9g4Pb93Mqoqsws+zNfQWkLpWaHOkXdqg3ar7U3kL1f8O/OIwVLWtz4ctHsW6SELkOwaCQNRQSRKh8zATAydzWac6yRLzVLeSEYHEJsrkEPGhtu+Pxm+VkYA4VjnwZMGjdwsOoioH8+Uo0hnXWigcnAdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = os.getenv("LINE_USER_ID", "Ud0a320fd7f6668af93a78405ca8a08fa")

# สร้างโฟลเดอร์สำหรับบันทึกรูปภาพ
ALERT_FOLDER = "alert_images"
os.makedirs(ALERT_FOLDER, exist_ok=True)

# ImgBB API Key - สมัครฟรีที่ https://api.imgbb.com/
IMGBB_API_KEY = "5f2ea505ff11f11b145c8f3282acb2fc"  # ใส่ API Key ของคุณที่นี่ เช่น "abc123xyz456"

def upload_image_to_imgbb(image_path: str, api_key: str) -> str:
    """
    อัปโหลดรูปภาพไป ImgBB และคืนค่า URL
    สมัคร API Key ฟรีที่: https://api.imgbb.com/
    """
    try:
        url = "https://api.imgbb.com/1/upload"
        
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        payload = {
            "key": api_key,
            "image": image_data,
            "expiration": 600  # รูปจะหายหลัง 10 นาที (600 วินาที) - ปรับได้ตามต้องการ
        }
        
        response = requests.post(url, data=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                image_url = data['data']['url']
                print(f"✅ อัปโหลด ImgBB สำเร็จ: {image_url}")
                return image_url
            else:
                print(f"❌ ImgBB error: {data}")
                return None
        else:
            print(f"❌ อัปโหลด ImgBB ล้มเหลว: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ข้อผิดพลาดอัปโหลด ImgBB: {e}")
        return None

def upload_image_to_cloudinary(image_path: str, cloud_name: str, api_key: str, api_secret: str) -> str:
    """
    อัปโหลดรูปภาพไป Cloudinary และคืนค่า URL
    สมัครฟรีที่: https://cloudinary.com/
    """
    try:
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        result = cloudinary.uploader.upload(image_path)
        image_url = result['secure_url']
        print(f"✅ อัปโหลด Cloudinary สำเร็จ: {image_url}")
        return image_url
        
    except Exception as e:
        print(f"❌ ข้อผิดพลาดอัปโหลด Cloudinary: {e}")
        return None

def push_line_text_only(token: str, to_user_id: str, message: str) -> bool:
    """ส่งเฉพาะข้อความผ่าน LINE"""
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

def push_line_with_image_url(token: str, to_user_id: str, message: str, image_url: str) -> bool:
    """ส่งข้อความพร้อมรูปภาพผ่าน LINE (ใช้ URL)"""
    try:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "to": to_user_id,
            "messages": [
                {"type": "text", "text": message},
                {
                    "type": "image",
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url
                }
            ]
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if resp.status_code in (200, 201):
            print("✅ ส่ง LINE พร้อมรูปภาพสำเร็จ")
            return True
        else:
            print(f"❌ ส่ง LINE ล้มเหลว: {resp.status_code} - {resp.text}")
            return False
            
    except Exception as e:
        print(f"❌ ข้อผิดพลาดส่ง LINE: {e}")
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
cap = cv2.VideoCapture("Video/Videotest3.mp4")

# กำหนดโซนเป็นรูปหลายเหลี่ยม
zone_polygon = np.array([
    [38, 354],
    [338, 350],
    [1175, 342],
    [1170, 716],
    [508, 560],
    [331, 512],
    [326, 534],
    [111, 473],
    [38, 449],
], dtype=np.int32)

# ตัวแปรสำหรับป้องกันการแจ้งเตือนซ้ำ
last_notify_time = 0
notify_cooldown = 5  # เว้นช่วงแจ้งเตือน 5 วินาที

print("="*70)
print("🚀 Elder Ma Nee Ma - Image Alert System")
print("="*70)
print(f"📍 โซนตรวจจับ: รูปหลายเหลี่ยม {len(zone_polygon)} จุด")
print(f"📸 บันทึกรูปภาพที่: {ALERT_FOLDER}/")

if IMGBB_API_KEY:
    print("☁️  อัปโหลดรูปภาพ: ImgBB (เปิดใช้งาน)")
    print("📱 LINE: ส่งข้อความ + รูปภาพ")
else:
    print("💾 โหมด: บันทึกรูปในเครื่องเท่านั้น")
    print("📱 LINE: ส่งเฉพาะข้อความ")
    print("")
    print("💡 เคล็ดลับ: ถ้าต้องการส่งรูปผ่าน LINE")
    print("   1. สมัคร API Key ฟรีที่: https://api.imgbb.com/")
    print("   2. ใส่ API Key ในตัวแปร IMGBB_API_KEY")

print("="*70)
print("กด 'q' เพื่อออกจากโปรแกรม\n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ วิดีโอจบแล้ว หรืออ่านเฟรมไม่ได้")
        break

    # สำเนาเฟรมต้นฉบับสำหรับบันทึก
    original_frame = frame.copy()

    # วาดโซนตรวจจับ
    cv2.polylines(frame, [zone_polygon], isClosed=True, color=(0, 255, 255), thickness=3)
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
                        
                        # ครอบรูปบุคคลที่ตรวจพบ
                        margin = 30  # ขยายกรอบออกไปอีกนิด
                        crop_x1 = max(0, int(x1) - margin)
                        crop_y1 = max(0, int(y1) - margin)
                        crop_x2 = min(original_frame.shape[1], int(x2) + margin)
                        crop_y2 = min(original_frame.shape[0], int(y2) + margin)
                        
                        cropped_person = original_frame[crop_y1:crop_y2, crop_x1:crop_x2]
                        
                        # บันทึกรูปภาพ 2 แบบ
                        # 1. รูปเต็มจอพร้อมกรอบและโซน
                        full_image_path = os.path.join(ALERT_FOLDER, f"full_{timestamp}.jpg")
                        cv2.imwrite(full_image_path, frame)
                        
                        # 2. รูปครอบเฉพาะบุคคล
                        person_image_path = os.path.join(ALERT_FOLDER, f"person_{timestamp}.jpg")
                        cv2.imwrite(person_image_path, cropped_person)
                        
                        # สร้างข้อความแจ้งเตือน
                        text_msg = (
                            f"⚠️ ตรวจพบผู้สูงอายุในเขตเฝ้าระวัง!\n"
                            f"รีบไปตามไอควาย\n"
                            f"📍 ตำแหน่ง: ({center_x:.1f}, {center_y:.1f})\n"
                            f"⏰ เวลา: {timestamp}\n"
                            f"📊 ความมั่นใจ: {conf:.2%}\n"
                            f"━━━━━━━━━━━━━━━\n"
                            f"📸 อีแก่นี้ มันหนีออกจากบ้าน"
                        )
                        
                        # ถ้ามี ImgBB API Key ให้อัปโหลดและส่งรูปผ่าน LINE
                        if IMGBB_API_KEY:
                            print("☁️  กำลังอัปโหลดรูปภาพไป ImgBB...")
                            image_url = upload_image_to_imgbb(person_image_path, IMGBB_API_KEY)
                            if image_url:
                                push_line_with_image_url(LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, 
                                                        text_msg, image_url)
                            else:
                                # ถ้าอัปโหลดล้มเหลว ส่งแค่ข้อความ
                                print("⚠️  อัปโหลดล้มเหลว ส่งเฉพาะข้อความ")
                                push_line_text_only(LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, text_msg)
                        else:
                            # ส่งแค่ข้อความ (รูปบันทึกในเครื่อง)
                            push_line_text_only(LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, text_msg)
                        
                        last_notify_time = current_time
                        print(f"🔔 แจ้งเตือนส่งแล้ว! (เวลา: {timestamp})")
                        print(f"   📸 Full Image: {full_image_path}")
                        print(f"   📸 Person Image: {person_image_path}\n")

                # วาดกรอบและจุดศูนย์กลาง
                color = (0, 0, 255) if inside_zone else (0, 255, 0)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.circle(frame, (int(center_x), int(center_y)), 8, color, -1)
                
                tag = f"{label} {conf:.2f}"
                if inside_zone:
                    tag += " ⚠️ IN-ZONE"
                cv2.putText(frame, tag, (int(x1), int(y1)-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # แสดงข้อมูลเพิ่มเติม
    cv2.putText(frame, "Elder Ma Nee Ma - Image Alert System", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"Zone: Polygon ({len(zone_polygon)} points)", (10, 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    status = "ImgBB Active" if IMGBB_API_KEY else "Local Save Only"
    status_color = (0, 255, 0) if IMGBB_API_KEY else (0, 165, 255)
    cv2.putText(frame, f"Status: {status}", (10, 90),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    # แสดงภาพ
    cv2.imshow("YOLO Detection - Image Alert", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("\n" + "="*70)
print("👋 ปิดโปรแกรมเรียบร้อย")
print(f"📸 รูปภาพทั้งหมดถูกบันทึกที่: {ALERT_FOLDER}/")
print("="*70)