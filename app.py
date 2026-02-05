from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจ LINE (พี่เอา Token ที่ก๊อปมาวางตรงนี้) ---
LINE_CHANNEL_ACCESS_TOKEN = 'วาง Access Token ยาวๆ ตรงนี้'
LINE_CHANNEL_SECRET = 'วาง Channel Secret ตรงนี้'

# --- 2. ตั้งค่าระบบฐานข้อมูล ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jbot_members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# โครงสร้างฐานข้อมูลสมาชิก
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# --- 3. ฟังก์ชันบอทแอดมิน (ส่งข้อความหาลูกค้า) ---
def send_line_message(user_id, text):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        'to': user_id,
        'messages': [{'type': 'text', 'text': text}]
    }
    requests.post(url, headers=headers, json=payload)

# Webhook สำหรับรับข้อมูลจาก LINE
@app.route("/callback/admin", methods=['POST'])
def callback():
    body = request.get_json()
    if not body or 'events' not in body: return 'OK'
    
    for event in body['events']:
        if event['type'] == 'message':
            user_id = event['source']['userId']
            msg_text = event['message'].get('text', '')

            # ถ้าลูกค้าทักมาครั้งแรก ให้ส่งวิธีชำระเงิน
            reply_text = "สวัสดีครับ J-Bot ยินดีต้อนรับ!\nกรุณาโอนเงิน 490 บาทมาที่\nกสิกรไทย: 024-3-44305-9\nจิรายุ วรรณกุล\nแล้วส่งรูปสลิปพร้อมพิมพ์ 'แจ้งโอน' ครับ"
            
            # ตรวจสอบเบื้องต้น (แบบง่าย) ถ้าลูกค้าบอกแจ้งโอน ให้สร้างชื่อในตารางรอไว้
            if 'แจ้งโอน' in msg_text:
                existing = Member.query.filter_by(line_id=user_id).first()
                if not existing:
                    new_member = Member(line_id=user_id, expiry_date=datetime.now(), is_active=False)
                    db.session.add(new_member)
                    db.session.commit()
                reply_text = "ได้รับเรื่องแล้วครับ แอดมินจะรีบตรวจสอบสลิปและอนุมัติให้ภายใน 15 นาทีครับ"
            
            send_line_message(user_id, reply_text)
    return 'OK'

# --- 4. หน้าเว็บจัดการสมาชิก (Admin Dashboard) ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    members = Member.query.all()
    return render_template('admin.html', members=members, now=datetime.now())

@app.route('/admin/approve/<int:member_id>')
def approve_member(member_id):
    member = Member.query.get(member_id)
    if member:
        member.is_active = True
        member.expiry_date = datetime.now() + timedelta(days=30)
        db.session.commit()
        # แจ้งเตือนลูกค้าผ่านบอททันทีเมื่ออนุมัติ
        send_line_message(member.line_id, "✅ อนุมัติเรียบร้อย! คุณเริ่มรับสัญญาณได้ทันทีครับ\nแอดบอทจ่าที่นี่: [ลิงก์บอทจ่า]")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/block/<int:member_id>')
def block_member(member_id):
    member = Member.query.get(member_id)
    if member:
        member.is_active = False
        db.session.commit()
        send_line_message(member.line_id, "❌ สัญญาณของคุณถูกปิดชั่วคราว โปรดติดต่อแอดมินครับ")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)