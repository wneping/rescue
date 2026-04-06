# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template_string, request, session, redirect, url_for, make_response
import cloudinary
import cloudinary.uploader
from supabase import create_client, Client

app = Flask(__name__)
# 建議在 Render 的 Environment Variables 增加 FLASK_SECRET_KEY
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'pet_mission_secure_key_2026')

# --- 1. 外部服務配置 ---
# Cloudinary 配置
cloudinary.config( 
  cloud_name = os.environ.get('CLOUDINARY_NAME'), 
  api_key = os.environ.get('CLOUDINARY_API_KEY'), 
  api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
  secure = True
)

# Supabase 連線配置
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # 這裡填入 anon public key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. 管理員帳密設定 ---
ADMIN_USER = "wxp800218"
ADMIN_PW = "0981161269"

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
        .form-panel { padding: 15px; background: white; border-top: 4px solid #27ae60; z-index: 1001; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); }
        .btn { padding: 10px 15px; cursor: pointer; border: none; border-radius: 5px; font-weight: bold; }
        .btn-add { background: #27ae60; color: white; width: 100%; margin-top: 10px; font-size: 16px; }
        .btn-locate { position: absolute; top: 80px; left: 10px; z-index: 1000; background: white; border: 2px solid rgba(0,0,0,0.2); padding: 8px; cursor: pointer; border-radius: 4px; font-size: 20px; }
        .btn-del { background: #e74c3c; color: white; width: 100%; margin-top: 8px; font-size: 12px; }
        input { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
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
            <span style="color:#f1c40f; font-size:12px;">👑 管理員已登入</span> | <a href="/logout" style="color:white; font-size:12px; text-decoration:none;">登出</a>
        {% else %}
            <form action="/login" method="POST" style="display: inline;">
                <input type="text" name="username" placeholder="帳號" style="width:60px; padding:2px; font-size:10px; display:inline-block;">
                <input type="password" name="password" placeholder="密碼" style="width:60px; padding:2px; font-size:10px; display:inline-block;">
                <button type="submit" style="font-size:10px; padding:2px 5px;">登入</button>
            </form>
        {% endif %}
    </div>
</header>

<div id="map">
    <button class="btn-locate" onclick="locateUser()" title="點擊定位我的位置">📍</button>
</div>

<div class="form-panel">
    <strong>🆕 通報地點：地圖已自動定位 (或點擊地圖修正)</strong>
    <form action="/add_pet" method="POST" enctype="multipart/form-data" onsubmit="return checkCoords()">
        <input type="hidden" id="lat" name="lat" required>
        <input type="hidden" id="lng" name="lng" required>
        <div style="display: flex; gap: 5px;">
            <input type="text" name="name" placeholder="毛小孩稱呼" required>
            <input type="text" name="phone" placeholder="您的聯絡電話" required>
        </div>
        <input type="text" name="desc" placeholder="特徵描述 (如：藍色項圈、親人、受傷)" required>
        <div style="margin-top:5px;">
            <label style="font-size:12px; color:#666;">📸 上傳照片：</label>
            <input type="file" name="photo" accept="image/*" required>
        </div>
        <button type="submit" class="btn btn-add">🚀 立即發布救援任務</button>
    </form>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    var map = L.map('map').setView([23.6, 121.0], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    var tempMarker = null;
    var isAdmin = {{ 'true' if is_admin else 'false' }};

    function checkCoords() {
        var lat = document.getElementById('lat').value;
        if (!lat) {
            alert("請先在地圖上點擊位置，或點擊 📍 按鈕獲取 GPS 座標。");
            return false;
        }
        return true;
    }

    function locateUser() {
        map.locate({setView: true, maxZoom: 16, enableHighAccuracy: true, timeout: 15000, maximumAge: 0});
    }

    map.on('locationfound', function(e) {
        document.getElementById('lat').value = e.latlng.lat;
        document.getElementById('lng').value = e.latlng.lng;
        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(e.latlng).addTo(map).bindTooltip("您目前的精確位置").openTooltip();
        L.circle(e.latlng, e.accuracy / 2, {color: '#3498db', fillOpacity: 0.1}).addTo(map);
    });

    map.on('locationerror', function(e) {
        alert("定位失敗：" + e.message + "\\n請確保使用 HTTPS 並開啟權限。");
    });

    setTimeout(locateUser, 1000);

    map.on('click', function(e) {
        document.getElementById('lat').value = e.latlng.lat;
        document.getElementById('lng').value = e.latlng.lng;
        if (tempMarker) map.removeLayer(tempMarker);
        tempMarker = L.marker(e.latlng).addTo(map).bindTooltip("已選取新地點").openTooltip();
    });

    var pets = {{ pets | tojson }};
    pets.forEach(function(pet) {
        var marker = L.marker([pet.lat, pet.lng]).addTo(map);
        var popupContent = `
            <div class="popup-card">
                <img src="${pet.photo_url}" style="width:100%; border-radius:8px; margin-bottom:8px;">
                <h3 style="margin:0; color:#2c3e50;">${pet.name}</h3>
                <div style="color:#e67e22; font-weight:bold; margin:5px 0;">📞 ${pet.phone}</div>
                <div style="font-size:13px; color:#555; text-align:left;">${pet.description}</div>
                <div class="comment-box">
                    ${pet.comments && pet.comments.length > 0 ? pet.comments.map(c => '<div>💬 '+c+'</div>').join('') : '目前尚無回報資訊'}
                </div>
                <form action="/comment/${pet.id}" method="POST" style="display:flex; gap:2px;">
                    <input type="text" name="msg" placeholder="我有看見..." style="font-size:11px; flex:1; border:1px solid #ccc; padding:3px;">
                    <button type="submit" style="font-size:11px;">回報</button>
                </form>
        `;
        if (isAdmin) {
            popupContent += `<a href="/delete/${pet.id}"><button class="btn btn-del">🗑️ 刪除案件</button></a>`;
        }
        popupContent += `</div>`;
        marker.bindPopup(popupContent);
    });

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
    # 從 Supabase 抓取資料
    try:
        response = supabase.table("pets").select("*").order("created_at", desc=True).execute()
        pets_list = response.data
    except Exception:
        pets_list = []
    
    paths = [[p['lat'], p['lng']] for p in pets_list]

    rendered = render_template_string(HTML_TEMPLATE, pets=pets_list, paths=paths, is_admin=is_admin)
    response = make_response(rendered)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/add_pet', methods=['POST'])
def add_pet():
    try:
        file = request.files.get('photo')
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        
        if not file or not lat or not lng:
            return "資料不完整", 400
        
        # 上傳照片
        upload_result = cloudinary.uploader.upload(file)
        photo_url = upload_result.get('secure_url')

        # 寫入 Supabase
        new_pet = {
            "name": request.form.get('name'),
            "phone": request.form.get('phone'),
            "lat": float(lat),
            "lng": float(lng),
            "description": request.form.get('desc'),
            "photo_url": photo_url,
            "comments": []
        }
        supabase.table("pets").insert(new_pet).execute()
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/comment/<int:pet_id>', methods=['POST'])
def add_comment(pet_id):
    msg = request.form.get('msg')
    if msg:
        res = supabase.table("pets").select("comments").eq("id", pet_id).single().execute()
        current_comments = res.data.get('comments', [])
        current_comments.append(msg)
        supabase.table("pets").update({"comments": current_comments}).eq("id", pet_id).execute()
    return redirect(url_for('index'))

@app.route('/delete/<int:pet_id>')
def delete_pet(pet_id):
    if session.get('is_admin'):
        supabase.table("pets").delete().eq("id", pet_id).execute()
    return redirect(url_for('index'))

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

if __name__ == '__main__':
    app.run(debug=True)
