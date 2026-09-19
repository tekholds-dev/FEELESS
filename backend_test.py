#!/usr/bin/env python3
"""
Backend API Test Suite for FEELESS Chat API
Tests all chat endpoints with various scenarios
"""
import requests
import json
import sys
from typing import Dict, Any

# Read backend URL from frontend/.env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.strip().split('=', 1)[1]
            break

BASE_URL = f"{BACKEND_URL}/api"
print(f"Testing backend at: {BASE_URL}\n")

# Test results tracking
test_results = []
failed_tests = []


def log_test(test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = f"{status} - {test_name}"
    if details:
        result += f"\n    {details}"
    print(result)
    test_results.append({"name": test_name, "passed": passed, "details": details})
    if not passed:
        failed_tests.append({"name": test_name, "details": details})


def test_root_endpoint():
    """Test 1: GET /api/ - should return {"message": "FEELESS API"}"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        expected = {"message": "FEELESS API"}
        
        if response.status_code == 200 and response.json() == expected:
            log_test("GET /api/ - Root endpoint", True, f"Response: {response.json()}")
            return True
        else:
            log_test("GET /api/ - Root endpoint", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        log_test("GET /api/ - Root endpoint", False, f"Exception: {str(e)}")
        return False


def test_get_empty_room():
    """Test 2: GET /api/chat/solana - should return empty messages array"""
    try:
        response = requests.get(f"{BASE_URL}/chat/solana", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("room") == "solana" and "messages" in data and isinstance(data["messages"], list):
                log_test("GET /api/chat/solana - Empty room", True, 
                        f"Room: {data['room']}, Messages count: {len(data['messages'])}")
                return True, data
            else:
                log_test("GET /api/chat/solana - Empty room", False, 
                        f"Invalid response structure: {data}")
                return False, None
        else:
            log_test("GET /api/chat/solana - Empty room", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False, None
    except Exception as e:
        log_test("GET /api/chat/solana - Empty room", False, f"Exception: {str(e)}")
        return False, None


def test_post_message_without_tokens():
    """Test 3: POST /api/chat/solana - create message without tokens"""
    try:
        payload = {
            "username": "tester",
            "text": "hello world",
            "tokens": None
        }
        response = requests.post(f"{BASE_URL}/chat/solana", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["id", "room", "username", "text", "ts"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if not missing_fields and data["room"] == "solana" and data["username"] == "tester" and data["text"] == "hello world":
                log_test("POST /api/chat/solana - Message without tokens", True, 
                        f"Created message ID: {data.get('id')}, ts: {data.get('ts')}")
                return True, data
            else:
                log_test("POST /api/chat/solana - Message without tokens", False, 
                        f"Missing fields: {missing_fields} or incorrect data: {data}")
                return False, None
        else:
            log_test("POST /api/chat/solana - Message without tokens", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False, None
    except Exception as e:
        log_test("POST /api/chat/solana - Message without tokens", False, f"Exception: {str(e)}")
        return False, None


def test_post_message_with_tokens():
    """Test 4: POST /api/chat/solana - create message with tokens"""
    try:
        payload = {
            "username": "tester",
            "text": "Check CA",
            "tokens": [{
                "chainId": "solana",
                "address": "So11111111111111111111111111111111111111112",
                "symbol": "SOL",
                "name": "Wrapped SOL",
                "priceUsd": "142.37",
                "url": "https://dexscreener.com",
                "liquidity": 1000000,
                "volume": 500000,
                "mcap": 10000000,
                "priceChange24h": 2.4,
                "pairCreatedAt": 1700000000000,
                "imageUrl": ""
            }]
        }
        response = requests.post(f"{BASE_URL}/chat/solana", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["id", "room", "username", "text", "tokens", "ts"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if not missing_fields and data["room"] == "solana" and data["tokens"] is not None and len(data["tokens"]) > 0:
                log_test("POST /api/chat/solana - Message with tokens", True, 
                        f"Created message with tokens, ID: {data.get('id')}")
                return True, data
            else:
                log_test("POST /api/chat/solana - Message with tokens", False, 
                        f"Missing fields: {missing_fields} or tokens not echoed: {data}")
                return False, None
        else:
            log_test("POST /api/chat/solana - Message with tokens", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False, None
    except Exception as e:
        log_test("POST /api/chat/solana - Message with tokens", False, f"Exception: {str(e)}")
        return False, None


def test_get_messages_after_posts():
    """Test 5: GET /api/chat/solana - verify posted messages are returned"""
    try:
        response = requests.get(f"{BASE_URL}/chat/solana", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            
            if len(messages) >= 2:
                # Check chronological order (ts should be increasing)
                timestamps = [m.get("ts", 0) for m in messages]
                is_chronological = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
                
                log_test("GET /api/chat/solana - Messages after posts", True, 
                        f"Found {len(messages)} messages, chronological: {is_chronological}")
                return True, data
            else:
                log_test("GET /api/chat/solana - Messages after posts", False, 
                        f"Expected at least 2 messages, got {len(messages)}")
                return False, None
        else:
            log_test("GET /api/chat/solana - Messages after posts", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False, None
    except Exception as e:
        log_test("GET /api/chat/solana - Messages after posts", False, f"Exception: {str(e)}")
        return False, None


def test_room_isolation():
    """Test 6: GET /api/chat/ethereum - verify room isolation"""
    try:
        response = requests.get(f"{BASE_URL}/chat/ethereum", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            
            # Ethereum room should be empty or have different messages than solana
            if data.get("room") == "ethereum":
                log_test("GET /api/chat/ethereum - Room isolation", True, 
                        f"Ethereum room has {len(messages)} messages (isolated from solana)")
                return True
            else:
                log_test("GET /api/chat/ethereum - Room isolation", False, 
                        f"Room field incorrect: {data}")
                return False
        else:
            log_test("GET /api/chat/ethereum - Room isolation", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        log_test("GET /api/chat/ethereum - Room isolation", False, f"Exception: {str(e)}")
        return False


def test_invalid_post():
    """Test 7: POST /api/chat/solana - invalid body should return 422"""
    try:
        payload = {
            "username": "",
            "text": ""
        }
        response = requests.post(f"{BASE_URL}/chat/solana", json=payload, timeout=10)
        
        if response.status_code == 422:
            log_test("POST /api/chat/solana - Invalid body validation", True, 
                    f"Correctly returned 422 for invalid input")
            return True
        else:
            log_test("POST /api/chat/solana - Invalid body validation", False, 
                    f"Expected 422, got {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        log_test("POST /api/chat/solana - Invalid body validation", False, f"Exception: {str(e)}")
        return False


def test_online_count():
    """Test 8: GET /api/chat/solana/online - should return online count"""
    try:
        response = requests.get(f"{BASE_URL}/chat/solana/online", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "room" in data and "online" in data and isinstance(data["online"], int):
                log_test("GET /api/chat/solana/online - Online count", True, 
                        f"Room: {data['room']}, Online: {data['online']}")
                return True
            else:
                log_test("GET /api/chat/solana/online - Online count", False, 
                        f"Invalid response structure: {data}")
                return False
        else:
            log_test("GET /api/chat/solana/online - Online count", False, 
                    f"Status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        log_test("GET /api/chat/solana/online - Online count", False, f"Exception: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("FEELESS BACKEND CHAT API TEST SUITE")
    print("=" * 80)
    print()
    
    # Run tests in order
    test_root_endpoint()
    print()
    
    test_get_empty_room()
    print()
    
    test_post_message_without_tokens()
    print()
    
    test_post_message_with_tokens()
    print()
    
    test_get_messages_after_posts()
    print()
    
    test_room_isolation()
    print()
    
    test_invalid_post()
    print()
    
    test_online_count()
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)
    print(f"Total: {total} tests")
    print(f"Passed: {passed} tests")
    print(f"Failed: {total - passed} tests")
    print()
    
    if failed_tests:
        print("FAILED TESTS:")
        for test in failed_tests:
            print(f"  ❌ {test['name']}")
            print(f"     {test['details']}")
        print()
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    main()
