import requests
import sys

url = 'http://127.0.0.1:8080/api/generate'
payload = {'model':'gpt-oss','prompt':'Hello from smoke test — please respond briefly.','stream':False}
try:
    r = requests.post(url, json=payload, timeout=30)
    print('STATUS', r.status_code)
    print('BODY', r.text)
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
