import cv2

# โหลดภาพ (เปลี่ยนเป็นภาพของคุณ)
img = cv2.imread('Video/testphoto.png')
clone = img.copy()

# เก็บพิกัดสองจุด
points = []

def draw_rectangle(event, x, y, flags, param):
    global points, img

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))

        # ถ้าคลิกครบ 2 จุดแล้ว
        if len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]

            # วาดวงกลมโดยใช้กรอบสองจุดเป็นเส้นผ่านศูนย์กลาง
            # หาจุดศูนย์กลางและรัศมีให้วงกลมพอดีกับสี่เหลี่ยมที่ผู้ใช้ลาก
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            radius = min(abs(x2 - x1), abs(y2 - y1)) // 2
            cv2.circle(img, (cx, cy), radius, (0, 255, 0), 2)
            cv2.imshow("Image", img)

            print(f"center=({cx},{cy}), radius={radius}, x1={x1}, y1={y1}, x2={x2}, y2={y2}")

cv2.namedWindow("Image")
cv2.setMouseCallback("Image", draw_rectangle)

while True:
    cv2.imshow("Image", img)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):  # กด ESC เพื่อออก
        break
    elif key == ord("r"):  # กด r เพื่อล้างจุดแล้วเริ่มใหม่
        img = clone.copy()
        points = []

cv2.destroyAllWindows()
