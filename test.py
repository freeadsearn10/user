import requests

API_URL = "https://msgrush-backend-258291301565.us-central1.run.app/api"
API_KEY = "sk_853dba57f90f56dcfb6f701950b04a39c3d50cb166dc13906089479a4ad64a80"

def send_sms():
    url = f"{API_URL}/sms-api/send"

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "sender_id": "Facebook",
        "recipients": ["+23674299523"],
        "message": "গিফট তোমার pachaa দিয়া দিব 😀"
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(response.json())
    except requests.exceptions.RequestException as e:
        print("Error:", e)

if __name__ == "__main__":
    send_sms()
()
