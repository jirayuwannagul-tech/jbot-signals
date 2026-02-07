from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import requests
import json

app = Flask(__name__)

# ============================================
# LAYER 1: CONFIGURATION
# ============================================
LINE_CHANNEL_ACCESS_TOKEN = 'PWgMZOGpbkRwRvPSTKQI4MnNsD8NEY5HYwCJT/Ge5KegcYNIdhJbZlQaww6GEYAYZ62Dw4F1/+0iOuz4FlZjlo0+npM9gaeLy1m0ujcMDqzZwy4NqgfYdrSV9/Hgv1lKk/OKmiq2kpG8hy3tTKVbjAdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'b113f6e5414f3bcc23acbea86c4cee71'
ADMIN_LINE_ID = 'U8e5ae7c7887eca3cdf7831bf1ede1d3f'

database_url = os.environ.get('DATABASE_URL', 'sqlite:///jbot_members.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============================================
# LAYER 2: DATABASE MODEL
# ============================================
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

# ============================================
# LAYER 3: LINE MESSAGING FUNCTIONS
# ============================================
def send_line_message(user_id, text):
    """ส่งข้อความธรรมดา"""
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {'to': user_id, 'messages': [{'type': 'text', 'text': text}]}
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code

def send_flex_message(user_id, flex_content):
    """ส่ง Flex Message (ปุ่มสวยๆ)"""
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    payload = {
        'to': user_id,
        'messages': [{
            'type': 'flex',
            'altText': 'มีสมาชิกใหม่รอการอนุมัติ',
            'contents': flex_content
        }]
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code

def get_line_profile(user_id):
    """ดึงชื่อจาก LINE"""
    url = f'https://api.line.me/v2/bot/profile/{user_id}'
    headers = {'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get('displayName', 'สมาชิกใหม่')
    except:
        pass
    return 'สมาชิกใหม่'

def create_approval_flex(member_id, display_name, line_id):
    """สร้าง Flex Message พร้อมปุ่มเปิดหน้าเว็บ"""
    return {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🔔 สมาชิกใหม่",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#1E90FF"
                }
            ],
            "backgroundColor": "#132844",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "👤 ชื่อ:", "color": "#94A3B8", "size": "sm", "flex": 2},
                        {"type": "text", "text": display_name, "color": "#FFFFFF", "size": "sm", "flex": 5, "wrap": True}
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "🆔 User ID:", "color": "#94A3B8", "size": "xs", "flex": 2},
                        {"type": "text", "text": line_id, "color": "#94A3B8", "size": "xxs", "flex": 5, "wrap": True}
                    ],
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "lg"
                },
                {
                    "type": "text",
                    "text": "กดปุ่มด้านล่างเพื่อจัดการ",
                    "size": "sm",
                    "color": "#FFD700",
                    "margin": "lg",
                    "weight": "bold"
                }
            ],
            "backgroundColor": "#0A1628"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "🎛️ เปิดหน้าจัดการ",
                        "uri": "https://web-production-f17e.up.railway.app/admin/dashboard"
                    },
                    "style": "primary",
                    "color": "#10B881",
                    "height": "sm"
                }
            ],
            "backgroundColor": "#0A1628",
            "spacing": "sm"
        }
    }

