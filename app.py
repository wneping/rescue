import os
from flask import Flask, render_template_string, request, session, redirect, url_for
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
# 建議在 Render 的 Environment Variables 增加一個 FLASK_SECRET_KEY
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'pet_mission_secure_key_2026')

# --- 1. Cloudinary 配置 ---
cloudinary.config( 
  cloud_name = os.environ.get('CLOUDINARY_NAME'), 
  api_key = os.environ.get('CLOUDINARY_API_KEY'), 
  api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
  secure = True
)

# --- 2. 管理員帳密設定 ---
ADMIN_USER = "wxp800218"
ADMIN_PW = "0981161269"

# 暫存資料庫
pets_data = []
searched_paths = []

# --- 3. HTML & JavaScript 模板 ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>🐾 尋獲毛小孩任務 - 即時救援地圖</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: "Microsoft JhengHei", Arial, sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; background: #eceff1; }
        header { background: #2c3e50; color: white; padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; z-index: 1000; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        #map { flex: 1; width: 100%; position: relative; }
        .form-panel { padding: 15px; background: white; border-top: 4px solid #27ae60; z-index: 1001; }
        .btn { padding: 10px 15px; cursor: pointer; border: none; border-radius: 5px; font-weight: bold; }
        .btn-add { background: #27ae60; color: white; width: 100%; margin-top: 10px; font-size: 16px; }
        .btn-locate { position: absolute; top: 80px; left: 10px; z-index: 1000; background: white; border: 2px solid rgba(0,0,0,0.2); padding: 8px; cursor: pointer; border-radius: 4px; font-size: 20px; }
        .btn-del { background: #e74c3c; color: white; width: 100%; margin-top: 8px; font-size: 12px; }
        input, textarea { width: 95%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .popup-card { width: 220px; text-align: center; }
        .comment-box { text-align: left; font-size: 12px; background: #f1f2f6; padding: 8px; max-height: 80px; overflow-y: auto; margin: 10px 0; border-radius: 5px; border-left: 3px solid #2ecc71; }
    </style>
</head>
<body>

<header>
    <div onclick="location.reload()" style="cursor:pointer;">
        <h3 style="margin:0;">🐾 尋獲毛小孩任務</h3>
    </div>
    <div>
        {% if is_admin %}
            <span style="color:#f1c40f; font-size:12px;">👑 管理員</span> | <a href="/logout" style="color:white; font-size:12px;">登出</a>
        {% else %}
            <form action="/login" method="POST" style="display: inline;">
                <input type="text" name="username" placeholder="帳號" style="width:60px; padding:2px; font-size:10px;">
                <input type="password" name="password" placeholder="密碼" style="width:60px; padding:2px; font-size:10px;">
                <button type="submit" style="font-size:10px; padding:2px 5px;">登入</button>
            </form>
        {% endif %}
    </div>
</header>

<div id="map">
    <button class="btn-locate" onclick="locateUser()" title="點擊定位我的位置">📍</button>
</div>

<div class="form-panel">
    <strong>🆕 發布新資訊：地圖已自動定位 (或手動點擊)</strong>
    <form action="/add_pet" method="POST" enctype="multipart/form-data">
        <input type="hidden" id="lat" name="lat" required>
        <input type="hidden" id="lng" name="lng" required>
        <div style="display: flex; gap: 5px;">
            <input type="text" name="name" placeholder="毛小孩稱呼" style="flex: 1;" required>
            <input type="text" name="phone" placeholder="聯絡電話" style="flex: 1;" required>
        </div>
        <input type="text" name="desc" placeholder="特徵描述 (例如：親人、受傷、藍色領巾)" required>
        <div style="margin-top:5px;">
            <label style="font-size:12px; color:#666;">📸 上傳照片：</label>
            <input type="file" name="photo" accept="image/*" required>
        </div>
        <button type="submit" class="btn btn-add">🚀 立即發布救援任務</button>
    </form>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    // 初始化地圖
    var map = L.map('map').setView([23.6, 121.0], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    var tempMarker;
    var isAdmin = {{ 'true' if is_admin else 'false' }};

    // --- GPS 定位邏輯 ---
    function locateUser() {
        map.locate({
            setView: true, 
            maxZoom: 16,
            enableHighAccuracy: true 
        });
    }

    map.on('locationfound', function(e) {
        // 更新隱藏欄位
        document.getElementById('lat').value = e.latlng.lat;
        document.getElementById('lng').value = e.latlng.lng;
        
        // 放置刊登標記
        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(e.latlng).addTo(map).bindTooltip("您目前的精確位置").openTooltip();
        
        // 畫出定位誤差圓圈
        L.circle(e.latlng, e.accuracy / 2, {color: '#3498db', fillOpacity: 0.1}).addTo(map);
    });

    map.on('locationerror', function(e) {
        console.log("定位失敗: " + e.message);
    });

    // 啟動即定位
    locateUser();

    // 手動點擊修正位置
    map.on('click', function(e) {
        document.getElementById('lat').value = e.latlng.lat;
        document.getElementById('lng').value = e.latlng.lng;
        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(e.latlng).addTo(map).bindTooltip("已選取新地點").openTooltip();
    });

    // 載入資料
    var pets = {{ pets | tojson }};
    pets.forEach(function(pet) {
        var marker = L.marker([pet.lat, pet.lng]).addTo(map);
        var popupContent = `
            <div class="popup-card">
                <img src="${pet.photo_url}" style="width:100%; border-radius:8px; margin-bottom:8px;">
                <h3 style="margin:0; color:#2c3e50;">${pet.name}</h3>
                <div style="color:#e67e22; font-weight:bold; margin:5px 0;">📞 ${pet.phone}</div>
                <div style="font-size:13px; color:#555; text-align:left;">${pet.desc}</div>
                <div class="comment-box">
                    ${pet.comments.length > 0 ? pet.comments.map(c => '<div>💬 '+c+'</div>').join('') : '目前尚無回報資訊'}
                </div>
                <form action="/comment/${pet.id}" method="POST" style="display:flex; gap:2px;">
                    <input type="text" name="msg" placeholder="我有看見..." style="font-size:11px; flex:1;">
                    <button type="submit" style="font-size:11px;">回報</button>
                </form>
        `;
        if (isAdmin) {
            popupContent += `<a href="/delete/${pet.id}"><button class="btn btn-del">🗑️ 刪除案件 (管理員專用)</button></a>`;
        }
        popupContent += `</div>`;
        marker.bindPopup(popupContent);
    });

    // 繪製搜尋路線
    var paths = {{ paths | tojson }};
    if (paths.length > 1) {
        L.polyline(paths, {color: '#2ecc71', weight: 4, opacity: 0.6, dashArray: '5, 10'}).addTo(map);
    }
</script>
</body>
</html>
"""

# --- 4. 後端路由邏輯 ---

@app.route('/')
def index():
    is_admin = session.get('is_admin', False)
    return render_template_string(HTML_TEMPLATE, pets=pets_data, paths=searched_paths, is_admin=is_admin)

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
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
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        
        if not file or not lat or not lng:
            return "資料不完整 (請確保已點擊地圖定位並選取照片)", 400
        
        upload_result = cloudinary.uploader.upload(file)
        photo_url = upload_result.get('secure_url')

        new_pet = {
            "id": len(pets_data) + 1,
            "name": request.form.get('name'),
            "phone": request.form.get('phone'),
            "lat": float(lat),
            "lng": float(lng),
            "desc": request.form.get('desc'),
            "comments": [],
            "photo_url": photo_url
        }
        pets_data.append(new_pet)
        searched_paths.append([new_pet['lat'], new_pet['lng']])
        return redirect(url_for('index'))
    except Exception as e:
        return f"上傳失敗，請檢查 Cloudinary 設定: {e}", 500

@app.route('/comment/<int:pet_id>', methods=['POST'])
def add_comment(pet_id):
    msg = request.form.get('msg')
    if msg:
        for pet in pets_data:
            if pet['id'] == pet_id:
                pet['comments'].append(msg)
    return redirect(url_for('index'))

@app.route('/delete/<int:pet_id>')
def delete_pet(pet_id):
    global pets_data
    if session.get('is_admin'):
        pets_data = [p for p in pets_data if p['id'] != pet_id]
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
