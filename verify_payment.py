from soundwarapp import create_app, db
from soundwarapp.models import User
from flask_jwt_extended import create_access_token
import soundwarapp.myroutes.payments as payments_module

app = create_app('testing')
app.config.update(TESTING=True)

with app.app_context():
    db.drop_all()
    db.create_all()
    user = User(email='payuser@example.com', username='payuser', name='Pay User', password_hash='hashed', roles=['artist'])
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))

class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
    def json(self):
        return self._payload


def fake_post(*args, **kwargs):
    return FakeResponse({'status': 'success', 'message': 'OK', 'data': {'id': 123, 'link': 'https://checkout.flutterwave.com/test'}})

payments_module.requests.post = fake_post
client = app.test_client()
resp = client.post('/api/payments/initialize', headers={'Authorization': f'Bearer {token}'}, json={'tx_ref': 'SW-test-ref-12345'})
print(resp.status_code)
print(resp.get_json())
