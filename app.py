from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# 1. ตั้งค่าฐานข้อมูลสมาชิก (สร้างไฟล์ชื่อ jbot_members.db อัตโนมัติ)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jbot_members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. สร้างโครงสร้างตารางสมุดจดชื่อสมาชิก
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    line_id = db.Column(db.String(100), unique=True, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=False) # วาล์วเปิด-ปิดสัญญาณ

# สร้างฐานข้อมูลทันทีเมื่อรันแอป
with app.app_context():
    db.create_all()

# --- หน้าบ้าน (สำหรับลูกค้า) ---
@app.route('/')
def home():
    return render_template('index.html')

# --- หน้าแอดมิน (สำหรับคุณจัดการสมาชิก) ---
@app.route('/admin/dashboard')
def admin_dashboard():
    # ดึงรายชื่อสมาชิกทั้งหมดจากฐานข้อมูลมาแสดงผล
    members = Member.query.all()
    return render_template('admin.html', members=members)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

    # ฟังก์ชันสำหรับ "เปิดวาล์ว" และ "เพิ่มวันหมดอายุ"
@app.route('/admin/approve/<int:member_id>')
def approve_member(member_id):
    member = Member.query.get(member_id)
    if member:
        member.is_active = True
        # ตั้งวันหมดอายุเป็น 30 วันนับจากตอนนี้
        member.expiry_date = datetime.now() + timedelta(days=30)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ฟังก์ชันสำหรับ "ปิดวาล์ว" (ตัดสัญญาณ)
@app.route('/admin/block/<int:member_id>')
def block_member(member_id):
    member = Member.query.get(member_id)
    if member:
        member.is_active = False
        db.session.commit()
    return redirect(url_for('admin_dashboard'))