import requests

def test_accountant_approval():
    base_url = "http://localhost:8008/api/v1" 
    
    # 1. Login as Accountant
    print("Logging in as Accountant...")
    login_data = {
        "username": "account@neco.gov.ng",
        "password": "Account123"
    }
    try:
        response = requests.post(f"{base_url}/auth/login", data=login_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful!")
    except Exception as e:
        print(f"Login failed: {e}")
        if 'response' in locals():
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
        return

    # 2. Attempt to approve a school
    school_code = "0020001" 
    print(f"Attempting to approve school {school_code}...")
    try:
        url = f"{base_url}/data/schools/{school_code}/approve?accrd_year=2026"
        response = requests.post(url, headers=headers)
        
        if response.status_code == 200:
            print("SUCCESS: Accountant approved the school!")
        elif response.status_code == 403:
            print("FAILURE: Still getting 403 Forbidden.")
        elif response.status_code == 404:
            print("NOTE: School not found (404), but no 403 Forbidden! Success in terms of permissions.")
        else:
            print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_accountant_approval()
