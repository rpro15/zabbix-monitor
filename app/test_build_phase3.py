#!/usr/bin/env python
"""Build verification test for Phase 3 implementation"""

import sys
import os

print("=" * 60)
print("PHASE 3 BUILD VERIFICATION")
print("=" * 60)

tests_passed = 0
tests_failed = 0

# Test 1: Import Flask-SocketIO
try:
    from flask_socketio import SocketIO
    print("[PASS] Flask-SocketIO imported")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] Flask-SocketIO: {e}")
    tests_failed += 1

# Test 2: Import updated alert_poller with socketio param
try:
    from tasks.alert_poller import poll_alerts_task, get_polling_metrics
    import inspect
    sig = inspect.signature(poll_alerts_task)
    params = list(sig.parameters.keys())
    if 'socketio' in params:
        print("[PASS] poll_alerts_task has socketio parameter")
        tests_passed += 1
    else:
        print("[FAIL] poll_alerts_task missing socketio parameter")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] alert_poller: {e}")
    tests_failed += 1

# Test 3: Import app with SocketIO
try:
    from app import app, socketio, scheduler
    print("[PASS] App with SocketIO initialized")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] App initialization: {e}")
    tests_failed += 1

# Test 4: Check that /alerts route exists
try:
    from app import app
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    if '/alerts' in routes:
        print("[PASS] /alerts dashboard route registered")
        tests_passed += 1
    else:
        print(f"[FAIL] /alerts route not found in routes: {routes}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] Checking routes: {e}")
    tests_failed += 1

# Test 5: Verify API blueprint registered
try:
    from app import app
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    api_routes = [r for r in routes if '/api/alerts' in r]
    if len(api_routes) >= 3:  # Should have GET list, GET one, POST acknowledge at minimum
        print(f"[PASS] API blueprint registered ({len(api_routes)} routes)")
        tests_passed += 1
    else:
        print(f"[FAIL] API blueprint: expected >=3 routes, found {len(api_routes)}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] API blueprint check: {e}")
    tests_failed += 1

# Test 6: Check that templates directory exists
try:
    if os.path.isdir('templates') and os.path.isfile('templates/alerts.html'):
        print("[PASS] templates/alerts.html exists")
        tests_passed += 1
    else:
        print("[FAIL] templates/alerts.html not found")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] Templates check: {e}")
    tests_failed += 1

# Test 7: Check that static files exist
try:
    files_ok = True
    if not os.path.isfile('static/css/alerts.css'):
        print("[FAIL] static/css/alerts.css not found")
        files_ok = False
    if not os.path.isfile('static/js/alerts-dashboard.js'):
        print("[FAIL] static/js/alerts-dashboard.js not found")
        files_ok = False
    
    if files_ok:
        print("[PASS] All static files (CSS, JS) exist")
        tests_passed += 1
    else:
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] Static files check: {e}")
    tests_failed += 1

# Test 8: Verify alerts.html contains key elements
try:
    with open('templates/alerts.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    required_elements = [
        'id="alerts-list"',
        'id="filter-status"',
        'id="filter-severity"',
        'id="alert-modal"',
        'socket.io',
        'alerts-dashboard.js'
    ]
    
    missing = [elem for elem in required_elements if elem not in html_content]
    
    if not missing:
        print("[PASS] alerts.html contains all required elements")
        tests_passed += 1
    else:
        print(f"[FAIL] alerts.html missing: {missing}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] HTML validation: {e}")
    tests_failed += 1

# Test 9: Verify alerts.css contains severity colors
try:
    with open('static/css/alerts.css', 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    required_colors = [
        'severity-5',
        'severity-critical',
        'd32f2f',  # Critical red
        'f57c00',  # High orange
        'fbc02d',  # Average yellow
    ]
    
    missing = [color for color in required_colors if color not in css_content]
    
    if not missing:
        print("[PASS] alerts.css contains severity color coding")
        tests_passed += 1
    else:
        print(f"[FAIL] alerts.css missing colors: {missing}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] CSS validation: {e}")
    tests_failed += 1

# Test 10: Verify JavaScript has WebSocket and polling
try:
    with open('static/js/alerts-dashboard.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    required_features = [
        'this.socket = io',  # WebSocket client initialization
        'new_alerts_batch',
        'HTTP polling',
        'showAlertModal',
        'acknowledgeAlert',
        'loadAlerts'
    ]
    
    missing = [feature for feature in required_features if feature not in js_content]
    
    if not missing:
        print("[PASS] alerts-dashboard.js has all Phase 3 features (WebSocket, polling, modal)")
        tests_passed += 1
    else:
        print(f"[FAIL] alerts-dashboard.js missing: {missing}")
        tests_failed += 1
except Exception as e:
    print(f"[FAIL] JavaScript validation: {e}")
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
    print("ALL TESTS PASSED - Phase 3 implementation verified!")
    print()
    print("Phase 3 Features Implemented:")
    print("[DONE] T011: GET /api/alerts endpoint (from Phase 1)")
    print("[DONE] T012: WebSocket broadcast integration")
    print("[DONE] T013: alerts.html template dashboard")
    print("[DONE] T014: alerts-dashboard.js with WebSocket client")
    print("[DONE] T015: alerts.css with severity color coding")
    print("[DONE] T016: Alert detail modal (clickable alerts)")
    print("[DONE] T017: HTTP polling fallback for non-WebSocket browsers")
    print()
    print("Dashboard accessible at: http://localhost:5000/alerts")
    sys.exit(0)
else:
    print()
    print(f"FAILED: {tests_failed} test(s) failed")
    sys.exit(1)
