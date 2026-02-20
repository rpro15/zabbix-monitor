"""Alert API endpoints - Flask blueprint"""

from flask import Blueprint, jsonify, request
from flask_socketio import emit
from datetime import datetime
from services.alert_service import AlertService
from models import Alert, AlertAcknowledgment, AlertHistory
import logging

logger = logging.getLogger(__name__)

# Create blueprint
alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')

# Global SocketIO reference (will be set by app.py)
_socketio = None

def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO datetime, accepting trailing 'Z' for UTC."""
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.fromisoformat(value)

def set_socketio(socketio):
    """Set global SocketIO reference for WebSocket broadcasting"""
    global _socketio
    _socketio = socketio


@alerts_bp.route('', methods=['GET'])
def get_alerts():
    """
    Get all current alerts with optional filtering.
    
    Query Parameters:
        - status: Filter by status (new, acknowledged, resolved)
        - severity: Filter by severity level (0-5)
        - host: Filter by hostname (partial match)
        - search: Search in alert name
        - skip: Number of records to skip (default 0)
        - limit: Maximum records to return (default 100, max 1000)
    """
    try:
        # Parse query parameters
        status = request.args.get('status', None)
        severity = request.args.get('severity', None, type=int)
        host = request.args.get('host', None)
        search = request.args.get('search', None)
        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Validate limit (max 1000)
        limit = min(limit, 1000)
        
        # Get filtered alerts
        alerts, total = AlertService.get_alerts_filtered(
            status=status,
            severity=severity,
            host=host,
            search=search,
            skip=skip,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': [alert.to_dict() for alert in alerts],
            'pagination': {
                'skip': skip,
                'limit': limit,
                'total': total
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@alerts_bp.route('/<alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get single alert by ID"""
    try:
        alert = Alert.query.get(alert_id)
        if not alert:
            return jsonify({'success': False, 'error': 'Alert not found'}), 404
        
        return jsonify({
            'success': True,
            'data': alert.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@alerts_bp.route('/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """
    Acknowledge an alert (T018, T023).
    
    T020: Syncs acknowledgment back to Zabbix API.
    
    Request Body:
        - operator_name: Name of operator acknowledging (optional, can be from session)
        - reason: Acknowledgment reason (optional)
    """
    try:
        data = request.get_json() or {}
        
        # Get operator name from request, session, or auth header (T023)
        operator_name = (
            data.get('operator_name') or
            request.headers.get('X-Operator-Name') or
            'Unknown'
        )
        reason = data.get('reason', None)
        
        # Acknowledge alert (T019: creates AlertAcknowledgment record, T024: creates AlertHistory)
        # T020: Also syncs to Zabbix if service available
        ack = AlertService.acknowledge_alert(alert_id, operator_name, reason)
        if not ack:
            return jsonify({'success': False, 'error': 'Failed to acknowledge alert or already acknowledged'}), 400
        
        alert = Alert.query.get(alert_id)
        
        # Broadcast acknowledgment to all WebSocket clients
        if _socketio and alert:
            try:
                _socketio.emit(
                    'alert_acknowledged',
                    {
                        'alert_id': alert_id,
                        'operator_name': operator_name,
                        'reason': reason,
                        'timestamp': datetime.utcnow().isoformat(),
                        'new_status': alert.status
                    },
                    namespace='/'
                )
                logger.debug(f"Broadcasted acknowledgment for alert {alert_id}")
            except Exception as e:
                logger.error(f"Error broadcasting acknowledgment: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Alert acknowledged successfully',
            'data': {
                'alert': alert.to_dict() if alert else None,
                'acknowledgment': ack.to_dict()
            }
        }), 200
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@alerts_bp.route('/history', methods=['GET'])
def get_alert_history():
    """
    Get historical alerts within date range.
    
    Query Parameters:
        - date_from: Start date (ISO format, e.g. 2026-02-15T00:00:00)
        - date_to: End date (ISO format, e.g. 2026-02-20T23:59:59)
        - skip: Number of records to skip (default 0)
        - limit: Maximum records to return (default 100)
    """
    try:
        # Parse dates
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        if not date_from_str or not date_to_str:
            return jsonify({
                'success': False,
                'error': 'date_from and date_to parameters required'
            }), 400
        
        # Parse dates
        try:
            date_from = _parse_iso_datetime(date_from_str)
            date_to = _parse_iso_datetime(date_to_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use ISO format: 2026-02-20T12:30:00'
            }), 400
        
        # Get historical alerts
        alerts, total = AlertService.get_alerts_by_date_range(
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': [alert.to_dict() for alert in alerts],
            'pagination': {
                'skip': skip,
                'limit': limit,
                'total': total
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching alert history: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@alerts_bp.route('/<alert_id>/history', methods=['GET'])
def get_single_alert_history(alert_id):
    """
    Get history timeline for a specific alert.
    
    Query Parameters:
        - date_from: Start date (optional)
        - date_to: End date (optional)
    """
    try:
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        # Parse dates if provided
        date_from = None
        date_to = None
        if date_from_str:
            date_from = _parse_iso_datetime(date_from_str)
        if date_to_str:
            date_to = _parse_iso_datetime(date_to_str)
        
        # Get history
        history = AlertService.get_alert_history(alert_id, date_from, date_to)
        
        return jsonify({
            'success': True,
            'data': [h.to_dict() for h in history]
        }), 200
    except Exception as e:
        logger.error(f"Error fetching history for alert {alert_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
