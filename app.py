from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# 加载数据
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nodes_path = os.path.join(base_dir, 'nodes.json')
    links_path = os.path.join(base_dir, 'links.json')
    
    with open(nodes_path, 'r', encoding='utf-8') as f:
        nodes = json.load(f)
    with open(links_path, 'r', encoding='utf-8') as f:
        links = json.load(f)
    
    return nodes, links, {n['id']: n for n in nodes}

try:
    nodes, links, node_map = load_data()
    print(f"✅ 数据加载完成：{len(nodes)} 个节点，{len(links)} 条关系")
except FileNotFoundError as e:
    print(f"❌ 文件未找到: {e}")
    nodes, links, node_map = [], [], {}

def find_node(name):
    for n in nodes:
        if n['name'] == name:
            return n
    for n in nodes:
        if name in n['name'] or n['name'] in name:
            return n
    return None

@app.route('/')
def index():
    return jsonify({
        "status": "OK", 
        "nodes": len(nodes), 
        "links": len(links),
        "diseases": ["开裂", "空鼓", "剥落"]
    })

@app.route('/api/query-disease', methods=['POST'])
def query_disease():
    """查询病害完整信息（保留原功能）"""
    data = request.json or {}
    name = data.get('diseaseName', '').strip()
    if not name:
        return jsonify({"error": "请提供病害名称"}), 400
    disease = find_node(name)
    if not disease:
        return jsonify({"error": f"未找到 '{name}'", "available": ["开裂", "空鼓", "剥落"]}), 404
    
    result = {
        "disease": {"id": disease['id'], "name": disease['name'], "desc": disease.get('desc', '')},
        "risk_levels": []
    }
    for link in links:
        if link['from'] == disease['id'] and '包含' in link.get('relation', ''):
            risk = node_map.get(link['to'])
            if risk and '风险' in risk['name']:
                risk_info = {"level": risk['name'], "desc": risk.get('desc', ''), "criteria": []}
                for cl in links:
                    if cl['from'] == risk['id'] and '判定标准' in cl.get('relation', ''):
                        criterion = node_map.get(cl['to'])
                        if criterion:
                            risk_info['criteria'].append({"name": criterion['name'], "desc": criterion.get('desc', '')})
                result['risk_levels'].append(risk_info)
    return jsonify(result)

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """
    根据测量数据直接计算风险等级
    请求体示例:
    {
        "diseaseType": "开裂",
        "crackWidth": 2.0,      // 单位 mm
        "hollowArea": 0.02,     // 单位 ㎡
        "spallingArea": 1.5     // 单位 ㎡
    }
    """
    data = request.json or {}
    disease_type = data.get('diseaseType', '').strip()
    if not disease_type:
        return jsonify({"error": "请提供病害类型"}), 400

    # 获取测量值（只有对应病害类型的测量值会被使用）
    crack_width = data.get('crackWidth')
    hollow_area = data.get('hollowArea')
    spalling_area = data.get('spallingArea')

    # 根据病害类型计算风险等级
    risk_level = None
    matched_criterion = None

    if disease_type == "开裂":
        if crack_width is None:
            return jsonify({"error": "开裂病害需要提供 crackWidth (mm)"}), 400
        if crack_width <= 0.2:
            risk_level = "低风险"
            matched_criterion = "裂缝宽度 ≤ 0.2mm"
        elif crack_width <= 1.0:
            risk_level = "中风险"
            matched_criterion = "0.2mm < 裂缝宽度 ≤ 1.0mm"
        else:
            risk_level = "高风险"
            matched_criterion = "裂缝宽度 ≥ 1.0mm"

    elif disease_type == "空鼓":
        if hollow_area is None:
            return jsonify({"error": "空鼓病害需要提供 hollowArea (㎡)"}), 400
        if hollow_area <= 0.01:
            risk_level = "低风险"
            matched_criterion = "单处空鼓面积 ≤ 0.01㎡"
        elif hollow_area < 0.04:
            risk_level = "中风险"
            matched_criterion = "0.01㎡ < 单处空鼓面积 < 0.04㎡"
        else:
            risk_level = "高风险"
            matched_criterion = "单处空鼓面积 ≥ 0.04㎡"

    elif disease_type == "剥落":
        if spalling_area is None:
            return jsonify({"error": "剥落病害需要提供 spallingArea (㎡)"}), 400
        if spalling_area < 1.0:
            risk_level = "低风险"
            matched_criterion = "剥落面积 < 1㎡"
        else:
            risk_level = "高风险"
            matched_criterion = "剥落面积 ≥ 1㎡"

    else:
        return jsonify({"error": f"未知病害类型: {disease_type}", "available": ["开裂", "空鼓", "剥落"]}), 400

    # 返回计算结果
    return jsonify({
        "disease": disease_type,
        "risk_level": risk_level,
        "matched_criterion": matched_criterion,
        "measurements": {
            "crack_width_mm": crack_width,
            "hollow_area_m2": hollow_area,
            "spalling_area_m2": spalling_area
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
