from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    # Railway จะส่งเลขช่อง (Port) มาให้ผ่านคำว่า "PORT"
    port = int(os.environ.get("PORT", 5000))
    # ต้องระบุ host='0.0.0.0' เพื่อให้ Railway มองเห็นเว็บเรา
    app.run(host='0.0.0.0', port=port)