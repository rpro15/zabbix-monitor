import os
from flask import Flask, jsonify, request
from models import db, Project
from zabbix_client import ZabbixClient
import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Инициализация Zabbix клиента
zabbix_client = ZabbixClient(
    url=os.getenv('ZABBIX_URL', 'http://zabbix-web:8080/api_jsonrpc.php'),
    username=os.getenv('ZABBIX_USER', 'Admin'),
    password=os.getenv('ZABBIX_PASSWORD', 'zabbix')
)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "<h1>Zabbix Monitor</h1><p>It works with DB and Zabbix!</p>"

@app.route('/api/health')
def health():
    try:
        db.session.execute('SELECT 1')
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'service': 'zabbix-monitor',
        'database': db_status
    })

@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'url': p.url,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'is_active': p.is_active,
        'zabbix_host_id': p.zabbix_host_id
    } for p in projects])

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    project = Project(
        name=data['name'],
        url=data['url']
    )
    db.session.add(project)
    db.session.commit()

    # Создаём хост в Zabbix
    host_data = {
        'host': data['name'].lower().replace(' ', '_'),
        'name': data['name'],
        'interfaces': [{
            'type': 1,  # Zabbix agent
            'main': 1,
            'useip': 1,
            'ip': '127.0.0.1',  # В реальности IP нужно получать
            'dns': '',
            'port': '10050'
        }],
        'groups': [{'groupid': '2'}],  # Linux servers (обычно groupid=2)
        'templates': [{'templateid': '10001'}]  # Template OS Linux by Zabbix agent
    }
    host_id = zabbix_client.create_host(host_data)
    if host_id:
        project.zabbix_host_id = host_id
        db.session.commit()
        return jsonify({'id': project.id, 'zabbix_host_id': host_id, 'message': 'Project created with Zabbix host'}), 201
    else:
        return jsonify({'id': project.id, 'message': 'Project created but failed to create Zabbix host'}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