# ============================================
# LAYER 4: LINE WEBHOOK HANDLER
# ============================================
@app.route("/callback/admin", methods=['POST'])
def callback():
    json_data = request.get_json()
    if not json_data or 'events' not in json_data: 
        return 'OK'
        
    for event in json_data['events']:
        # === POSTBACK EVENT (กดปุ่ม) ===
        if event['type'] == 'postback':
            data = event['postback']['data']
            params = dict(item.split('=') for item in data.split('&'))
            
            action = params.get('action')
            member_id = int(params.get('member_id'))
            
            member = Member.query.get(member_id)
            if not member:
                return 'OK'
            
            # อนุมัติ
            if action == 'approve':
                member.is_active = True
                member.expiry_date = datetime.now() + timedelta(days=30)
                db.session.commit()
                
                # ส่งข้อความหาลูกค้า
                send_line_message(
                    member.line_id,
                    f"✅ ยินดีด้วยครับ!\n\n"
                    f"👤 คุณ {member.display_name}\n"
                    f"🤖 สถานะ: VIP Active\n"
                    f"📅 หมดอายุ: {member.expiry_date.strftime('%d/%m/%Y')}\n\n"
                    f"🎯 ขั้นตอนถัดไป:\n"
                    f"แอดบอทจ่าเพื่อรับสัญญาณเทรด\n"
                    f"👉 https://line.me/R/ti/p/@684zmxdd\n\n"
                    f"ขอให้กำไรปังๆ นะครับ! 🚀"
                )
                
                # ตอบกลับแอดมิน
                send_line_message(
                    ADMIN_LINE_ID,
                    f"✅ อนุมัติสำเร็จ!\n\n"
                    f"👤 {member.display_name}\n"
                    f"📅 หมดอายุ: {member.expiry_date.strftime('%d/%m/%Y')}"
                )
            
            # ปิดวาล์ว
            elif action == 'reject':
                member.is_active = False
                db.session.commit()
                
                # ส่งข้อความหาลูกค้า
                send_line_message(
                    member.line_id,
                    "❌ ขออภัยครับ\n\n"
                    "ระบบไม่สามารถยืนยันการชำระเงินได้\n"
                    "กรุณาติดต่อแอดมินเพื่อตรวจสอบอีกครั้ง"
                )
                
                # ตอบกลับแอดมิน
                send_line_message(
                    ADMIN_LINE_ID,
                    f"🚫 ปิดวาล์วแล้ว\n\n"
                    f"👤 {member.display_name}\n"
                    f"🆔 {member.line_id}"
                )
        
        # === FOLLOW EVENT ===
        elif event['type'] == 'follow':
            user_id = event['source']['userId']
            display_name = get_line_profile(user_id)
            
            welcome_msg = (
                f"สวัสดีครับคุณ {display_name}! 🎉\n"
                f"ยินดีต้อนรับสู่ J-Bot Signals\n\n"
                
                "📊 ระบบนี้คืออะไร?\n"
                "เราเป็นระบบวิเคราะห์สัญญาณเทรดคริปโตอัตโนมัติ\n"
                "ให้สัญญาณ Buy/Sell พร้อม Stop Loss\n\n"
                
                "💰 ค่าบริการ: 490 บาท/เดือน\n\n"
                
                "📌 ขั้นตอนการสมัคร:\n"
                "1. โอนเงิน 490 บาท\n"
                "   กสิกรไทย: 024-3-44305-9\n"
                "   ชื่อบัญชี: จิรายุ วรรณกุล\n\n"
                
                "2. ส่งรูปสลิปมาที่บอทนี้\n\n"
                
                "3. รอแอดมินตรวจสอบ (15 นาที)\n\n"
                
                "4. หลังอนุมัติ แอดมินจะส่งลิงก์บอทจ่า\n"
                "   เพื่อรับสัญญาณเทรด 24 ชม."
            )
            send_line_message(user_id, welcome_msg)

        # === IMAGE EVENT (ส่งสลิป) ===
        elif event['type'] == 'message' and event['message']['type'] == 'image':
            user_id = event['source']['userId']
            display_name = get_line_profile(user_id)
            
            # เช็คว่ามีในระบบแล้วหรือยัง
            existing = Member.query.filter_by(line_id=user_id).first()
            if not existing:
                new_member = Member(
                    line_id=user_id,
                    display_name=display_name,
                    expiry_date=datetime.now(),
                    is_active=False
                )
                db.session.add(new_member)
                db.session.commit()
                member_id = new_member.id
            else:
                member_id = existing.id
            
            # ส่ง Flex Message พร้อมปุ่มไปหาแอดมิน
            flex = create_approval_flex(member_id, display_name, user_id)
            send_flex_message(ADMIN_LINE_ID, flex)
            
            # ตอบกลับลูกค้า
            send_line_message(
                user_id,
                "✅ ได้รับสลิปแล้วครับ!\n\n"
                "แอดมินจะตรวจสอบและอนุมัติภายใน 15 นาที\n"
                "รอสักครู่นะครับ ☕"
            )

        # === TEXT EVENT ===
        elif event['type'] == 'message' and event['message']['type'] == 'text':
            user_id = event['source']['userId']
            send_line_message(
                user_id,
                "📌 กรุณาส่งรูปสลิปโอนเงินครับ\n\n"
                "ยังไม่ได้โอนใช่ไหม?\n"
                "โอนที่: กสิกรไทย 024-3-44305-9"
            )
            
    return 'OK'

