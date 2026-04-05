import os
from flask import Flask, render_template_string, request, session, redirect, url_for
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

app = Flask(__name__)
app.secret_key = "pet_mission_secret"

# --- 1. Cloudinary 配置 (請填入你的資訊) ---
cloudinary.config( 
  cloud_name = "你的Cloud_Name", 
  api_key = "你的API_Key", 
  api_secret = "你的API_Secret",
  secure = True
)

# --- 2. 模擬資料庫 ---
pets_data = [
    {
        "id": 1, 
        "name": "範例小黃", 
        "lat": 25.0330, "lng": 121.5654, 
        "desc": "在101附近，有紅色項圈", 
        "user": "admin", 
        "comments": [],
        "photo_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg"
    },
]
searched_paths = []
users = {"admin": "1234"}

# --- 3. HTML 模板 (已更新圖片顯示邏輯) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>尋獲毛小孩任務 - Cloudinary 版</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: 'PingFang TC', sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        header { background: #3f51b5; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        #map { flex: 1; width: 100%; }
        .form-panel { padding: 20px; background: #fff; border-top: 2px solid #3f51b5; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); }
        .btn { padding: 8px 18px; cursor: pointer; border: none; border-radius: 4px; font-weight: bold; }
        .btn-add { background: #4CAF50; color: white; }
        .btn-del { background: #f44336; color: white; font-size: 12px; }
        input { padding: 8px; margin-right: 5px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>

<header>
    <h2>🐾 尋獲毛小孩任務 (雲端圖片版)</h2>
    <div>
        {% if session.get('user') %}
            <span>👤 {{ session['user'] }}</span>
            <a href="/logout" style="color: #ffeb3b; margin-left: 10px; text-decoration: none;">登出</a>
        {% else %}
            <form action="/login" method="POST" style="display: inline;">
                <input type="text" name="username" placeholder="帳號" required>
                <input type="password" name="password" placeholder="密碼" required>
                <button type="submit" class="btn">登入</button>
            </form>
        {% endif %}
    </div>
</header>

<div id="map"></div>

<div class="form-panel">
    <h3>📢 刊登走丟資訊 (請先點擊地圖位置)</h3>
    <form action="/add_pet" method="POST" enctype="multipart/form-data">
        <input type="hidden" id="lat" name="lat" required>
        <input type="hidden" id="lng" name="lng" required>
        <input type="text" name="name" placeholder="毛小孩名字/特徵" required>
        <input type="text" name="desc" placeholder="詳細描述 (例如：花色、項圈)" style="width: 250px;" required>
        <label>照片：</label><input type="file" name="photo" accept="image/*" required>
        <button type="submit" class="btn btn-add">確認發布</button>
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
        clickMarker = L.marker(e.latlng, {opacity: 0.7}).addTo(map).bindTooltip("刊登位置").openTooltip();
    });

    var pets = {{ pets | tojson }};
    pets.forEach(function(pet) {
        var marker = L.marker([pet.lat, pet.lng]).addTo(map);
        var popupHTML = `
            <div style="width: 200px; text-align: center;">
                <img src="${pet.photo_url}" style="width: 100%; border-radius: 8px; margin-bottom: 8px;">
                <b style="font-size: 16px;">${pet.name}</b><br>
                <p style="font-size: 13px; color: #666;">${pet.desc}</p>
                <small>由 ${pet.user} 發布</small><hr>
                <form action="/comment/${pet.id}" method="POST">
                    <input type="text" name="msg" placeholder="回報近況..." style="width: 120px; font-size: 12px;">
                    <button type="submit">送出</button>
                </form>
                ${pet.comments.map(c => '<div style="font-size:11px; color:blue;">- '+c+'</div>').join('')}
                ${ ("{{ session.get('user') }}" === pet.user) ? '<br><a href="/delete/'+pet.id+'"><button class="btn btn-del">刪除資訊</button></a>' : '' }
            </div>
        `;
        marker.bindPopup(popupHTML);
    });

    var paths = {{ paths | tojson }};
    if (paths.length > 0) L.polyline(paths, {color: '#4CAF50', weight: 4, opacity: 0.6}).addTo(map);
</script>
</body>
</html>
"""

# --- 4. 路由設定 ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, pets=pets_data, paths=searched_paths)

@app.route('/add_pet', methods=['POST'])
def add_pet():
    if 'user' not in session: return "請先登入", 403
    
    file_to_upload = request.files['photo']
    if file_to_upload:
        # 上傳到 Cloudinary
        upload_result = cloudinary.uploader.upload(file_to_upload)
        photo_url = upload_result['secure_url'] # 獲取雲端網址
        
        new_pet = {
            "id": len(pets_data) + 1,
            "name": request.form.get('name'),
            "lat": float(request.form.get('lat')),
            "lng": float(request.form.get('lng')),
            "desc": request.form.get('desc'),
            "user": session['user'],
            "comments": [],
            "photo_url": photo_url
        }
        pets_data.append(new_pet)
        searched_paths.append([new_pet['lat'], new_pet['lng']])
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
    if users.get(u) == p: session['user'] = u
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/comment/<int:pet_id>', methods=['POST'])
def add_comment(pet_id):
    msg = request.form.get('msg')
    for pet in pets_data:
        if pet['id'] == pet_id: pet['comments'].append(msg)
    return redirect(url_for('index'))

@app.route('/delete/<int:pet_id>')
def delete_pet(pet_id):
    global pets_data
    pets_data = [p for p in pets_data if not (p['id'] == pet_id and p['user'] == session.get('user'))]
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)