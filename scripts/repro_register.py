from soundwarapp import create_app
from flask import json

app = create_app('testing')
app.config.update(TESTING=True)
client = app.test_client()

payload = {
    'username': 'TestUser',
    'email': 'testuser@example.com',
    'password': 'Str0ng!Pass1',
    'role': 'voter',
    'name': 'Test User',
    'artistName': 'Test Artist',
    'genre': 'Test Genre'
}

resp = client.post('/api/auth/register', json=payload)
print('status:', resp.status_code)
print('headers:', dict(resp.headers))
print('body:', resp.get_data(as_text=True))
