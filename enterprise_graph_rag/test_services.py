import requests
import json
import time
import websockets # pip install websockets
import asyncio

API_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": "enterprise-secret-key"}

def test_health():
    print("Checking API Health...")
    try:
        r = requests.get(f"{API_URL}/health")
        print(f"Status: {r.status_code} | Body: {r.json()}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_upload():
    print("\n--- Testing Secure Upload ---")
    with open("secure_doc.txt", "w") as f:
        f.write("CONFIDENTIAL: Project Manhattan is run by Oppenheimer.")
    
    files = {'file': open('secure_doc.txt', 'rb')}
    
    # 1. Try without Auth (Should Fail)
    r_fail = requests.post(f"{API_URL}/ingest/upload", files=files)
    if r_fail.status_code == 403:
        print("✅ Security Check Passed (403 without key).")
    else:
        print(f"❌ Security Failed! Got {r_fail.status_code} without key.")
        
    # 2. Try with Auth
    files = {'file': open('secure_doc.txt', 'rb')} # Re-open
    r = requests.post(f"{API_URL}/ingest/upload", files=files, headers=HEADERS)
    
    if r.status_code == 202:
        print(f"✅ Authenticated Upload Accepted. Task: {r.json()['task_id']}")
    else:
        print(f"❌ Upload Failed: {r.text}")

def test_chat_stream():
    print("\n--- Testing Secure Chat Stream ---")
    payload = {"message": "Who runs Project Manhattan?", "thread_id": "secure-thread-1"}
    
    with requests.post(f"{API_URL}/chat/stream", json=payload, headers=HEADERS, stream=True) as r:
        if r.status_code == 200:
            print("AI: ", end="")
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if "token" in decoded:
                        data = json.loads(decoded.replace("data: ", ""))
                        print(data['content'], end="", flush=True)
            print("\n✅ Stream Finished")
        else:
            print(f"❌ Chat Failed: {r.status_code}")

async def test_websocket_status(task_id):
    print(f"\n--- Testing Real-Time WebSocket for Task {task_id} ---")
    uri = f"ws://localhost:8000/ws/status/{task_id}"
    
    async with websockets.connect(uri) as websocket:
        print("🔌 Connected to WebSocket. Waiting for events...")
        try:
            while True:
                message = await websocket.recv()
                print(f"   📡 Update: {message}")
                
                data = json.loads(message)
                if data['status'] == 'completed':
                    print("✅ Processing Completed!")
                    break
                if data['status'] == 'failed':
                    print("❌ Processing Failed.")
                    break
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection Closed.")
            
if __name__ == "__main__":
    test_health()
    test_upload()
    test_chat_stream()