import cv2
import numpy as np

# ตัวแปรเก็บจุดที่เลือก
points = []
frame = None
original_frame = None

def mouse_callback(event, x, y, flags, param):
    """ฟังก์ชันสำหรับจับเหตุการณ์คลิกเมาส์"""
    global points, frame, original_frame
    
    if event == cv2.EVENT_LBUTTONDOWN:  # คลิกซ้าย
        points.append([x, y])
        print(f"✅ เพิ่มจุดที่ {len(points)}: ({x}, {y})")
        
        # วาดจุดและเส้นเชื่อมบนภาพ
        frame = original_frame.copy()
        
        # วาดทุกจุด
        for i, point in enumerate(points):
            cv2.circle(frame, tuple(point), 8, (0, 255, 0), -1)
            cv2.putText(frame, f"{i+1}", (point[0]+10, point[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # วาดเส้นเชื่อม
        if len(points) > 1:
            for i in range(len(points) - 1):
                cv2.line(frame, tuple(points[i]), tuple(points[i+1]), (0, 255, 255), 2)
            # เส้นเชื่อมจุดสุดท้ายกับจุดแรก (แสดงตัวอย่าง)
            cv2.line(frame, tuple(points[-1]), tuple(points[0]), (255, 0, 255), 2)
        
        # แสดงจำนวนจุด
        cv2.putText(frame, f"Points: {len(points)}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "Left Click: Add Point | Right Click: Undo | Enter: Save & Exit", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Polygon Point Selector", frame)
    
    elif event == cv2.EVENT_RBUTTONDOWN:  # คลิกขวา = ลบจุดล่าสุด
        if points:
            removed = points.pop()
            print(f"❌ ลบจุด: {removed}")
            
            # วาดใหม่
            frame = original_frame.copy()
            
            for i, point in enumerate(points):
                cv2.circle(frame, tuple(point), 8, (0, 255, 0), -1)
                cv2.putText(frame, f"{i+1}", (point[0]+10, point[1]-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if len(points) > 1:
                for i in range(len(points) - 1):
                    cv2.line(frame, tuple(points[i]), tuple(points[i+1]), (0, 255, 255), 2)
                cv2.line(frame, tuple(points[-1]), tuple(points[0]), (255, 0, 255), 2)
            
            cv2.putText(frame, f"Points: {len(points)}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, "Left Click: Add Point | Right Click: Undo | Enter: Save & Exit", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("Polygon Point Selector", frame)

def main():
    global frame, original_frame, points
    
    print("="*60)
    print("🎯 โปรแกรมเลือกจุด Polygon สำหรับ Elder Ma Nee Ma")
    print("="*60)
    
    # เลือกแหล่งที่มาของภาพ
    print("\n📹 กรุณาเลือกแหล่งที่มาของภาพ:")
    print("1. ไฟล์วิดีโอ")
    print("2. กล้องเว็บแคม")
    choice = input("เลือก (1/2): ").strip()
    
    if choice == "1":
        video_path = input("📁 ใส่ path ของวิดีโอ (เช่น Video/video.mp4): ").strip()
        cap = cv2.VideoCapture(video_path)
    else:
        cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ ไม่สามารถเปิดวิดีโอได้!")
        return
    
    # อ่านเฟรมแรก
    ret, original_frame = cap.read()
    if not ret:
        print("❌ ไม่สามารถอ่านภาพได้!")
        cap.release()
        return
    
    frame = original_frame.copy()
    cap.release()
    
    print("\n✨ วิธีใช้งาน:")
    print("   🖱️  คลิกซ้าย = เพิ่มจุด")
    print("   🖱️  คลิกขวา = ลบจุดล่าสุด")
    print("   ⌨️  กด Enter = บันทึกและออก")
    print("   ⌨️  กด ESC = ยกเลิก")
    print("\n⏳ รอการเลือกจุด...\n")
    
    # สร้างหน้าต่างและผูก callback
    cv2.namedWindow("Polygon Point Selector")
    cv2.setMouseCallback("Polygon Point Selector", mouse_callback)
    
    # แสดงคำแนะนำบนภาพ
    cv2.putText(frame, "Left Click: Add Point | Right Click: Undo | Enter: Save & Exit", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imshow("Polygon Point Selector", frame)
    
    # รอจนกว่าจะกด Enter หรือ ESC
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter
            if len(points) >= 3:
                break
            else:
                print("⚠️ ต้องเลือกอย่างน้อย 3 จุด!")
        elif key == 27:  # ESC
            print("❌ ยกเลิกการเลือกจุด")
            cv2.destroyAllWindows()
            return
    
    cv2.destroyAllWindows()
    
    # แสดงผลลัพธ์
    print("\n" + "="*60)
    print("✅ บันทึกจุดเรียบร้อย!")
    print("="*60)
    print(f"\n📊 จำนวนจุดทั้งหมด: {len(points)} จุด\n")
    
    print("📋 รายการพิกัด:")
    for i, point in enumerate(points, 1):
        print(f"   จุดที่ {i}: ({point[0]}, {point[1]})")
    
    print("\n" + "="*60)
    print("🎉 โค้ด Python สำหรับใช้ใน Elder Ma Nee Ma:")
    print("="*60)
    print("\n# วางโค้ดนี้ในโปรแกรมหลัก")
    print("zone_polygon = np.array([")
    for point in points:
        print(f"    [{point[0]}, {point[1]}],")
    print("], dtype=np.int32)")
    print("\n" + "="*60)
    
    # บันทึกลงไฟล์
    save_choice = input("\n💾 ต้องการบันทึกลงไฟล์ zone_config.txt หรือไม่? (y/n): ").strip().lower()
    if save_choice == 'y':
        with open("zone_config.txt", "w", encoding="utf-8") as f:
            f.write("# Elder Ma Nee Ma - Zone Configuration\n")
            f.write(f"# จำนวนจุด: {len(points)}\n")
            f.write("# วันที่สร้าง: " + str(np.datetime64('now')) + "\n\n")
            f.write("zone_polygon = np.array([\n")
            for point in points:
                f.write(f"    [{point[0]}, {point[1]}],\n")
            f.write("], dtype=np.int32)\n")
        print("✅ บันทึกไฟล์ zone_config.txt เรียบร้อย!")
    
    print("\n👋 เสร็จสิ้น! นำโค้ดไปใช้ได้เลยครับ\n")

if __name__ == "__main__":
    main()