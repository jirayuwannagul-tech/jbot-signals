from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจ LINE (ใส่รหัสที่พี่ให้มาเรียบร้อยครับ) ---
LINE_CHANNEL_ACCESS_TOKEN = 'b113f6e5414f3bcc23acbea86c4cee71'
LINE_CHANNEL_SECRET = 'vogysToPeoVbYteQDckcUyYFVVRKB4lq1uXaqTT7vL2mHplXUghEB+GGUCwSN/5Z62Dw4F1/+0iOuz4FlZjlo0+npM9gaeLy1m0ujcMDqylpummN0Ib+EesqIzdvhT0jYVLOwCKh+FURhzDP/JLsAdB04t89/1O/w1cDnyilFU='

# --- 2. ตั้งค่าระบบฐานข้อมูล ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jbot_members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.String(100), unique=True, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

def send_line_message(user_id, text):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {'to': user_id, 'messages': [{'type': 'text', 'text': text}]}
    requests.post(url, headers=headers, json=payload)

# --- 3. ทางเข้าหน้าแรก (Home Page) ---
@app.route('/')
def home():
    return render_template('index.html')

# --- 4. ระบบบอทรับข้อมูล (Webhook) ---
@app.route("/callback/admin", methods=['POST'])
def callback():
    body = request.get_json()
    if not body or 'events' not in body: return 'OK'
    for event in body['events']:
        user_id = event['source']['userId']
        # ถ้าส่ง "รูปภาพ" มา (สลิป)
        if event['type'] == 'message' and event['message']['type'] == 'image':
            existing = Member.query.filter_by(line_id=user_id).first()
            if not existing:
                new_member = Member(line_id=user_id, expiry_date=datetime.now(), is_active=False)
                db.session.add(new_member)
                db.session.commit()
            send_line_message(user_id, "ได้รับรูปสลิปแล้วครับ! แอดมินจะรีบตรวจสอบและอนุมัติให้ภายใน 15 นาทีครับ")
        # ถ้าพิมพ์ "ตัวหนังสือ"
        elif event['type'] == 'message' and event['message']['type'] == 'text':
            send_line_message(user_id, "สวัสดีครับ!\nโอนเงิน 490 บาทมาที่\nกสิกร: 024-3-44305-9 (จิรายุ)\nแล้วส่งรูปสลิปมาที่นี่ได้เลยครับ")
    return 'OK'

# --- 5. หน้าเว็บจัดการสมาชิก (Admin Dashboard) ---
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
        send_line_message(member.line_id, "✅ อนุมัติเรียบร้อย! เริ่มรับสัญญาณได้เลยครับ")
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)