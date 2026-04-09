from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# 加载数据
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(base_dir, 'data', 'nodes.json'), 'r', encoding='utf-8') as f:
        nodes = json.load(f)
    
    with open(os.path.join(base_dir, 'data', 'links.json'), 'r', encoding='utf-8') as f:
        links = json.load(f)
    
    return nodes, links, {n['id']: n for n in nodes}

nodes, links, node_map = load_data()
print(f"数据加载完成：{len(nodes)} 个节点，{len(links)} 条关系")

def find_node(name):
    """查找节点（支持模糊匹配）"""
    # 完全匹配
    for n in nodes:
        if n['name'] == name:
            return n
    # 包含匹配
    for n in nodes:
        if name in n['name'] or n['name'] in name:
            return n
    return None

def get_related_nodes(node_id):
    """获取关联节点"""
    related = []
    for link in links:
        if link['from'] == node_id:
            related.append(node_map.get(link['to']))
        elif link['to'] == node_id:
            related.append(node_map.get(link['from']))
    return [r for r in related if r]

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
    """查询病害完整信息"""
    data = request.json or {}
    name = data.get('diseaseName', '').strip()
    
    if not name:
        return jsonify({"error": "请提供病害名称"}), 400
    
    # 查找病害节点（开裂/空鼓/剥落）
    disease = find_node(name)
    if not disease:
        return jsonify({
            "error": f"未找到 '{name}'",
            "available": ["开裂", "空鼓", "剥落"]
        }), 404
    
    result = {
        "disease": {
            "id": disease['id'],
            "name": disease['name'],
            "desc": disease.get('desc', '')
        },
        "risk_levels": []
    }
    
    # 查找风险等级（低风险/中风险/高风险）
    for link in links:
        if link['from'] == disease['id'] and '包含' in link.get('relation', ''):
            risk = node_map.get(link['to'])
            if risk and '风险' in risk['name']:
                risk_info = {
                    "level": risk['name'],
                    "desc": risk.get('desc', ''),
                    "criteria": []  # 判定标准
                }
                
                # 查找判定标准
                for cl in links:
                    if cl['from'] == risk['id'] and '判定标准' in cl.get('relation', ''):
                        criterion = node_map.get(cl['to'])
                        if criterion:
                            risk_info['criteria'].append({
                                "name": criterion['name'],
                                "desc": criterion.get('desc', '')
                            })
                
                result['risk_levels'].append(risk_info)
    
    return jsonify(result)

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """根据测量数据评估风险等级"""
    data = request.json or {}
    disease_type = data.get('diseaseType', '').strip()
    
    if not disease_type:
        return jsonify({"error": "请提供病害类型"}), 400
    
    # 这里可以根据传入的测量值（裂缝宽度、空鼓面积等）判断风险等级
    # 简化版：返回该病害的所有风险判定标准
    disease = find_node(disease_type)
    if not disease:
        return jsonify({"error": f"未找到 '{disease_type}'"}), 404
    
    criteria = {}
    for link in links:
        if link['from'] == disease['id'] and '包含' in link.get('relation', ''):
            risk = node_map.get(link['to'])
            if risk and '风险' in risk['name']:
                level_name = risk['name'].split('-')[1] if '-' in risk['name'] else risk['name']
                criteria[level_name] = []
                
                for cl in links:
                    if cl['from'] == risk['id'] and '判定标准' in cl.get('relation', ''):
                        criterion = node_map.get(cl['to'])
                        if criterion:
                            criteria[level_name].append(criterion['name'])
    
    return jsonify({
        "disease": disease_type,
        "evaluation_criteria": criteria
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)