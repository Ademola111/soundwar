from soundwarapp import create_app

app = create_app('testing')
app.config.update(TESTING=True)
client = app.test_client()

payload_weak = {
 'name':'Test User', 'username':'Test User', 'email':'testuser@example.com', 'password':'password1', 'role':'voter'
}
resp = client.post('/api/auth/register', json=payload_weak)
print('WEAK STATUS', resp.status_code)
print('WEAK JSON', resp.get_data(as_text=True))

payload_strong = {
 'name':'Strong User', 'username':'StrongUser', 'email':'strong@example.com', 'password':'Str0ng!Pass', 'role':'voter'
}
resp2 = client.post('/api/auth/register', json=payload_strong)
print('STRONG STATUS', resp2.status_code)
print('STRONG JSON', resp2.get_data(as_text=True))
