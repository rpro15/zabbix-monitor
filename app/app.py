import os
import logging
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit, disconnect
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from models import db, Project
from zabbix_client import ZabbixClient
from services.alert_service import AlertService, ConnectionStateManager, set_zabbix_service
from services.zabbix_service import ZabbixService
from tasks.alert_poller import poll_alerts_task, cleanup_old_alerts_task
from api.alerts import alerts_bp, set_socketio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Flask-SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Set global SocketIO reference for alert API (T022)
set_socketio(socketio)

# Initialize background scheduler
scheduler = BackgroundScheduler()

# Initialize connection state manager
connection_state = ConnectionStateManager()

# Initialize Zabbix services
try:
    zabbix_client = ZabbixClient(
        url=os.getenv('ZABBIX_URL', 'http://zabbix-web:8080/api_jsonrpc.php'),
        username=os.getenv('ZABBIX_USER', 'Admin'),
        password=os.getenv('ZABBIX_PASSWORD', 'zabbix')
    )
    logger.info("✓ Old ZabbixClient initialized")
except Exception as e:
    logger.warning(f"Warning: Could not initialize old ZabbixClient: {e}")
    zabbix_client = None

try:
    zabbix_service = ZabbixService(
        url=os.getenv('ZABBIX_URL', 'http://zabbix-web:8080/api_jsonrpc.php'),
        username=os.getenv('ZABBIX_USER', 'Admin'),
        password=os.getenv('ZABBIX_PASSWORD', 'zabbix')
    )
    logger.info("✓ New ZabbixService initialized")
    # Set global reference for AlertService to use for Zabbix sync (T020)
    set_zabbix_service(zabbix_service)
except Exception as e:
    logger.warning(f"Warning: Could not initialize ZabbixService: {e}")
    zabbix_service = None
    set_zabbix_service(None)

# Initialize database tables
with app.app_context():
    db.create_all()

# Register blueprints
app.register_blueprint(alerts_bp)

# Configure and start scheduler
def start_scheduler():
    """Start background scheduler for alert polling"""
    if not scheduler.running:
        # Alert polling task - runs every 2 seconds (configurable via env)
        polling_interval = int(os.getenv('POLLING_INTERVAL_SECONDS', 2))

        def poll_with_context():
            """Run polling inside Flask application context."""
            with app.app_context():
                return poll_alerts_task(zabbix_service, AlertService, connection_state, socketio)

        def cleanup_with_context():
            """Run cleanup inside Flask application context."""
            with app.app_context():
                return cleanup_old_alerts_task(AlertService, 30)
        
        # Only add polling job if Zabbix service is available
        if zabbix_service:
            scheduler.add_job(
                func=poll_with_context,
                trigger='interval',
                seconds=polling_interval,
                id='alert_polling',
                name='Alert Polling Task',
                replace_existing=True,
                max_instances=1
            )
            logger.info("✓ Alert polling task scheduled")
        else:
            logger.warning("⚠ Zabbix service unavailable, alert polling task disabled")
        
        # Cleanup task - runs daily at 2 AM
        scheduler.add_job(
            func=cleanup_with_context,
            trigger='cron',
            hour=2,
            minute=0,
            id='alert_cleanup',
            name='Alert Cleanup Task',
            replace_existing=True,
            max_instances=1
        )
        
        scheduler.start()
        logger.info("✓ Background scheduler started")


# Initialize scheduler on module load (replaces deprecated before_first_request)
try:
    start_scheduler()
    logger.info("✓ Scheduler initialized on app startup")
except Exception as e:
    logger.error(f"Error starting scheduler on startup: {str(e)}")


# ============ Routes ============

@app.route('/')
def index():
    return "<h1>Zabbix Monitor - Real-time Alerts</h1><p>Service running</p>"


@app.route('/alerts')
def alerts_dashboard():
    """Serve real-time alert dashboard (T013)"""
    return render_template('alerts.html')


@app.route('/alerts/history')
def alerts_history():
    """Serve alert history page (T032, T033: Browse historical alerts by date range)"""
    return render_template('alerts-history.html')


@app.route('/api/health')
def health():
    """System health check endpoint"""
    try:
        db.session.execute('SELECT 1')
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    if zabbix_service:
        zabbix_status = zabbix_service.get_status()
    else:
        zabbix_status = {'connected': False, 'error': 'Service not initialized'}
    
    scheduler_status = 'running' if scheduler.running else 'stopped'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'zabbix-monitor',
        'database': db_status,
        'scheduler': scheduler_status,
        'zabbix': zabbix_status,
        'connection_state': connection_state.get_status()
    }), 200


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

    # Create host in Zabbix if client available
    if zabbix_client:
        try:
            host_data = {
                'host': data['name'].lower().replace(' ', '_'),
                'name': data['name'],
                'interfaces': [{
                    'type': 1,  # Zabbix agent
                    'main': 1,
                    'useip': 1,
                    'ip': '127.0.0.1',  # In practice, IP should be obtained
                    'dns': '',
                    'port': '10050'
                }],
                'groups': [{'groupid': '2'}],  # Linux servers (usually groupid=2)
                'templates': [{'templateid': '10001'}]  # Template OS Linux by Zabbix agent
            }
            host_id = zabbix_client.create_host(host_data)
            if host_id:
                project.zabbix_host_id = host_id
                db.session.commit()
                return jsonify({'id': project.id, 'zabbix_host_id': host_id, 'message': 'Project created with Zabbix host'}), 201
        except Exception as e:
            logger.warning(f"Failed to create Zabbix host: {e}")
    
    return jsonify({'id': project.id, 'message': 'Project created (Zabbix host creation skipped)'}), 201


# ============ WebSocket Handlers ============

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    
    # Send current connection status
    emit('connection_status', connection_state.get_status())


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


def broadcast_new_alert(alert_data):
    """
    Broadcast new alert to all connected clients via WebSocket.
    
    Called when a new alert is fetched from Zabbix.
    
    Args:
        alert_data: Dictionary with alert information
    """
    try:
        socketio.emit(
            'new_alert',
            {'data': alert_data, 'timestamp': datetime.utcnow().isoformat()},
            namespace='/'
        )
        logger.debug(f"Broadcasted alert: {alert_data.get('id')}")
    except Exception as e:
        logger.error(f"Error broadcasting alert: {str(e)}")


def broadcast_connection_status(status: dict):
    """
    Broadcast connection status to all clients.
    
    Args:
        status: Dictionary with connection status
    """
    try:
        socketio.emit(
            'connection_status',
            status,
            namespace='/'
        )
    except Exception as e:
        logger.error(f"Error broadcasting status: {str(e)}")


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
