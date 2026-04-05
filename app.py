import os
from flask import Flask, render_template_string, request, session, redirect, url_for
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
# 建議將 secret_key 也放在環境變數，這裡先設為固定值
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'pet_mission_secure_key_2026')

# --- 1. Cloudinary 配置 (透過環境變數讀取) ---
cloudinary.config( 
  cloud_name = os.environ.get('CLOUDINARY_NAME'), 
  api_key = os.environ.get('CLOUDINARY_API_KEY'), 
  api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
  secure = True
)

# --- 2. 管理員資料 ---
ADMIN_USER = "wxp800218"
ADMIN_PW = "0981161269"

# 模擬資料庫 (注意：Render 重啟後會清空)
pets_data = []
searched_paths = []

# --- 3. HTML 模板 ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>尋獲毛小孩任務</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: "Helvetica Neue", Helvetica, Arial, "Microsoft JhengHei", sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; background: #f4f7f6; }
        header { background: #2c3e50; color: white; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; z-index: 1000; }
        #map { flex: 1; width: 100%; }
        .form-panel { padding: 15px; background: white; border-top: 3px solid #27ae60; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); }
        .btn { padding: 8px 15px; cursor: pointer; border: none; border-radius: 4px; font-weight: bold; }
        .btn-add { background: #27ae60; color: white; }
        .btn-del { background: #e74c3c; color: white; width: 100%; margin-top: 8px; font-size: 12px; }
        input { padding: 8px; margin: 4px; border: 1px solid #ddd; border-radius: 4px; }
        .popup-card { width: 200px; text-align: center; }
        .comment-box { text-align: left; font-size: 12px; background: #f9f9f9; padding: 5px; max-height: 60px; overflow-y: auto; margin-top: 5px; border-radius: 4px; }
    </style>
</head>
<body>

<header>
    <div>
        <h3 style="margin:0;">🐾 尋獲毛小孩任務</h3>
    </div>
    <div>
        {% if is_admin %}
            <span style="color:#f1c40f;">👑 管理員模式</span> | <a href="/logout" style="color:white; text-decoration:none;">登出</a>
        {% else %}
            <form action="/login" method="POST" style="display: inline;">
                <input type="text" name="username" placeholder="帳號" style="width:80px; padding:3px;">
                <input type="password" name="password" placeholder="密碼" style="width:80px; padding:3px;">
                <button type="submit" style="padding:3px 8px;">登入</button>
            </form>
        {% endif %}
    </div>
</header>

<div id="map"></div>

<div class="form-panel">
    <strong>📢 快速發布：請點擊地圖位置</strong>
    <form action="/add_pet" method="POST" enctype="multipart/form-data" style="margin-top:10px;">
        <input type="hidden" id="lat" name="lat" required>
        <input type="hidden" id="lng" name="lng" required>
        <input type="text" name="name" placeholder="毛小孩稱呼" required>
        <input type="text" name="phone" placeholder="聯絡電話" required>
        <input type="text" name="desc" placeholder="特徵描述" style="width: 200px;" required>
        <label>照片：</label><input type="file" name="photo" accept="image/*" required>
        <button type="submit" class="btn btn-add">發布任務</button>
    </form>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    var map = L.map('map').setView([23.6, 121.0], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    // 點擊選取座標
    var tempMarker;
    map.on('click', function(e) {
        document.getElementById('lat').value = e.latlng.lat;
        document.getElementById('lng').value = e.latlng.lng;
        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(e.latlng).addTo(map).bindTooltip("刊登位置").openTooltip();
    });

    // 修正 JavaScript 判斷管理員的邏輯，避免語法錯誤
    var isAdmin = {{ 'true' if is_admin else 'false' }};

    var pets = {{ pets | tojson }};
    pets.forEach(function(pet) {
        var marker = L.marker([pet.lat, pet.lng]).addTo(map);
        var popupContent = `
            <div class="popup-card">
                <img src="${pet.photo_url}" style="width:100%; border-radius:5px;">
                <h4 style="margin:5px 0;">${pet.name}</h4>
                <div style="color:#e67e22; font-weight:bold;">📞 ${pet.phone}</div>
                <p style="font-size:12px; color:#666;">${pet.desc}</p>
                <div class="comment-box">
                    ${pet.comments.length > 0 ? pet.comments.map(c => '<div>• '+c+'</div>').join('') : '尚無回報'}
                </div>
                <form action="/comment/${pet.id}" method="POST" style="margin-top:5px;">
                    <input type="text" name="msg" placeholder="回報看見地點" style="width:100px; font-size:11px;">
                    <button type="submit" style="font-size:11px;">送出</button>
                </form>
        `;

        if (isAdmin) {
            popupContent += `<a href="/delete/${pet.id}"><button class="btn btn-del">🗑️ 刪除資訊</button></a>`;
        }
        
        popupContent += `</div>`;
        marker.bindPopup(popupContent);
    });

    var paths = {{ paths | tojson }};
    if (paths.length > 0) L.polyline(paths, {color: '#27ae60', weight: 3, opacity: 0.5}).addTo(map);
</script>
</body>
</html>
"""

# --- 4. 路由 ---

@app.route('/')
def index():
    # 這裡確保 is_admin 一定有布林值，不會讓模板崩潰
    is_admin = session.get('is_admin', False)
    return render_template_string(HTML_TEMPLATE, pets=pets_data, paths=searched_paths, is_admin=is_admin)

@app.route('/login', methods=['POST'])
def login():
    u = request.form.get('username')
    p = request.form.get('password')
    if u == ADMIN_USER and p == ADMIN_PW:
        session['is_admin'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/add_pet', methods=['POST'])
def add_pet():
    try:
        file = request.files.get('photo')
        if not file:
            return "未偵測到上傳照片", 400
        
        # 上傳至 Cloudinary
        upload_result = cloudinary.uploader.upload(file)
        photo_url = upload_result.get('secure_url')

        new_pet = {
            "id": len(pets_data) + 1,
            "name": request.form.get('name'),
            "phone": request.form.get('phone'),
            "lat": float(request.form.get('lat')),
            "lng": float(request.form.get('lng')),
            "desc": request.form.get('desc'),
            "comments": [],
            "photo_url": photo_url
        }
        pets_data.append(new_pet)
        searched_paths.append([new_pet['lat'], new_pet['lng']])
        return redirect(url_for('index'))
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return f"伺服器錯誤 (可能與 Cloudinary 連線有關): {e}", 500

@app.route('/delete/<int:pet_id>')
def delete_pet(pet_id):
    global pets_data
    if session.get('is_admin'):
        pets_data = [p for p in pets_data if p['id'] != pet_id]
    return redirect(url_for('index'))

@app.route('/comment/<int:pet_id>', methods=['POST'])
def add_comment(pet_id):
    msg = request.form.get('msg')
    if msg:
        for pet in pets_data:
            if pet['id'] == pet_id:
                pet['comments'].append(msg)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # 建議在正式環境不要開啟 debug=True，這裡為了讓你方便查看錯誤而保留
    app.run(debug=True)
