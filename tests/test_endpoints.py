import requests
import json
import time

def test_endpoints():
    base_url = "http://localhost:5000"
    results = []

    # Test 1: Get paragraph
    print("\n1. Testing /get_paragraph endpoint...")
    try:
        response = requests.get(f"{base_url}/get_paragraph")
        assert response.status_code == 200
        data = response.json()
        assert "paragraph" in data
        print("✅ Success: Got paragraph:", data["paragraph"][:50] + "...")
        results.append(("Get Paragraph", "Pass"))
    except Exception as e:
        print("❌ Error:", str(e))
        results.append(("Get Paragraph", f"Fail: {str(e)}"))

    # Test 2: Submit test results
    print("\n2. Testing /submit_results endpoint...")
    try:
        test_data = {
            "wpm": 60,
            "accuracy": 95,
            "typing_time": 60,
            "session_id": f"test_{int(time.time())}",
            "progress": [30, 40, 50, 55, 60]
        }
        response = requests.post(f"{base_url}/submit_results", json=test_data)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        print("✅ Success: Results submitted, session ID:", data["session_id"])
        results.append(("Submit Results", "Pass"))

        # Test 3: Get results page
        print(f"\n3. Testing /results/{data['session_id']} endpoint...")
        response = requests.get(f"{base_url}/results/{data['session_id']}")
        assert response.status_code == 200
        print("✅ Success: Results page loads")
        results.append(("View Results", "Pass"))
    except Exception as e:
        print("❌ Error:", str(e))
        results.append(("Submit/View Results", f"Fail: {str(e)}"))

    # Print summary
    print("\n=== Test Summary ===")
    for test, result in results:
        status = "✅" if "Pass" in result else "❌"
        print(f"{status} {test}: {result}")

if __name__ == "__main__":
    test_endpoints()