#!/usr/bin/env python
"""Build verification test for Phase 2 implementation"""

import sys
import os

# Set encoding for output
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("=" * 60)
print("PHASE 2 BUILD VERIFICATION")
print("=" * 60)

tests_passed = 0
tests_failed = 0

# Test 1: Import models
try:
    from models import Alert, AlertAcknowledgment, AlertHistory, AlertStatus, AlertSeverity
    print("[PASS] Models import (Alert, AlertAcknowledgment, AlertHistory)")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] Models import: {e}")
    tests_failed += 1

# Test 2: Import AlertService and ConnectionStateManager
try:
    from services.alert_service import AlertService, ConnectionStateManager
    print("[PASS] AlertService and ConnectionStateManager")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] AlertService: {e}")
    tests_failed += 1

# Test 3: Import ZabbixService
try:
    from services.zabbix_service import ZabbixService
    print("[PASS] ZabbixService")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] ZabbixService: {e}")
    tests_failed += 1

# Test 4: Import API blueprint
try:
    from api.alerts import alerts_bp
    print("[PASS] API Blueprint (alerts)")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] API Blueprint: {e}")
    tests_failed += 1

# Test 5: Import polling task functions
try:
    from tasks.alert_poller import poll_alerts_task, cleanup_old_alerts_task, get_polling_metrics
    print("[PASS] Background tasks (poll_alerts_task, cleanup_old_alerts_task, get_polling_metrics)")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] Background tasks: {e}")
    tests_failed += 1

print()
print("=" * 60)
print("TESTING PHASE 2 FEATURES")
print("=" * 60)

# Test 6: ConnectionStateManager initialization and backoff
try:
    conn_state = ConnectionStateManager(initial_backoff_seconds=1, max_backoff_seconds=60)
    assert conn_state.is_connected == False
    assert conn_state.error_count == 0
    assert conn_state.current_backoff == 1
    print("[PASS] ConnectionStateManager initialization with exponential backoff")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] ConnectionStateManager: {e}")
    tests_failed += 1

# Test 7: Test ConnectionStateManager mark_connected
try:
    conn_state.mark_connected()
    assert conn_state.is_connected == True
    assert conn_state.error_count == 0
    assert conn_state.consecutive_failures == 0
    print("[PASS] ConnectionStateManager.mark_connected() resets backoff")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] mark_connected: {e}")
    tests_failed += 1

# Test 8: Test ConnectionStateManager mark_disconnected
try:
    conn_state.mark_disconnected("Test error")
    assert conn_state.is_connected == False
    assert conn_state.error_count == 1
    assert conn_state.consecutive_failures == 1
    assert conn_state.last_error == "Test error"
    print("[PASS] ConnectionStateManager.mark_disconnected() tracks errors")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] mark_disconnected: {e}")
    tests_failed += 1

# Test 9: Test ConnectionStateManager status
try:
    status = conn_state.get_status()
    assert 'is_connected' in status
    assert 'error_count' in status
    assert 'consecutive_failures' in status
    assert 'current_backoff_seconds' in status
    assert 'next_reconnect_attempt' in status
    print("[PASS] ConnectionStateManager.get_status() returns full status")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] get_status: {e}")
    tests_failed += 1

# Test 10: Test polling metrics
try:
    metrics = get_polling_metrics()
    assert 'total_polls' in metrics
    assert 'successful_polls' in metrics
    assert 'failed_polls' in metrics
    assert 'total_alerts_created' in metrics
    assert 'total_alerts_updated' in metrics
    assert 'consecutive_failures' in metrics
    print("[PASS] Polling metrics tracking")
    tests_passed += 1
except Exception as e:
    print(f"[FAIL] Polling metrics: {e}")
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
    print("ALL TESTS PASSED - Phase 2 implementation verified!")
    sys.exit(0)
else:
    print()
    print(f"FAILED: {tests_failed} test(s) failed")
    sys.exit(1)
