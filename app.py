from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)

# ============================================
# LAYER 1: CONFIGURATION (ตั้งค่ากุญแจสำคัญ)
# ============================================
# 1. LINE Messaging API (Messaging API)
LINE_CHANNEL_ACCESS_TOKEN = 'vogysToPeoVbYteQDckcUyYFVVRKB4lq1uXaqTT7vL2mHplXUghEB+GGUCwSN/5Z62Dw4F1/+0iOuz4FlZjlo0+npM9gaeLy1m0ujcMDqylpummN0Ib+EesqIzdvhT0jYVLOwCKh+FURhzDP/JLsAdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'b113f6e5414f3bcc23acbea86c4cee71'

# 2. Admin ID (ก๊อป User ID ของพี่จากหน้า Dashboard มาใส่ที่นี่)
# เพื่อให้บอทส่งข้อความแจ้งเตือนหาพี่ได้โดยตรง
ADMIN_LINE_ID = 'ใส่_USER_ID_ของพี่ที่นี่' 

# 3. Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jbot_members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============================================
# LAYER 2: DATABASE MODELS (โครงสร้างข้อมูล)
# ============================================
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.String(100), unique=True, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# ============================================
# LAYER 3: HELPER FUNCTIONS (ฟังก์ชันช่วย)
# ============================================
# ฟังก์ชันหลักในการส่งข้อความ LINE
def send_line_message(user_id, text):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {'to': user_id, 'messages': [{'type': 'text', 'text': text}]}
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code

# ฟังก์ชันแจ้งเตือนแอดมิน (เปลี่ยนจาก Notify มาเป็น Push Message)
def notify_admin(message):
    if ADMIN_LINE_ID != 'ใส่_USER_ID_ของพี่ที่นี่':
        send_line_message(ADMIN_LINE_ID, message)

# ============================================
# LAYER 4: LINE WEBHOOK (ระบบตอบโต้บอท)
# ============================================
@app.route("/callback/admin", methods=['POST'])
def callback():
    json_data = request.get_json()
    if not json_data or 'events' not in json_data: 
        return 'OK'
        
    for event in json_data['events']:
        user_id = event['source']['userId']

        # A. ลูกค้าแอดเพื่อนใหม่
        if event['type'] == 'follow':
            welcome_msg = (
                "สวัสดีครับ! ยินดีต้อนรับสู่ J-Bot Signals 🤖\n\n"
                "💰 ค่าบริการ VIP: 490 บาท/เดือน\n"
                "ช่องทางโอนเงิน:\n"
                "กสิกรไทย: 024-3-44305-9\n"
                "ชื่อบัญชี: จิรายุ วรรณกุล\n\n"
                "โอนแล้วส่ง 'รูปสลิป' มาได้เลยครับ"
            )
            send_line_message(user_id, welcome_msg)

        # B. ลูกค้าส่งสลิป (รูปภาพ)
        elif event['type'] == 'message' and event['message']['type'] == 'image':
            existing = Member.query.filter_by(line_id=user_id).first()
            if not existing:
                new_member = Member(line_id=user_id, expiry_date=datetime.now(), is_active=False)
                db.session.add(new_member)
                db.session.commit()
            
            # แจ้งเตือนแอดมิน
            notify_admin(f"📢 มีสลิปใหม่เข้า!\nUser ID: {user_id}\nตรวจที่: https://web-production-f17e.up.railway.app/admin/dashboard")
            
            send_line_message(user_id, "ได้รับสลิปแล้วครับ! แอดมินจะรีบตรวจสอบและอนุมัติให้ภายใน 15 นาทีครับ")

        # C. ลูกค้าพิมพ์ข้อความ
        elif event['type'] == 'message' and event['message']['type'] == 'text':
            send_line_message(user_id, "หากต้องการสมัคร VIP รบกวนส่งรูปสลิปโอนเงินได้เลยครับ")
            
    return 'OK'

# ============================================
# LAYER 5: ADMIN SYSTEM (ระบบจัดการหลังบ้าน)
# ============================================
@app.route('/admin/dashboard')
def admin_dashboard():
    members = Member.query.all()
    return render_template('admin.html', members=members, now=datetime.now())

# ปุ่มอนุมัติ (เพิ่มเวลา 30 วัน)
@app.route('/admin/approve/<int:member_id>')
def approve_member(member_id):
    member = Member.query.get(member_id)
    if member:
        member.is_active = True
        member.expiry_date = datetime.now() + timedelta(days=30)
        db.session.commit()
        send_line_message(member.line_id, "✅ อนุมัติเรียบร้อย! เริ่มรับสัญญาณได้เลยครับ")
    return redirect(url_for('admin_dashboard'))

# ระบบเช็ควันหมดอายุ (เรียกวันละครั้ง)
@app.route('/admin/check-expiry')
def check_expiry():
    today = datetime.now()
    warning_date = today + timedelta(days=3)
    
    members = Member.query.filter_by(is_active=True).all()
    for m in members:
        if m.expiry_date <= today:
            m.is_active = False
            send_line_message(m.line_id, "❌ สมาชิกของคุณหมดอายุแล้ว รบกวนต่ออายุเพื่อรับสัญญาณต่อครับ")
        elif today < m.expiry_date <= warning_date:
            send_line_message(m.line_id, f"⚠️ อีก 3 วันสมาชิกจะหมดอายุ ({m.expiry_date.strftime('%d/%m/%Y')}) อย่าลืมต่ออายุนะครับ")
            
    db.session.commit()
    return "Checked Successfully"

# ============================================
# LAYER 6: START SERVER
# ============================================
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)