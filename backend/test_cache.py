import requests
import json
import time

BASE_URL = "http://localhost:8000"
CLAIM = "The earth is flat"

def test_caching():
    """
    Tests the caching functionality by sending the same claim twice.
    """
    print("--- Testing Caching ---")
    
    # First request - should not be cached
    print("Sending first request...")
    response1 = requests.post(f"{BASE_URL}/api/verify", json={"claim": CLAIM})
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cached"] == False
    print("First request successful, result not cached as expected.")
    
    # Wait a moment to ensure timestamp is different
    time.sleep(1)
    
    # Second request - should be cached
    print("Sending second request...")
    response2 = requests.post(f"{BASE_URL}/api/verify", json={"claim": CLAIM})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cached"] == True
    print("Second request successful, result was cached as expected.")
    
    print("--- Caching test passed! ---")

if __name__ == "__main__":
    test_caching()
