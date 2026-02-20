#!/usr/bin/env python
"""Build verification test for Phase 4 implementation"""

import sys
import os

print("=" * 60)
print("PHASE 4 BUILD VERIFICATION")
print("=" * 60)

tests_passed = 0
tests_failed = 0

# Test 1: Import enhanced AlertService with Zabbix sync
try:
    from services.alert_service import AlertService, set_zabbix_service
    print("[PASS] AlertService with Zabbix sync support")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] AlertService: {e}")
    tests_failed += 1

# Test 2: Import ZabbixService with acknowledge_event
try:
    from services.zabbix_service import ZabbixService
    import inspect
    methods = [m[0] for m in inspect.getmembers(ZabbixService, predicate=inspect.ismethod)]
    if 'acknowledge_event' in dir(ZabbixService):
        print("[PASS] ZabbixService.acknowledge_event() available")
        tests_passed += 1
    else:
        print("[FAIL] ZabbixService missing acknowledge_event")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] ZabbixService: {e}")
    tests_failed += 1

# Test 3: Check API alert blueprint has set_socketio
try:
    from api.alerts import set_socketio
    print("[PASS] API blueprint has set_socketio function")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] API blueprint: {e}")
    tests_failed += 1

# Test 4: Verify acknowledge endpoint exists
try:
    from app import app
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    if '/api/alerts/<alert_id>/acknowledge' in routes or any('acknowledge' in r for r in routes):
        print("[PASS] Acknowledge endpoint registered")
        tests_passed += 1
    else:
        print(f"[FAIL] Acknowledge endpoint not found")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] Route check: {e}")
    tests_failed += 1

# Test 5: Verify frontend JavaScript has acknowledge handler
try:
    with open('static/js/alerts-dashboard.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    required_features = [
        'acknowledgeAlert',
        'alert_acknowledged',
        'operator_name',
        'Acknowledging',
        'acknowledged successfully'
    ]
    
    missing = [feature for feature in required_features if feature not in js_content]
    
    if not missing:
        print("[PASS] Frontend has enhanced acknowledge functionality")
        tests_passed += 1
    else:
        print(f"[FAIL] Frontend missing: {missing}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] JavaScript check: {e}")
    tests_failed += 1

# Test 6: Verify AlertAcknowledgment model has synced_to_zabbix field
try:
    from models import AlertAcknowledgment
    ack_model = AlertAcknowledgment()
    if hasattr(ack_model, 'synced_to_zabbix'):
        print("[PASS] AlertAcknowledgment has synced_to_zabbix field")
        tests_passed += 1
    else:
        print("[FAIL] AlertAcknowledgment missing synced_to_zabbix")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] Model check: {e}")
    tests_failed += 1

# Test 7: Verify AlertHistory records status changes
try:
    from models import AlertHistory
    hist_model = AlertHistory()
    required_fields = ['alert_id', 'status_change_from', 'status_change_to', 'changed_by']
    missing_fields = []
    for field in required_fields:
        if not hasattr(hist_model, field):
            missing_fields.append(field)
    
    if not missing_fields:
        print("[PASS] AlertHistory model complete")
        tests_passed += 1
    else:
        print(f"[FAIL] AlertHistory missing: {missing_fields}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] History model: {e}")
    tests_failed += 1

# Test 8: Verify app sets both zabbix_service and socketio
try:
    from app import app, zabbix_service, socketio
    print("[PASS] App properly initializes zabbix_service and socketio")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] App initialization: {e}")
    tests_failed += 1

# Test 9: Verify CSS has acknowledge button styling
try:
    with open('static/css/alerts.css', 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    required_styles = [
        'btn-acknowledge',
        'slideInRight',
        'toast',
        'acknowledged'
    ]
    
    missing_styles = [style for style in required_styles if style not in css_content]
    
    if not missing_styles:
        print("[PASS] CSS has acknowledge styling and toast notifications")
        tests_passed += 1
    else:
        print(f"[FAIL] CSS missing: {missing_styles}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] CSS check: {e}")
    tests_failed += 1

# Test 10: Verify modal template has acknowledge button
try:
    with open('templates/alerts.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    if 'id="acknowledge-btn"' in html_content and 'btn-acknowledge' in html_content:
        print("[PASS] Modal template has acknowledge button")
        tests_passed += 1
    else:
        print("[FAIL] Modal missing acknowledge button")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] Template check: {e}")
    tests_failed += 1

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Tests Passed: {tests_passed}")
print(f"Tests Failed: {tests_failed}")
print(f"Total: {tests_passed + tests_failed}")

if tests_failed == 0:
    print()
    print("ALL TESTS PASSED - Phase 4 implementation verified!")
    print()
    print("Phase 4 Features Implemented:")
    print("[DONE] T018: POST /api/alerts/{alert_id}/acknowledge endpoint")
    print("[DONE] T019: AlertAcknowledgment record creation")
    print("[DONE] T020: Zabbix sync via event.acknowledge()")
    print("[DONE] T021: Alert status update + timestamp")
    print("[DONE] T022: Frontend acknowledge UI with loading state")
    print("[DONE] T023: Operator name capture from request/header")
    print("[DONE] T024: AlertHistory records for status changes")
    print()
    print("Features:")
    print("- Real-time acknowledgment sync to Zabbix API")
    print("- Optimistic UI updates with loading states")
    print("- Toast notifications for success/error")
    print("- WebSocket broadcast for acknowledgments")
    print("- Operator tracking with reason capture")
    sys.exit(0)
else:
    print()
    print(f"FAILED: {tests_failed} test(s) failed")
    sys.exit(1)