# ============================================
# LAYER 5: WEB ROUTES
# ============================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    # ดึงสมาชิกทั้งหมด
    all_members = Member.query.all()
    now = datetime.now()
    
    # แยกตามสถานะ
    active_members = []
    pending_members = []
    expired_members = []
    
    for m in all_members:
        if m.is_active and m.expiry_date > now:
            active_members.append(m)
        elif not m.is_active:
            pending_members.append(m)
        elif m.expiry_date <= now:
            expired_members.append(m)
    
    # รวมเรียงลำดับ: Active → Pending → Expired
    members = active_members + pending_members + expired_members
    
    # นับสถิติ
    total = len(all_members)
    active = len(active_members)
    pending = len(pending_members)
    expired = len(expired_members)
    
    return render_template('admin.html', 
                         members=members,
                         now=now,
                         total=total,
                         active=active,
                         pending=pending,
                         expired=expired)

@app.route('/admin/approve/<int:member_id>')
def approve_member(member_id):
    """อนุมัติจากหน้าเว็บ (สำรอง)"""
    member = db.session.get(Member, member_id)
    if member:
        member.is_active = True
        member.expiry_date = datetime.now() + timedelta(days=30)
        db.session.commit()
        
        send_line_message(
            member.line_id,
            f"✅ ยินดีด้วยครับ!\n\n"
            f"👤 คุณ {member.display_name}\n"
            f"🤖 สถานะ: VIP Active\n"
            f"📅 หมดอายุ: {member.expiry_date.strftime('%d/%m/%Y')}\n\n"
            f"แอดบอทจ่า:\n"
            f"👉 https://line.me/R/ti/p/@684zmxdd"
        )
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/check-expiry')
def check_expiry():
    today = datetime.now()
    warning_date = today + timedelta(days=3)
    
    members = Member.query.filter_by(is_active=True).all()
    
    for m in members:
        if m.expiry_date <= today:
            m.is_active = False
            send_line_message(
                m.line_id,
                "❌ สมาชิกหมดอายุแล้วครับ\n\n"
                "ต้องการต่ออายุส่งสลิปมาได้เลย"
            )
        elif today < m.expiry_date <= warning_date:
            days = (m.expiry_date - today).days
            send_line_message(
                m.line_id,
                f"⚠️ เหลือเวลาอีก {days} วัน\n"
                f"📅 หมดอายุ: {m.expiry_date.strftime('%d/%m/%Y')}\n\n"
                "อย่าลืมต่ออายุนะครับ"
            )
    
    db.session.commit()
    return "✅ Checked"

@app.route('/admin/create-test-data')
def create_test_data():
    """สร้างสมาชิกทดสอบ"""
    Member.query.delete()
    m1 = Member(line_id='U1', display_name='Active 1', is_active=True, expiry_date=datetime.now()+timedelta(days=15))
    m2 = Member(line_id='U2', display_name='Active 2', is_active=True, expiry_date=datetime.now()+timedelta(days=20))
    m3 = Member(line_id='U3', display_name='Pending 1', is_active=False, expiry_date=datetime.now()+timedelta(days=30))
    m4 = Member(line_id='U4', display_name='Pending 2', is_active=False, expiry_date=datetime.now()+timedelta(days=30))
    m5 = Member(line_id='U5', display_name='Expired 1', is_active=True, expiry_date=datetime.now()-timedelta(days=5))
    m6 = Member(line_id='U6', display_name='Expired 2', is_active=True, expiry_date=datetime.now()-timedelta(days=10))
    db.session.add_all([m1, m2, m3, m4, m5, m6])
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ============================================
# LAYER 6: SERVER START
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)