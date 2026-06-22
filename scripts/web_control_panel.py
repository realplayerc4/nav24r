#!/usr/bin/env python3
"""
Factor Perception Web 控制面板
使用标准库 http.server
支持 ROS2 Jazzy + Factor Perception 建图/导航
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import os
import json
import glob
import urllib.parse
import logging
import yaml
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/tmp/factor_web_control_panel.log'
)
logger = logging.getLogger(__name__)

# ============ 配置加载 ============
CONFIG_YAML_PATH = "/home/yq/nav24r/config/factor_perception_config.yaml"
MAPS_CONFIG_PATH = "/home/yq/nav24r/config/maps_config.json"


def load_app_config():
    """加载 YAML 应用配置"""
    try:
        if os.path.exists(CONFIG_YAML_PATH):
            with open(CONFIG_YAML_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {CONFIG_YAML_PATH}")
            return config
        else:
            logger.warning("配置文件不存在，使用默认配置")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
    # 默认配置
    return {
        'camera': {'key': '12D0C1E7D1AB466C09BD9AE6427D5240'},
        'ros': {'distro': 'jazzy', 'setup_path': '/opt/ros/jazzy/setup.bash'},
        'maps': {'directory': '~/rtabmap_maps', 'default_db': '~/rtabmap.db'},
        'paths': {
            'project_root': '/home/yq/nav24r',
            'config_dir': '/home/yq/nav24r/config',
            'scripts_dir': '/home/yq/nav24r/scripts',
        }
    }


APP_CONFIG = load_app_config()
ROS_SETUP = APP_CONFIG['ros']['setup_path']
CAMERA_KEY = APP_CONFIG['camera']['key']
PROJECT_ROOT = APP_CONFIG['paths']['project_root']
CONFIG_DIR = APP_CONFIG['paths']['config_dir']
SCRIPTS_DIR = APP_CONFIG['paths']['scripts_dir']
MAPS_DIR = os.path.expanduser(APP_CONFIG['maps']['directory'])
DEFAULT_DB = os.path.expanduser(APP_CONFIG['maps']['default_db'])

LAUNCH_FILE = f"{PROJECT_ROOT}/factor_perception_auto.launch.py"
FULL_NAV_LAUNCH = f"{PROJECT_ROOT}/launch/nav24r_full.launch.py"


# ============ 工具函数 ============

def run_ros2_cmd(cmd):
    """运行 ROS2 命令，确保环境变量正确"""
    full_cmd = f"bash -c 'source {ROS_SETUP} && {cmd}'"
    logger.info(f"执行命令: {full_cmd}")
    return subprocess.Popen(full_cmd, shell=True, start_new_session=True)


def run_cmd(cmd):
    """运行普通命令（不需要 ROS 环境）"""
    logger.info(f"执行命令: {cmd}")
    return subprocess.Popen(cmd, shell=True, start_new_session=True)


def stop_all_processes():
    """停止所有 ROS2/RTAB-Map 相关进程"""
    kill_list = [
        'ros2 launch',
        'rviz2',
        'rtabmap',              # RTAB-Map 核心进程
        'rtabmap-databaseViewer',
        'rtabmap_viz',
        'component_container',   # Factor Perception 容器
        'robot_state_publisher',
    ]
    for proc in kill_list:
        subprocess.run(f"pkill -f '{proc}'", shell=True, stderr=subprocess.DEVNULL)
    # 强制清理 factor_perception
    subprocess.run("pkill -9 -f 'factor_perception'", shell=True, stderr=subprocess.DEVNULL)
    logger.info("所有进程已停止")


def get_db_path(map_id):
    """获取地图数据库路径"""
    if map_id == "default":
        return DEFAULT_DB
    return os.path.join(MAPS_DIR, f"{map_id}.db")


def load_maps_config():
    """加载地图元数据配置"""
    if os.path.exists(MAPS_CONFIG_PATH):
        with open(MAPS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"maps_dir": MAPS_DIR, "last_map": None, "maps": {}}


def save_maps_config(config):
    """保存地图元数据配置"""
    with open(MAPS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_map_list():
    """获取地图列表"""
    if not os.path.exists(MAPS_DIR):
        os.makedirs(MAPS_DIR)
    db_files = glob.glob(os.path.join(MAPS_DIR, "*.db"))
    maps = []
    for f in db_files:
        name = os.path.basename(f).replace(".db", "")
        size_mb = os.path.getsize(f) / (1024 * 1024)
        maps.append({"name": name, "size": f"{size_mb:.1f}MB"})
    if os.path.exists(DEFAULT_DB):
        size_mb = os.path.getsize(DEFAULT_DB) / (1024 * 1024)
        maps.append({"name": "default", "size": f"{size_mb:.1f}MB"})
    return sorted(maps, key=lambda x: x["name"], reverse=True)


def analyze_map_quality(db_path):
    """调用地图质量分析脚本"""
    try:
        result = subprocess.run(
            ['python3', f'{SCRIPTS_DIR}/analyze_map_quality.py', db_path],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "分析超时，地图文件可能过大"
    except Exception as e:
        return f"分析失败: {e}"


# ============ HTML 页面 ============

HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factor Perception 控制面板</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #00ff88; text-align: center; margin-bottom: 20px; font-size: 24px; }
        .section { background: #16213e; border-radius: 12px; padding: 20px; margin: 12px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        .section h2 { color: #4ecdc4; margin-bottom: 15px; font-size: 16px; border-bottom: 1px solid #2a3a5e; padding-bottom: 8px; }
        .form-row { display: flex; gap: 8px; margin: 8px 0; align-items: center; flex-wrap: wrap; }
        input, select { padding: 8px 12px; border-radius: 6px; border: 1px solid #2a3a5e; background: #0f3460; color: #fff; font-size: 14px; }
        input[type="text"] { flex: 1; min-width: 120px; }
        button { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
        button:hover { opacity: 0.85; transform: translateY(-1px); }
        button:active { transform: translateY(0); }
        .btn-green { background: #27ae60; color: white; }
        .btn-orange { background: #e07c24; color: white; }
        .btn-blue { background: #2980b9; color: white; }
        .btn-red { background: #c0392b; color: white; }
        .btn-purple { background: #8e44ad; color: white; }
        .btn-teal { background: #16a085; color: white; }
        .btn-gray { background: #7f8c8d; color: white; }
        .btn-large { padding: 12px 24px; font-size: 15px; min-width: 120px; }
        .btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
        .status-bar { background: #0f3460; padding: 12px 20px; border-radius: 8px; margin-top: 12px; display: flex; justify-content: space-between; align-items: center; }
        .status-bar.ok { color: #00ff88; }
        .status-bar.error { color: #ff6b6b; }
        .status-bar.running { color: #f39c12; }
        .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .status-indicator.ready { background: #00ff88; }
        .status-indicator.running { background: #f39c12; animation: pulse 1.5s infinite; }
        .status-indicator.error { background: #ff6b6b; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .info { color: #666; font-size: 12px; margin-top: 15px; line-height: 1.6; }
        .report-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; }
        .report-modal.active { display: flex; align-items: center; justify-content: center; }
        .report-content { background: #1a1a2e; border-radius: 12px; padding: 30px; max-width: 700px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .report-content pre { background: #0f3460; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5; color: #00ff88; white-space: pre-wrap; }
        .report-content h3 { color: #4ecdc4; margin-bottom: 15px; }
        .report-actions { display: flex; gap: 10px; margin-top: 15px; justify-content: flex-end; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        @media (max-width: 600px) { .grid-3, .grid-4 { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Factor Perception 控制面板</h1>

        <!-- 地图管理 -->
        <div class="section">
            <h2>🗺️ 地图管理</h2>
            <div class="form-row">
                <label>地图ID:</label>
                <input type="text" id="map_id" placeholder="输入新地图ID">
                <button class="btn btn-green" onclick="newMap()">🆕 新建</button>
            </div>
            <div class="form-row">
                <label>已有地图:</label>
                <select id="map_select" style="flex:1"></select>
                <button class="btn btn-blue" onclick="refreshMaps()">🔄</button>
                <button class="btn btn-orange" onclick="continueMap()">🔄 续建</button>
                <button class="btn btn-red" onclick="deleteMap()">🗑️ 删除</button>
            </div>
            <div class="form-row">
                <button class="btn btn-purple" onclick="viewMap()">👁️ 查看地图</button>
                <button class="btn btn-orange" onclick="analyzeQuality()">📊 解读质量</button>
                <button class="btn btn-teal" onclick="exportOctomap()">🗺️ 导出Octomap</button>
                <button class="btn btn-gray" onclick="viewDatabase()">📁 数据库查看器</button>
            </div>
        </div>

        <!-- 功能模块 -->
        <div class="section">
            <h2>⚙️ 功能模块</h2>
            <div class="grid-3" style="margin-bottom: 8px;">
                <button class="btn btn-green btn-large" onclick="startMapping()">🗺️ 开始建图</button>
                <button class="btn btn-blue btn-large" onclick="startNavigation()">🧭 开始导航</button>
                <button class="btn btn-blue btn-large" onclick="startFullNav()">🚀 完整导航</button>
            </div>
            <div class="grid-4">
                <button class="btn btn-blue" onclick="launchRviz()">📊 RViz</button>
                <button class="btn btn-blue" onclick="launchRviz3D()">📊 RViz 3D</button>
                <button class="btn btn-purple" onclick="launchMapViewer()">🗺️ 地图观察</button>
                <button class="btn btn-red" onclick="stopAll()">⏹️ 停止所有</button>
            </div>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar ok" id="status">
            <span><span class="status-indicator ready" id="statusDot"></span><span id="statusText">就绪</span></span>
            <span style="font-size:12px;color:#666" id="statusTime"></span>
        </div>

        <div class="info">
            <p>快捷操作: 新建/选择地图 → 建图/导航 | 地图存储: ~/rtabmap_maps/&lt;map_id&gt;.db</p>
            <p>ROS2 Jazzy | Factor Perception + RTAB-Map + Nav2</p>
        </div>
    </div>

    <!-- 地图质量报告弹窗 -->
    <div class="report-modal" id="reportModal">
        <div class="report-content">
            <h3 id="reportTitle">📊 地图质量分析报告</h3>
            <pre id="reportBody">加载中...</pre>
            <div class="report-actions">
                <button class="btn btn-blue" onclick="copyReport()">📋 复制</button>
                <button class="btn btn-gray" onclick="closeReport()">关闭</button>
            </div>
        </div>
    </div>

    <script>
        var lastReport = '';

        function setStatus(msg, type) {
            var el = document.getElementById('status');
            var dot = document.getElementById('statusDot');
            var text = document.getElementById('statusText');
            var time = document.getElementById('statusTime');
            text.textContent = msg;
            el.className = 'status-bar ' + (type || 'ok');
            dot.className = 'status-indicator ' + (type === 'error' ? 'error' : type === 'running' ? 'running' : 'ready');
            time.textContent = new Date().toLocaleTimeString();
        }

        function api(path, data, cb) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', path, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = function() {
                try {
                    var resp = JSON.parse(xhr.responseText);
                    if (cb) cb(resp);
                } catch(e) {
                    setStatus('通信错误', 'error');
                }
            };
            xhr.onerror = function() { setStatus('网络错误', 'error'); };
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
                setStatus('地图列表已刷新 (' + data.maps.length + ' 个)');
            });
        }

        function newMap() {
            var mapId = document.getElementById('map_id').value.trim();
            if (!mapId) { setStatus('请输入地图ID', 'error'); return; }
            api('/api/map/new', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'ok');
                if (!data.error) refreshMaps();
            });
        }

        function continueMap() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            api('/api/map/continue', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'ok');
                document.getElementById('map_id').value = mapId;
            });
        }

        function deleteMap() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            if (!confirm('确定删除地图 ' + mapId + '?')) return;
            api('/api/map/delete', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'ok');
                if (!data.error) refreshMaps();
            });
        }

        function startMapping() {
            var mapId = document.getElementById('map_id').value.trim();
            if (!mapId) { setStatus('请先输入或选择地图ID', 'error'); return; }
            setStatus('正在启动建图模式...', 'running');
            api('/api/start/mapping', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'running');
            });
        }

        function startNavigation() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            setStatus('正在启动导航模式...', 'running');
            api('/api/start/navigation', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'running');
            });
        }

        function startFullNav() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            setStatus('正在启动完整导航...', 'running');
            api('/api/start/full', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'running');
            });
        }

        function viewMap() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            setStatus('正在启动地图查看...', 'running');
            api('/api/map/view', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'running');
            });
        }

        function analyzeQuality() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            document.getElementById('reportTitle').textContent = '📊 地图质量分析 - ' + mapId;
            document.getElementById('reportBody').textContent = '正在分析...';
            document.getElementById('reportModal').classList.add('active');
            api('/api/map/analyze', {map_id: mapId}, function(data) {
                lastReport = data.report || data.message;
                document.getElementById('reportBody').textContent = data.report || data.message;
                setStatus(data.error ? '分析失败' : '分析完成', data.error ? 'error' : 'ok');
            });
        }

        function exportOctomap() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            setStatus('正在启动 Octomap 导出...', 'running');
            api('/api/map/export_octomap', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'ok');
            });
        }

        function viewDatabase() {
            var mapId = document.getElementById('map_select').value;
            if (!mapId) { setStatus('请选择地图', 'error'); return; }
            api('/api/database/view', {map_id: mapId}, function(data) {
                setStatus(data.message, data.error ? 'error' : 'ok');
            });
        }

        function launchRviz() {
            api('/api/rviz', {config: 'mapping'}, function(data) { setStatus(data.message, data.error ? 'error' : 'ok'); });
        }

        function launchRviz3D() {
            api('/api/rviz', {config: 'mapping_3d'}, function(data) { setStatus(data.message, data.error ? 'error' : 'ok'); });
        }

        function launchMapViewer() {
            api('/api/rviz', {config: 'map_viewer_3d'}, function(data) { setStatus(data.message, data.error ? 'error' : 'ok'); });
        }

        function stopAll() {
            setStatus('正在停止所有进程...', 'running');
            api('/api/stop', {}, function(data) {
                setStatus(data.message, 'ok');
            });
        }

        function closeReport() {
            document.getElementById('reportModal').classList.remove('active');
        }

        function copyReport() {
            navigator.clipboard.writeText(lastReport).then(function() {
                setStatus('报告已复制到剪贴板');
            });
        }

        // 初始化
        refreshMaps();
        document.getElementById('map_id').value = 'map_' + new Date().toISOString().slice(0,16).replace(/[-:T]/g, '_');
    </script>
</body>
</html>'''


# ============ HTTP 请求处理 ============

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
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        response = {"error": False, "message": "ok"}

        try:
            response = self._handle_api(data)
        except Exception as e:
            logger.error(f"API 错误: {e}", exc_info=True)
            response = {"error": True, "message": f"操作失败: {str(e)}"}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

    def _handle_api(self, data):
        path = self.path

        # ---- 地图列表 ----
        if path == '/api/maps':
            return {"maps": get_map_list()}

        # ---- 新建地图 ----
        elif path == '/api/map/new':
            map_id = data.get('map_id', '').strip()
            if not map_id:
                return {"error": True, "message": "请输入地图ID"}
            db_path = get_db_path(map_id)
            config = load_maps_config()
            if os.path.exists(db_path):
                return {"error": False, "message": f"地图 '{map_id}' 已存在，可续建"}
            config["last_map"] = map_id
            config["maps"][map_id] = {"created": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "path": db_path}
            save_maps_config(config)
            logger.info(f"新建地图: {map_id}")
            return {"error": False, "message": f"新地图 '{map_id}' 已创建"}

        # ---- 续建地图 ----
        elif path == '/api/map/continue':
            map_id = data.get('map_id', '').strip()
            config = load_maps_config()
            config["last_map"] = map_id
            save_maps_config(config)
            return {"error": False, "message": f"地图 '{map_id}' 已选中"}

        # ---- 删除地图 ----
        elif path == '/api/map/delete':
            map_id = data.get('map_id', '').strip()
            if map_id == "default":
                return {"error": True, "message": "不能删除默认地图"}
            # 检查确认 token（防止 CSRF）
            confirm_token = data.get('confirm_token', '')
            if not confirm_token:
                return {"error": True, "message": "缺少删除确认 token"}
            db_path = get_db_path(map_id)
            if os.path.exists(db_path):
                # 移动到回收站而非直接删除
                trash_dir = os.path.join(MAPS_DIR, ".trash")
                os.makedirs(trash_dir, exist_ok=True)
                trash_path = os.path.join(trash_dir, f"{map_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                os.rename(db_path, trash_path)
                logger.info(f"删除地图: {map_id} -> {trash_path}")
            return {"error": False, "message": f"地图 '{map_id}' 已移到回收站"}

        # ---- 查看地图 ----
        elif path == '/api/map/view':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                return {"error": True, "message": f"地图文件不存在: {db_path}"}
            # 启动 RTAB-Map 定位模式
            cmd = f"ros2 launch {LAUNCH_FILE} localization:=true rtabmap_viz:=true database_path:={db_path} key:={CAMERA_KEY}"
            run_ros2_cmd(cmd)
            logger.info(f"查看地图: {map_id}")
            return {"error": False, "message": f"正在查看地图 '{map_id}'"}

        # ---- 地图质量分析 ----
        elif path == '/api/map/analyze':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                return {"error": True, "message": f"地图文件不存在: {db_path}", "report": ""}
            report = analyze_map_quality(db_path)
            logger.info(f"地图质量分析: {map_id}")
            return {"error": False, "message": "分析完成", "report": report}

        # ---- 导出 Octomap ----
        elif path == '/api/map/export_octomap':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                return {"error": True, "message": f"地图文件不存在: {db_path}"}
            # 启动 Database Viewer（最可靠的导出方式）
            run_cmd(f"bash -c 'source {ROS_SETUP} && rtabmap-databaseViewer {db_path}'")
            logger.info(f"Octomap 导出 - 启动 Database Viewer: {map_id}")
            return {"error": False, "message": f"Database Viewer 已启动，请在 GUI 中: File → Export 3D clouds → Octomap"}

        # ---- 数据库查看器 ----
        elif path == '/api/database/view':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                return {"error": True, "message": f"地图文件不存在: {db_path}"}
            run_cmd(f"bash -c 'source {ROS_SETUP} && rtabmap-databaseViewer {db_path}'")
            logger.info(f"启动 Database Viewer: {map_id}")
            return {"error": False, "message": f"Database Viewer 已启动 | {map_id}"}

        # ---- 开始建图 ----
        elif path == '/api/start/mapping':
            map_id = data.get('map_id', '').strip()
            if not map_id:
                return {"error": True, "message": "请输入地图ID"}
            db_path = get_db_path(map_id)
            cmd = f"ros2 launch {LAUNCH_FILE} localization:=false rtabmap_viz:=true database_path:={db_path} key:={CAMERA_KEY}"
            run_ros2_cmd(cmd)
            logger.info(f"启动建图: {map_id}")
            return {"error": False, "message": f"建图模式已启动 | 地图: {map_id}"}

        # ---- 开始导航 ----
        elif path == '/api/start/navigation':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                return {"error": True, "message": f"地图文件不存在: {db_path}"}
            cmd = f"ros2 launch {LAUNCH_FILE} localization:=true rtabmap_viz:=true database_path:={db_path} key:={CAMERA_KEY}"
            run_ros2_cmd(cmd)
            logger.info(f"启动导航: {map_id}")
            return {"error": False, "message": f"导航模式已启动 | 地图: {map_id}"}

        # ---- 完整导航 ----
        elif path == '/api/start/full':
            map_id = data.get('map_id', '').strip()
            db_path = get_db_path(map_id)
            if not os.path.exists(db_path):
                return {"error": True, "message": f"地图文件不存在: {db_path}"}
            cmd = f"ros2 launch {FULL_NAV_LAUNCH} localization:=true rtabmap_viz:=true database_path:={db_path} key:={CAMERA_KEY}"
            run_ros2_cmd(cmd)
            logger.info(f"启动完整导航: {map_id}")
            return {"error": False, "message": f"完整导航已启动 | 地图: {map_id}"}

        # ---- RViz ----
        elif path == '/api/rviz':
            config_name = data.get('config', 'mapping')
            config_map = {
                'mapping': f'{CONFIG_DIR}/mapping.rviz',
                'mapping_3d': f'{CONFIG_DIR}/mapping_3d.rviz',
                'map_viewer_3d': f'{CONFIG_DIR}/map_viewer_3d.rviz',
                'octomap': f'{CONFIG_DIR}/octomap.rviz',
                'octomap_3d': f'{CONFIG_DIR}/octomap_3d.rviz',
                'navigation': f'{CONFIG_DIR}/navigation.rviz',
            }
            rviz_config = config_map.get(config_name, f'{CONFIG_DIR}/mapping.rviz')
            run_cmd(f"bash -c 'source {ROS_SETUP} && rviz2 -d {rviz_config}'")
            logger.info(f"启动 RViz: {config_name}")
            return {"error": False, "message": f"RViz 已启动 ({config_name})"}

        # ---- 停止所有 ----
        elif path == '/api/stop':
            stop_all_processes()
            return {"error": False, "message": "所有进程已停止"}

        else:
            return {"error": True, "message": "未知接口"}

    def log_message(self, format, *args):
        logger.info(f"HTTP: {format % args}")


# ============ 启动 ============
if __name__ == '__main__':
    print("=" * 50)
    print("Factor Perception Web 控制面板")
    print(f"ROS2: {APP_CONFIG['ros']['distro']} ({ROS_SETUP})")
    print(f"地图目录: {MAPS_DIR}")
    print(f"请在浏览器中打开: http://localhost:5000")
    print("=" * 50)
    server = HTTPServer(('127.0.0.1', 5000), Handler)
    server.serve_forever()
