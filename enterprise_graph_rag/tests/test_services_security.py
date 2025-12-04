import requests
import time

API_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": "enterprise-secret-key"}

def test_rate_limiting():
    print("\n--- Testing Rate Limiter (DoS Protection) ---")
    payload = {"message": "Spam", "thread_id": "spam-bot"}
    
    # Send 12 requests (Limit is 10)
    for i in range(12):
        r = requests.post(f"{API_URL}/chat/stream", json=payload, headers=HEADERS)
        print(f"Req {i+1}: {r.status_code}")
        if r.status_code == 429:
            print("✅ Rate Limit Triggered (429 Too Many Requests)")
            return
            
    print("❌ Rate Limit Failed (Should have blocked requests)")

def test_malicious_upload():
    print("\n--- Testing Malicious File Upload ---")
    
    # Create a fake PDF (actually a text file/script)
    with open("malware.pdf", "wb") as f:
        f.write(b"#!/bin/bash\nrm -rf /") # Malicious shell script header
        
    files = {'file': open('malware.pdf', 'rb')}
    
    r = requests.post(f"{API_URL}/ingest/upload", files=files, headers=HEADERS)
    
    if r.status_code == 400:
        print(f"✅ Security Blocked File: {r.json()['detail']}")
    else:
        print(f"❌ Security Check Failed! Status: {r.status_code}")

if __name__ == "__main__":
    test_rate_limiting()
    test_malicious_upload()