#!/usr/bin/env python3
"""
Factor Perception Web 控制面板
使用标准库 http.server
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import json
import glob
import urllib.parse
from datetime import datetime

# ROS2 环境设置
ROS_SETUP_CMD = "source /opt/ros/humble/setup.bash && source /home/yq/nav24r/install/setup.bash 2>/dev/null || true"

CONFIG_FILE = "/home/yq/nav24r/config/maps_config.json"
MAPS_DIR = os.path.expanduser("~/rtabmap_maps")

def run_ros2_cmd(cmd):
    """运行 ROS2 命令，确保环境变量正确"""
    full_cmd = f"bash -c '{ROS_SETUP_CMD} && {cmd}'"
    return subprocess.Popen(full_cmd, shell=True)

def get_db_path(map_id):
    """获取地图数据库路径，处理特殊名称"""
    if map_id == "default (rtabmap.db)":
        return os.path.expanduser("~/rtabmap.db")
    else:
        return os.path.join(MAPS_DIR, f"{map_id}.db")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"maps_dir": "~/rtabmap_maps", "last_map": None, "maps": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_map_list():
    if not os.path.exists(MAPS_DIR):
        os.makedirs(MAPS_DIR)
    db_files = glob.glob(os.path.join(MAPS_DIR, "*.db"))
    maps = []
    for f in db_files:
        name = os.path.basename(f).replace(".db", "")
        size_mb = os.path.getsize(f) / (1024 * 1024)
        maps.append({"name": name, "size": f"{size_mb:.1f}MB"})
    default_db = os.path.expanduser("~/rtabmap.db")
    if os.path.exists(default_db):
        size_mb = os.path.getsize(default_db) / (1024 * 1024)
        maps.append({"name": "default", "size": f"{size_mb:.1f}MB"})
    return sorted(maps, key=lambda x: x["name"], reverse=True)

HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Factor Perception 控制面板</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #00ff88; text-align: center; }
        .section { background: #16213e; border-radius: 10px; padding: 20px; margin: 15px 0; }
        .section h2 { color: #4a7c59; margin-top: 0; }
        .form-row { display: flex; gap: 10px; margin: 10px 0; align-items: center; flex-wrap: wrap; }
        input, select { padding: 10px; border-radius: 5px; border: none; background: #0f3460; color: #fff; }
        input[type="text"] { flex: 1; min-width: 150px; }
        button { padding: 10px 20px; border-radius: 5px; border: none; cursor: pointer; font-size: 14px; }
        .btn-green { background: #4a7c59; color: white; }
        .btn-orange { background: #e07c24; color: white; }
        .btn-blue { background: #3d5a80; color: white; }
        .btn-red { background: #e63946; color: white; }
        .btn:hover { opacity: 0.8; }
        .status { background: #0f3460; padding: 15px; border-radius: 5px; margin-top: 10px; }
        .status.ok { color: #00ff88; }
        .status.error { color: #ff6b6b; }
        .info { color: #888; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Factor Perception 控制面板</h1>
        
        <div class="section">
            <h2>🗺️ 地图管理</h2>
            <div class="form-row">
                <label>地图ID:</label>
                <input type="text" id="map_id" placeholder="输入新地图ID">
                <button class="btn btn-green" onclick="newMap()">🆕 新建地图</button>
            </div>
            <div class="form-row">
                <label>已有地图:</label>
                <select id="map_select"></select>
                <button class="btn btn-orange" onclick="continueMap()">🔄 续建地图</button>
                <button class="btn btn-blue" onclick="refreshMaps()">🔄 刷新</button>
                <button class="btn btn-red" onclick="deleteMap()">🗑️ 删除</button>
            </div>
        </div>
        
        <div class="section">
            <h2>功能模块</h2>
            <div class="form-row">
                <button class="btn btn-green" onclick="startMapping()">🗺️ 开始建图</button>
                <button class="btn btn-blue" onclick="startNavigation()">🧭 开始导航</button>
                <button class="btn btn-blue" onclick="startFullNav()">🚀 完整导航</button>
            </div>
            <div class="form-row">
                <button class="btn btn-blue" onclick="launchRviz()">📊 RViz</button>
                <button class="btn btn-blue" onclick="viewDatabase()">📁 查看数据库</button>
                <button class="btn btn-red" onclick="stopAll()">⏹️ 停止所有</button>
            </div>
        </div>
        
        <div class="status" id="status">状态: 就绪</div>
        
        <div class="info">
            <p>快捷操作:</p>
            <p>• 新建地图: 输入新ID → 点击「新建地图」→ 开始建图</p>
            <p>• 续建地图: 选择已有地图 → 点击「续建地图」→ 开始建图</p>
            <p>• 导航定位: 选择地图 → 点击「开始导航」</p>
            <p>• 地图存储: ~/rtabmap_maps/&lt;map_id&gt;.db</p>
        </div>
    </div>
    
    <script>
        function setStatus(msg, isError) {
            var el = document.getElementById('status');
            el.textContent = '状态: ' + msg;
            el.className = 'status ' + (isError ? 'error' : 'ok');
        }
        
        function api(path, data, cb) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', path, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = function() {
                if (cb) cb(JSON.parse(xhr.responseText));
            };
            xhr.send(JSON.stringify(data || {}));
        }
        
        function refreshMaps() {
            api('/api/maps', {}, function(data) {
                var select = document.getElementById('map_select');
                select.innerHTML = '';
                data.maps.forEach(function(m) {
                    var opt = document.createElement('option');
                    opt.value = m.name;
                    opt.textContent = m.name + ' (' + m.size + ')';
                    select.appendChild(opt);
                });
                setStatus('地图列表已刷新');
            });
        }
        
        function newMap() {
            var mapId = document.getElementById('map_id').value.trim();
            if (!mapId) { setStatus('请输入地图ID', true); return; }
            api('/api/map/new', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error);
                if (!data.error) refreshMaps();
            });
        }
        
        function continueMap() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', true); return; }
            api('/api/map/continue', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error);
                document.getElementById('map_id').value = mapId;
            });
        }
        
        function deleteMap() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', true); return; }
            if (!confirm('确定删除地图 ' + mapId + '?')) return;
            api('/api/map/delete', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error);
                if (!data.error) refreshMaps();
            });
        }
        
        function startMapping() {
            var mapId = document.getElementById('map_id').value.trim();
            if (!mapId) { setStatus('请先输入或选择地图ID', true); return; }
            setStatus('正在启动建图模式...');
            api('/api/start/mapping', {map_id: mapId}, function(data) { setStatus(data.message, data.error); });
        }
        
        function startNavigation() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', true); return; }
            setStatus('正在启动导航模式...');
            api('/api/start/navigation', {map_id: mapId}, function(data) { setStatus(data.message, data.error); });
        }
        
        function startFullNav() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', true); return; }
            setStatus('正在启动完整导航...');
            api('/api/start/full', {map_id: mapId}, function(data) { setStatus(data.message, data.error); });
        }
        
        function launchRviz() {
            api('/api/rviz', {}, function(data) { setStatus(data.message, data.error); });
        }
        
        function viewDatabase() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', true); return; }
            api('/api/database/view', {map_id: mapId}, function(data) { setStatus(data.message, data.error); });
        }
        
        function stopAll() {
            api('/api/stop', {}, function(data) { setStatus(data.message, data.error); });
        }
        
        refreshMaps();
        document.getElementById('map_id').value = 'map_' + new Date().toISOString().slice(0,16).replace(/[-:T]/g, '_');
    </script>
</body>
</html>'''

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        else:
            self.send_error(404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body) if body else {}
        
        response = {"error": False, "message": "ok"}
        
        if self.path == '/api/maps':
            response = {"maps": get_map_list()}
        
        elif self.path == '/api/map/new':
            map_id = data.get('map_id', '').strip()
            if not map_id:
                response = {"error": True, "message": "请输入地图ID"}
            else:
                db_path = os.path.join(MAPS_DIR, f"{map_id}.db")
                config = load_config()
                if os.path.exists(db_path):
                    response = {"error": False, "message": f"地图 '{map_id}' 已存在，可续建"}
                else:
                    config["last_map"] = map_id
                    config["maps"][map_id] = {"created": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "path": db_path}
                    save_config(config)
                    response = {"error": False, "message": f"新地图 '{map_id}' 已创建"}
        
        elif self.path == '/api/map/continue':
            map_id = data.get('map_id', '').strip()
            config = load_config()
            config["last_map"] = map_id
            save_config(config)
            response = {"error": False, "message": f"地图 '{map_id}' 已选中"}
        
        elif self.path == '/api/map/delete':
            map_id = data.get('map_id', '').strip()
            if map_id == "default (rtabmap.db)":
                response = {"error": True, "message": "不能删除默认地图"}
            else:
                db_path = os.path.join(MAPS_DIR, f"{map_id}.db")
                if os.path.exists(db_path):
                    os.remove(db_path)
                response = {"error": False, "message": f"地图 '{map_id}' 已删除"}
        
        elif self.path == '/api/start/mapping':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            subprocess.run("pkill -f 'ros2 launch'", shell=True)
            cmd = f"ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=false rtabmap_viz:=true database_path:={db_path}"
            run_ros2_cmd(cmd)
            response = {"error": False, "message": f"建图模式已启动 | 地图: {map_id}"}
        
        elif self.path == '/api/start/navigation':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                response = {"error": True, "message": f"地图文件不存在: {db_path}"}
            else:
                subprocess.run("pkill -f 'ros2 launch'", shell=True)
                cmd = f"ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=true rtabmap_viz:=true database_path:={db_path}"
                run_ros2_cmd(cmd)
                response = {"error": False, "message": f"导航模式已启动 | 地图: {map_id}"}
        
        elif self.path == '/api/start/full':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                response = {"error": True, "message": f"地图文件不存在: {db_path}"}
            else:
                subprocess.run("pkill -f 'ros2 launch'", shell=True)
                cmd = f"ros2 launch /home/yq/nav24r/launch/nav24r_full.launch.py database_path:={db_path}"
                run_ros2_cmd(cmd)
                response = {"error": False, "message": f"完整导航已启动 | 地图: {map_id}"}
        
        elif self.path == '/api/rviz':
            subprocess.Popen("rviz2 -d /home/yq/nav24r/config/mapping.rviz", shell=True)
            response = {"error": False, "message": "RViz 已启动"}
        
        elif self.path == '/api/database/view':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                response = {"error": True, "message": f"地图文件不存在: {db_path}"}
            else:
                subprocess.Popen(f"rtabmap-databaseViewer {db_path}", shell=True)
                response = {"error": False, "message": f"数据库查看器已启动"}
        
        elif self.path == '/api/stop':
            subprocess.run("pkill -f 'ros2 launch'", shell=True)
            subprocess.run("pkill -f rviz2", shell=True)
            response = {"error": False, "message": "所有进程已停止"}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # 静默日志

if __name__ == '__main__':
    print("=" * 50)
    print("Factor Perception Web 控制面板")
    print("请在浏览器中打开: http://localhost:5000")
    print("=" * 50)
    server = HTTPServer(('0.0.0.0', 5000), Handler)
    server.serve_forever()
