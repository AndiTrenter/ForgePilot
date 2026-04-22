#!/usr/bin/env python3
"""
Detailed ForgePilot Delivery Layer Testing
Tests specific JSON responses and detailed functionality as requested in the review.
"""

import requests
import json
import time
import uuid

# Test Configuration
BASE_URL = "https://autonomous-build-8.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def test_policy_engine_detailed():
    """Test Policy Engine with detailed JSON response verification"""
    print("\n=== DETAILED Policy Engine Testing ===")
    
    session = requests.Session()
    
    test_cases = [
        {
            "action": "build_app",
            "expected": {"category": "auto", "allowed": True, "requires_approval": False}
        },
        {
            "action": "deploy_production", 
            "expected": {"category": "approval", "requires_approval": True}
        },
        {
            "action": "wipe_database",
            "expected": {"category": "forbidden", "allowed": False}
        },
        {
            "action": "some_unknown_xyz",
            "expected": {"category": "unknown", "requires_approval": True}
        }
    ]
    
    for test_case in test_cases:
        action = test_case["action"]
        expected = test_case["expected"]
        
        print(f"\n--- Testing action: {action} ---")
        
        try:
            response = session.post(
                f"{API_BASE}/delivery/jobs/test-job-{uuid.uuid4().hex[:8]}/evaluate-action",
                json={"action": action},
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response JSON: {json.dumps(data, indent=2)}")
                
                # Verify expected fields
                all_match = True
                for key, expected_value in expected.items():
                    actual_value = data.get(key)
                    if actual_value != expected_value:
                        print(f"❌ MISMATCH: {key} = {actual_value}, expected {expected_value}")
                        all_match = False
                    else:
                        print(f"✅ MATCH: {key} = {actual_value}")
                
                if all_match:
                    print(f"✅ PASS: {action}")
                else:
                    print(f"❌ FAIL: {action}")
            else:
                print(f"❌ FAIL: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

def test_delivery_job_detailed():
    """Test detailed delivery job lifecycle with JSON responses"""
    print("\n=== DETAILED Delivery Job Lifecycle Testing ===")
    
    session = requests.Session()
    
    # Create project
    project_data = {
        "name": f"Detailed-Test-{uuid.uuid4().hex[:8]}",
        "description": "Detailed E2E Test"
    }
    
    print("\n--- Step a) Creating Project ---")
    response = session.post(f"{API_BASE}/projects", json=project_data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"❌ FAIL: Could not create project")
        return
    
    project = response.json()
    project_id = project.get("id")
    print(f"Project Created: {project_id}")
    print(f"Response JSON: {json.dumps(project, indent=2)}")
    
    # Step b) Check initial state
    print(f"\n--- Step b) GET /api/delivery/jobs/{project_id} (initial) ---")
    response = session.get(f"{API_BASE}/delivery/jobs/{project_id}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response JSON: {json.dumps(data, indent=2)}")
        
        if data.get("active") is None and data.get("history") == []:
            print("✅ PASS: Initial state correct (active=null, history=[])")
        else:
            print("❌ FAIL: Initial state incorrect")
    
    # Step c) Start chat with SSE
    print(f"\n--- Step c) POST /api/projects/{project_id}/chat (SSE) ---")
    chat_message = {
        "content": "Baue eine simple Todo App",
        "role": "user"
    }
    
    response = session.post(
        f"{API_BASE}/projects/{project_id}/chat",
        json=chat_message,
        stream=True,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("SSE Events (first few):")
        event_count = 0
        job_id = None
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    event_count += 1
                    
                    print(f"Event {event_count}: {json.dumps(data, indent=2)}")
                    
                    # Look for delivery_update
                    if data.get("type") == "delivery_update":
                        job_id = data.get("job_id")
                        print(f"Found job_id: {job_id}")
                    
                    # Stop after reasonable number of events
                    if event_count >= 10:
                        print("... (stopping after 10 events)")
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        print(f"Total events processed: {event_count}")
    
    # Wait a bit for job creation
    time.sleep(3)
    
    # Step d) Check active job
    print(f"\n--- Step d) GET /api/delivery/jobs/{project_id} (after chat) ---")
    response = session.get(f"{API_BASE}/delivery/jobs/{project_id}")
    print(f"Status Code: {response.status_code}")
    
    job_id = None
    if response.status_code == 200:
        data = response.json()
        print(f"Response JSON: {json.dumps(data, indent=2)}")
        
        active_job = data.get("active")
        history = data.get("history", [])
        
        if active_job and active_job.get("stage") and active_job.get("job_id"):
            job_id = active_job.get("job_id")
            print(f"✅ PASS: Active job found - stage={active_job.get('stage')}, job_id={job_id}")
            
            if len(history) >= 1:
                print(f"✅ PASS: History has {len(history)} entries")
            else:
                print("❌ FAIL: History is empty")
        else:
            print("❌ FAIL: No active job found")
    
    # Step e) Get full job details
    if job_id:
        print(f"\n--- Step e) GET /api/delivery/job/{job_id} ---")
        response = session.get(f"{API_BASE}/delivery/job/{job_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            job_data = response.json()
            print(f"Response JSON: {json.dumps(job_data, indent=2)}")
            
            required_fields = ["stage_history", "logs", "job_id", "stage", "created_at"]
            missing_fields = [field for field in required_fields if field not in job_data]
            
            if not missing_fields:
                print("✅ PASS: Full job details complete")
            else:
                print(f"❌ FAIL: Missing fields: {missing_fields}")
        else:
            print(f"❌ FAIL: Could not get job details")
    
    # Cleanup
    try:
        session.delete(f"{API_BASE}/projects/{project_id}")
        print(f"\n✅ Cleaned up project: {project_id}")
    except:
        pass

def test_approval_flow_detailed():
    """Test approval flow with detailed error responses"""
    print("\n=== DETAILED Approval Flow Testing ===")
    
    session = requests.Session()
    
    # Create a job first
    project_data = {
        "name": f"Approval-Flow-{uuid.uuid4().hex[:8]}",
        "description": "Approval flow detailed test"
    }
    
    response = session.post(f"{API_BASE}/projects", json=project_data)
    if response.status_code not in [200, 201]:
        print("❌ FAIL: Could not create project for approval test")
        return
    
    project = response.json()
    project_id = project.get("id")
    
    # Start chat to create job
    chat_message = {"content": "Test job for approval", "role": "user"}
    response = session.post(
        f"{API_BASE}/projects/{project_id}/chat",
        json=chat_message,
        stream=True,
        timeout=15
    )
    
    # Wait and get job_id
    time.sleep(2)
    response = session.get(f"{API_BASE}/delivery/jobs/{project_id}")
    if response.status_code != 200:
        print("❌ FAIL: Could not get job for approval test")
        return
    
    data = response.json()
    active_job = data.get("active")
    if not active_job:
        print("❌ FAIL: No active job for approval test")
        return
    
    job_id = active_job.get("job_id")
    current_stage = active_job.get("stage")
    
    print(f"Created job {job_id} in stage: {current_stage}")
    
    # Test approval when NOT in awaiting_approval stage
    print(f"\n--- Testing POST /api/delivery/jobs/{job_id}/approve (wrong stage) ---")
    response = session.post(
        f"{API_BASE}/delivery/jobs/{job_id}/approve",
        json={"approved_by": "tester"},
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 409:
        response_data = response.json()
        detail = response_data.get("detail", "")
        if "awaiting_approval" in detail.lower():
            print("✅ PASS: Correctly returned 409 with awaiting_approval message")
        else:
            print(f"❌ FAIL: 409 but wrong message: {detail}")
    else:
        print(f"❌ FAIL: Expected 409, got {response.status_code}")
    
    # Test with nonexistent job
    print(f"\n--- Testing POST /api/delivery/jobs/nonexistent-job/approve ---")
    response = session.post(
        f"{API_BASE}/delivery/jobs/nonexistent-job/approve",
        json={"approved_by": "tester"},
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code != 404:
        print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 404:
        print("✅ PASS: Correctly returned 404 for nonexistent job")
    else:
        print(f"❌ FAIL: Expected 404, got {response.status_code}")
    
    # Cleanup
    try:
        session.delete(f"{API_BASE}/projects/{project_id}")
    except:
        pass

if __name__ == "__main__":
    print("🔍 Starting Detailed ForgePilot Delivery Layer Tests")
    print("=" * 60)
    
    test_policy_engine_detailed()
    test_delivery_job_detailed()
    test_approval_flow_detailed()
    
    print("\n" + "=" * 60)
    print("🏁 Detailed Testing Complete")