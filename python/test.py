import requests

guess_payload = {'guess': 'Barbie'}
response = requests.post("http://127.0.0.1:5000/submit-guess", guess_payload)
print(response.text)