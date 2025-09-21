# safe_headers.py
import requests

url = "https://pf.emigrants.ypes.gr/pf/?lang=en"   # غيّر للـURL اللى لك أو عندك إذن عليه
resp = requests.get(url, timeout=10)

print("Status:", resp.status_code)
print("\nResponse headers:")
for k, v in resp.headers.items():
    print(f"{k}: {v}")

# بعض رؤوس ممكن تدلك: Server, X-Powered-By, Set-Cookie, X-AspNet-Version
