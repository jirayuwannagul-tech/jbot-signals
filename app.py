from flask import Flask, render_template
import os # เพิ่มการนำเข้า os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    # ดึงค่า PORT จากระบบ ถ้าไม่มีให้ใช้ 5000 (สำหรับรันในเครื่อง)
    port = int(os.environ.get("PORT", 5000))
    # ตั้ง host เป็น 0.0.0.0 เพื่อให้ภายนอกเข้าถึงได้
    app.run(host='0.0.0.0', port=port)