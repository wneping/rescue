import os
from flask import Flask, render_template_string, request, session, redirect, url_for
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = "pet_mission_secret"

# --- Cloudinary 配置 ---
cloudinary.config( 
  cloud_name = os.environ.get('CLOUDINARY_NAME'), 
  api_key = os.environ.get('CLOUDINARY_API_KEY'), 
  api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
  secure = True
)

# --- 資料與權限設定 ---
# 預設管理員資訊
ADMIN_USER = "wxp800218"
ADMIN_PW = "0981161269"

pets_data = [] # 存放所有毛小孩資訊
searched_paths = []

# --- HTML 模板 ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>尋獲毛小孩任務 - 管理員模式</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: 'Microsoft JhengHei', sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; background: #f9f9f9; }
        header { background: #2c3e50; color: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        #map { flex: 1; width: 100%; border-bottom: 3px solid #34495e; }
        .form-panel { padding: 25px; background: white; }
        .btn { padding: 10px 20px; cursor: pointer; border: none; border-radius: 5px; font-weight: bold; transition: 0.3s; }
        .btn-add { background: #27ae60; color: white; }
        .btn-add:hover { background: #2ecc71; }
        .btn-del { background: #e74c3c; color: white; width: 100%; margin-top: 10px; }
        input { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        .admin-tag { background: #f1c40f; color: #000; padding: 2px 5px; border-radius: 3px; font-size: 10px; margin-left: 5px; }
    </style>
</head>
<body>

<header>
    <div>
        <h2 style="margin:0;">🐾 尋獲毛小孩任務</h2>
        <small>人人皆可刊登，管理員專屬維護</small>
    </div>
    <div>
        {% if session.get('is_admin') %}
            <span style="color:#f1c40f;">👑 管理員已登入</span>
            <a href="/logout" style="color: white; margin-left: 15px; text-decoration: none;">[登出]</a>
        {% else %}
            <form action="/login" method="POST" style="display: inline;">
                <input type="text" name="username" placeholder="管理員帳號" required>
                <input type="password" name="password" placeholder="密碼" required>
                <button type="submit" class="btn" style="padding: 5px 10px; background:#7f8c8d; color:white;">管理登入</button>
            </form>
        {% endif %}
    </div>
</header>

<div id="map"></div>

<div class="form-panel">
    <h3>📢 快速發布：請點擊地圖位置並填寫資料</h3>
    <form action="/add_pet" method="POST" enctype="multipart/form-data">
        <input type="hidden" id="lat" name="lat" required>
        <input type="hidden" id="lng" name="lng" required>
        <input type="text" name="name" placeholder="毛小孩稱呼 (如：小黑)" required>
        <input type="text" name="phone" placeholder="您的聯絡電話" required>
        <input type="text" name="desc" placeholder="特徵描述 (如：藍色項圈、親人)" style="width: 300px;" required>
        <label>📸 上傳照片：</label>
        <input type="file" name="photo" accept="image/*" required>
        <button type="submit" class="btn btn-add">確認發布任務</button>
    </form>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    var map = L.map('map').setView([23.6, 121.0], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    var clickMarker;
    map.on('click', function(e) {
        document.getElementById('lat').value = e.latlng.lat;
        document.getElementById('lng').value = e.latlng.lng;
        if (clickMarker) map.removeLayer(clickMarker);
        clickMarker = L.marker(e.latlng, {draggable: false}).addTo(map)
            .bindTooltip("失蹤地點已選取", {permanent: true, direction: 'top'}).openTooltip();
    });

    var pets = {{ pets | tojson }};
    pets.forEach(function(pet) {
        var marker = L.marker([pet.lat, pet.lng]).addTo(map);
        var popupHTML = `
            <div style="width: 220px; text-align: center; padding: 5px;">
                <img src="${pet.photo_url}" style="width: 100%; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <b style="font-size: 18px; color: #2c3e50;">${pet.name}</b>
                <p style="margin: 5px 0; color: #e67e22; font-weight: bold;">📞 聯絡電話：${pet.phone}</p>
                <p style="font-size: 14px; color: #7f8c8d; text-align: left;">${pet.desc}</p>
                <hr>
                <form action="/comment/${pet.id}" method="POST" style="margin-bottom:10px;">
                    <input type="text" name="msg" placeholder="回報看見的地點..." style="width: 140px; font-size: 12px;">
                    <button type="submit">回報</button>
                </form>
                <div style="text-align: left; max-height: 80px; overflow-y: auto;">
                    ${pet.comments.map(c => '<div style="font-size:12px; border-bottom: 1px solid #eee; padding: 2px 0;">💬 '+c+'</div>').join('')}
                </div>
                ${ ("{{ session.get('is_admin') }}" === "True") ? '<a href="/delete/'+pet.id+'"><button class="btn btn-del">🗑️ 刪除違規/已尋獲資訊</button></a>' : '' }
            </div>
        `;
        marker.bindPopup(popupHTML);
    });

    var paths = {{ paths | tojson }};
    if (paths.length > 0) L.polyline(paths, {color: '#27ae60', weight: 4, opacity: 0.5}).addTo(map);
</script>
</body>
</html>
"""

# --- 路由 ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, pets=pets_data, paths=searched_paths)

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
    # 驗證管理員帳號密碼
    if u == ADMIN_USER and p == ADMIN_PW:
        session['is_admin'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))

@app.route('/add_pet', methods=['POST'])
def add_pet():
    file_to_upload = request.files['photo']
    if file_to_upload:
        upload_result = cloudinary.uploader.upload(file_to_upload)
        photo_url = upload_result['secure_url']
        
        new_pet = {
            "id": len(pets_data) + 1,
            "name": request.form.get('name'),
            "phone": request.form.get('phone'), # 儲存聯絡電話
            "lat": float(request.form.get('lat')),
            "lng": float(request.form.get('lng')),
            "desc": request.form.get('desc'),
            "comments": [],
            "photo_url": photo_url
        }
        pets_data.append(new_pet)
        searched_paths.append([new_pet['lat'], new_pet['lng']])
    return redirect(url_for('index'))

@app.route('/delete/<int:pet_id>')
def delete_pet(pet_id):
    global pets_data
    # 只有管理員可以刪除
    if session.get('is_admin'):
        pets_data = [p for p in pets_data if p['id'] != pet_id]
    return redirect(url_for('index'))

@app.route('/comment/<int:pet_id>', methods=['POST'])
def add_comment(pet_id):
    msg = request.form.get('msg')
    for pet in pets_data:
        if pet['id'] == pet_id: pet['comments'].append(msg)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
