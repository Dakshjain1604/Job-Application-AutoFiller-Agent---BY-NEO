#!/usr/bin/env python3
"""
Debug script to reproduce and test the 'Analyze Fit' functionality.
Tests the analyze_job endpoint with various scenarios.
"""

import sys
import json
import requests
import time

# Add backend to path
sys.path.insert(0, '/root/jobApplicationAutoFiller/backend')

from database import get_db

def test_direct_engine():
    """Test the IntelligenceEngine directly without API."""
    print("=" * 60)
    print("TEST 1: Direct IntelligenceEngine Testing")
    print("=" * 60)
    
    try:
        from intelligence import IntelligenceEngine
        
        # Test without API key (fallback mode)
        print("\n[1.1] Testing without API key (fallback mode)...")
        engine = IntelligenceEngine(api_key=None)
        
        db = get_db()
        
        # Get a test job
        jobs = db.get_jobs(limit=1)
        if not jobs:
            print("❌ ERROR: No jobs in database to test with")
            return False
        
        job = jobs[0]
        print(f"✓ Found test job: {job['title']} at {job['company']}")
        
        # Get profile
        profile = db.get_profile(1)
        if not profile:
            print("❌ ERROR: No profile found in database")
            return False
        
        print(f"✓ Found profile: {profile.get('name', 'N/A')}")
        
        # Test analysis
        print(f"\n[1.2] Analyzing job {job['id']}...")
        result = engine.analyze_job(job['id'], profile['id'])
        
        print(f"\n✅ Analysis Result:")
        print(f"   Job: {result['title']}")
        print(f"   Company: {result['company']}")
        print(f"   Score: {result['score']}")
        print(f"   Rationale: {result['rationale'][:200]}...")
        
        # Validate result structure
        assert 'score' in result, "Missing 'score' in result"
        assert isinstance(result['score'], (int, float)), "Score is not numeric"
        assert 0 <= result['score'] <= 100, "Score out of range"
        assert 'rationale' in result, "Missing 'rationale' in result"
        
        print("\n✅ TEST 1 PASSED: Direct engine works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """Test the /analyze-job/{job_id} API endpoint."""
    print("\n" + "=" * 60)
    print("TEST 2: API Endpoint Testing")
    print("=" * 60)
    
    try:
        # Start backend server in background if not running
        import subprocess
        import os
        
        # Check if server is running
        try:
            response = requests.get("http://localhost:8000/", timeout=2)
            print("✓ Backend server is already running")
        except:
            print("[2.1] Starting backend server...")
            # Start server in background
            backend_dir = "/root/jobApplicationAutoFiller/backend"
            os.chdir(backend_dir)
            proc = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for startup
            time.sleep(3)
            
            # Verify it started
            try:
                response = requests.get("http://localhost:8000/", timeout=2)
                print("✓ Backend server started successfully")
            except:
                print("❌ ERROR: Could not start backend server")
                return False
        
        # Get a test job
        db = get_db()
        jobs = db.get_jobs(limit=1)
        if not jobs:
            print("❌ ERROR: No jobs in database")
            return False
        
        job_id = jobs[0]['id']
        print(f"\n[2.2] Testing API endpoint with job_id={job_id}...")
        
        # Test API call
        url = f"http://localhost:8000/analyze-job/{job_id}"
        payload = {
            "profile_id": 1,
            "api_key": None  # Test without API key
        }
        
        print(f"   POST {url}")
        print(f"   Payload: {payload}")
        
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"\n[2.3] Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response JSON:")
            print(json.dumps(data, indent=2))
            
            # Validate response structure
            assert 'success' in data, "Missing 'success' field"
            assert data['success'] is True, "Success is not True"
            assert 'analysis' in data, "Missing 'analysis' field"
            
            analysis = data['analysis']
            assert 'score' in analysis, "Missing 'score' in analysis"
            assert isinstance(analysis['score'], (int, float)), "Score is not numeric"
            
            print(f"\n✅ TEST 2 PASSED: API endpoint works correctly")
            return True
        else:
            print(f"❌ ERROR: Got status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_missing_data():
    """Test error handling with missing job/profile."""
    print("\n" + "=" * 60)
    print("TEST 3: Error Handling Testing")
    print("=" * 60)
    
    try:
        from intelligence import IntelligenceEngine
        
        engine = IntelligenceEngine(api_key=None)
        
        print("\n[3.1] Testing with non-existent job_id...")
        try:
            result = engine.analyze_job(99999, 1)
            print("❌ ERROR: Should have raised ValueError for missing job")
            return False
        except ValueError as e:
            print(f"✓ Correctly raised ValueError: {e}")
        
        print("\n[3.2] Testing with non-existent profile_id...")
        db = get_db()
        jobs = db.get_jobs(limit=1)
        if jobs:
            try:
                result = engine.analyze_job(jobs[0]['id'], 99999)
                print("❌ ERROR: Should have raised ValueError for missing profile")
                return False
            except ValueError as e:
                print(f"✓ Correctly raised ValueError: {e}")
        
        print("\n✅ TEST 3 PASSED: Error handling works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("AUTOCAREER FIT ANALYSIS DEBUGGING")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Direct Engine", test_direct_engine()))
    results.append(("API Endpoint", test_api_endpoint()))
    results.append(("Error Handling", test_with_missing_data()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED - Fit Analysis is working!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - See details above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
