#!/usr/bin/env python
"""Build verification test for Phase 1 implementation"""

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("TESTING IMPORTS AND BUILD")
print("=" * 60)

try:
    from models import Alert, AlertAcknowledgment, AlertHistory, AlertStatus, AlertSeverity
    print("✓ Models (Alert, AlertAcknowledgment, AlertHistory)")
except Exception as e:
    print(f"✗ Models import failed: {e}")
    sys.exit(1)

try:
    from services.alert_service import AlertService, ConnectionStateManager
    print("✓ AlertService and ConnectionStateManager")
except Exception as e:
    print(f"✗ AlertService import failed: {e}")
    sys.exit(1)

try:
    from services.zabbix_service import ZabbixService
    print("✓ ZabbixService")
except Exception as e:
    print(f"✗ ZabbixService import failed: {e}")
    sys.exit(1)

try:
    from api.alerts import alerts_bp
    print("✓ Flask Blueprint (alerts API)")
except Exception as e:
    print(f"✗ API Blueprint import failed: {e}")
    sys.exit(1)

try:
    from tasks.alert_poller import poll_alerts_task, cleanup_old_alerts_task
    print("✓ Background Tasks (alert_poller)")
except Exception as e:
    print(f"✗ Background tasks import failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("CHECKING APP INITIALIZATION")
print("=" * 60)

try:
    from app import app, db, socketio, scheduler, alerts_bp
    print("✓ App core components initialized")
    print("  - Flask app")
    print("  - SQLAlchemy db")
    print("  - Flask-SocketIO")
    print("  - APScheduler")
    print("  - Alert blueprint registered")
except Exception as e:
    print(f"✗ App initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("CHECKING DATABASE MODELS")
print("=" * 60)

try:
    with app.app_context():
        # Check model definitions
        print(f"✓ Alert model: {Alert.__tablename__}")
        print(f"  - Columns: {[c.name for c in Alert.__table__.columns]}")
        
        print(f"✓ AlertAcknowledgment model: {AlertAcknowledgment.__tablename__}")
        print(f"  - Columns: {[c.name for c in AlertAcknowledgment.__table__.columns]}")
        
        print(f"✓ AlertHistory model: {AlertHistory.__tablename__}")
        print(f"  - Columns: {[c.name for c in AlertHistory.__table__.columns]}")
except Exception as e:
    print(f"✗ Model verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("BUILD VERIFICATION COMPLETE ✓")
print("=" * 60)
print("\nPhase 1 Status: ALL SYSTEMS GO")
print("Ready to proceed to Phase 2")
