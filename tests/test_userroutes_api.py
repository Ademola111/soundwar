import unittest, json, requests
from datetime import datetime, timezone, timedelta
from io import BytesIO
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import create_access_token, get_jti
from werkzeug.security import generate_password_hash, check_password_hash
from styleitapp import create_app, db
from styleitapp.models import (Cities, State, Lga, Customer, States, Login, Posting, Comment, 
                               Designer, Bookappointment, Subscription, Notification, TokenBlocklist,
                               Payment)

"""Base API Test Case"""
class BaseApiTestCase(unittest.TestCase):
    def setUp(self):
        self.email_patcher = patch("styleitapp.myroutes.userroutes.send_email")
        self.mock_send_email = self.email_patcher.start()
        self.mock_send_email.return_value = True
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        self.email_patcher.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()


"""Home Section"""
class ApiHomeTestCase(BaseApiTestCase):
    def test_api_home_guest(self):
        response = self.client.get('/api/home')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('user_type', data)
        self.assertEqual(data['user_type'], 'guest')
        self.assertIn('customer', data)
        self.assertIn('designer', data)
        self.assertIn('subscription_updates', data)

    def test_api_home_method_not_allowed(self):
        response = self.client.post('/api/home')
        self.assertEqual(response.status_code, 405)

"""LGA Section """
class ApiLgaTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Add a state and some LGAs for testing
        state = State(state_id=1, state_name='TestState')
        db.session.add(state)
        db.session.commit()
        lga1 = Lga(lga_id=1, lga_name='LGA1', lga_stateid=1)
        lga2 = Lga(lga_id=2, lga_name='LGA2', lga_stateid=1)
        db.session.add_all([lga1, lga2])
        db.session.commit()

    def test_get_lgas_by_state_success(self):
        response = self.client.get('/api/lga/1')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)
        self.assertTrue(any(lga['name'] == 'LGA1' for lga in data))
        self.assertTrue(any(lga['name'] == 'LGA2' for lga in data))

    def test_get_lgas_by_state_no_lgas(self):
        response = self.client.get('/api/lga/999')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_get_lgas_by_state_invalid_id(self):
        response = self.client.get('/api/lga/notanint')
        self.assertEqual(response.status_code, 404)  # Flask will return 404 for invalid int

    def test_get_lgas_by_state_db_error(self):
        # Simulate DB error by dropping the table
        db.session.execute(text('DROP TABLE lga'))
        db.session.commit()
        response = self.client.get('/api/lga/1')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertIn('error', data)


""" Customer Section """
"""Customer Login Section"""
class ApiCustomerLoginTestCase(BaseApiTestCase):

    def setUp(self):
        super().setUp()
        # Create state & lga
        self.state = State(state_name="TestState")
        self.lga = Lga(lga_name="TestLGA")
        db.session.add_all([self.state, self.lga])
        db.session.commit()

        db.session.refresh(self.state)
        db.session.refresh(self.lga)

        # Create customer
        self.customer = Customer(
            cust_id=1,
            cust_email="test@example.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="John",
            cust_lname="Doe",
            cust_phone="1234567890",
            cust_address="123 Test St",
            cust_username="johndoe",
            cust_gender="male",
            cust_regdate=datetime.now(timezone.utc),
            cust_pic="profile.png",
            cust_status="actived",
            cust_nin="12345678901",
            cust_passport="passport.png",
            cust_vinpic="vin.png",
            cust_city="TestCity",
            cust_state="TestState",
            cust_access="actived",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

    def test_login_success(self):
        """✅ Test successful login"""
        response = self.client.post(
            "/api/user/customer/login",
            data=json.dumps({"email": "test@example.com", "pwd": "password123"}),
            content_type="application/json"
        )
        data = json.loads(response.data.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')
        self.assertIn('access_token', data)
        self.assertEqual(data['customer']['email'], "test@example.com")

    def test_login_missing_fields(self):
        """❌ Test login with missing fields"""
        response = self.client.post(
            "/api/user/customer/login",
            data=json.dumps({}),
            content_type="application/json"
        )
        data = json.loads(response.data.decode())

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'danger')
        self.assertEqual(data['message'], 'Invalid Credentials')

    def test_login_wrong_password(self):
        """⚠️ Test login with wrong password"""
        response = self.client.post(
            "/api/user/customer/login",
            data=json.dumps({"email": "test@example.com", "pwd": "wrongpassword"}),
            content_type="application/json"
        )
        data = json.loads(response.data.decode())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(data['status'], 'warning')
        self.assertEqual(data['message'], 'Kindly supply a valid email address and password')

    def test_login_nonexistent_user(self):
        """⚠️ Test login with non-existent email"""
        response = self.client.post(
            "/api/user/customer/login",
            data=json.dumps({"email": "notfound@example.com", "pwd": "password123"}),
            content_type="application/json"
        )
        data = json.loads(response.data.decode())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(data['status'], 'warning')
        self.assertEqual(data['message'], 'Kindly supply valid credentials')


"""Customer Signup"""
class ApiCustomerSignupTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create sample state and lga for testing Nigeria signup (country=161)
        self.state = State(state_name="Lagos")
        db.session.add(self.state)
        db.session.commit()  # must commit before using self.state.state_id

        self.lga = Lga(lga_name="Ikeja")
        db.session.add(self.lga)
        db.session.commit()

        self.signup_url = "/api/customer/signup"

    def test_signup_success_foreign(self):
        payload = {
            "fname": "Alice",
            "lname": "Smith",
            "username": "alicesmith",
            "email": "alice@gmail.com",
            "pwd": "Password123",
            "cpwd": "Password123",
            "gender": "female",
            "phone": "+44123456789",
            "address": "221B Baker Street",
            "country": "840",              # foreign, sent as integer
            "state": "California",       # string
            "cities": "Los Angeles",     # string
            "passport": "X12345678"
        }
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.json["status"])
        self.assertIn("access_token", response.json)


    def test_signup_success_nigeria(self):
        data = {
            "fname": "John",
            "lname": "Doe",
            "username": "johndoe",
            "email": "john@gmail.com",
            "phone": "08012345678",
            "pwd": "password123",
            "cpwd": "password123",
            "address": "123 street",
            "country": "161",
            "state": str(self.state.state_id),
            "lga": str(self.lga.lga_id),
            "gender": "male",
            "nin": "12345678901"
        }
        res = self.client.post(self.signup_url, data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("success", res.json["status"])
        self.assertIn("access_token", res.json)


    def test_signup_missing_fields(self):
        data = {
            "fname": "John",
            "lname": "Doe",
            "username": "johndoe",
            "email": "john@gmail.com",
            # phone missing
            "pwd": "password123",
            "cpwd": "password123",
            "address": "123 street",
            "country": "161",
            "state": str(self.state.state_id),
            "lga": str(self.lga.lga_id),
            "gender": "male",
            "nin": "12345678901"
        }
        res = self.client.post(self.signup_url, data=data)
        self.assertEqual(res.status_code, 400)
        self.assertIn("One or more fields are empty", res.json["message"])


    def test_signup_invalid_email(self):
        data = {
            "fname": "John",
            "lname": "Doe",
            "username": "johndoe",
            "email": "john@invalid.com",  # not allowed
            "phone": "08012345678",
            "pwd": "password123",
            "cpwd": "password123",
            "address": "123 street",
            "country": "161",
            "state": str(self.state.state_id),
            "lga": str(self.lga.lga_id),
            "gender": "male",
            "nin": "12345678901"
        }
        res = self.client.post(self.signup_url, data=data)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Kindly provide a valid email", res.json["message"])


    def test_signup_password_mismatch(self):
        data = {
            "fname": "Jane",
            "lname": "Doe",
            "username": "janedoe",
            "email": "jane@gmail.com",
            "phone": "08011111111",
            "pwd": "password123",
            "cpwd": "password321",  # mismatch
            "address": "321 street",
            "country": "161",
            "state": str(self.state.state_id),
            "lga": str(self.lga.lga_id),
            "gender": "female",
            "nin": "12345678901"
        }
        res = self.client.post(self.signup_url, data=data)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Password match error", res.json["message"])


    def test_signup_duplicate_email(self):
        # Create existing user
        hashed_pwd = generate_password_hash("password123")
        customer = Customer(
            cust_fname="Old", cust_lname="User", cust_username="olduser",
            cust_email="old@gmail.com", cust_pass=hashed_pwd,
            cust_gender="male", cust_phone="08099999999",
            cust_address="Old address", cust_countryid="161",
            cust_stateid=self.state.state_id, cust_lgaid=self.lga.lga_id,
            cust_nin="12345678901"
        )
        db.session.add(customer)
        db.session.commit()

        # Try signup with same email
        data = {
            "fname": "New",
            "lname": "User",
            "username": "newuser",
            "email": "old@gmail.com",
            "phone": "08012312345",
            "pwd": "password123",
            "cpwd": "password123",
            "address": "New address",
            "country": "161",
            "state": str(self.state.state_id),
            "lga": str(self.lga.lga_id),
            "gender": "male",
            "nin": "98765432109"
        }
        res = self.client.post(self.signup_url, data=data)
        self.assertEqual(res.status_code, 409)
        self.assertIn("already registered", res.json["message"])


    def test_signup_invalid_nin_length(self):
        """❌ Should fail when NIN length is not 11."""
        data = {
            'fname': 'Paul',
            'lname': 'Okoye',
            'username': 'poko',
            'email': 'paul@gmail.com',
            'phone': '08044445555',
            'pwd': 'password123',
            'cpwd': 'password123',
            'address': 'Lekki',
            'country': '161',
            'state': '1',
            'lga': '1',
            'gender': 'male',
            'nin': '12345'  # invalid
        }
        response = self.client.post('/api/customer/signup', data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Provide a valid NIN', response.json['message'])


"""Customer profile """
class ApiCustomerProfileTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        
        # create test data
        self.state = State(state_name="Lagos")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Ikeja", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.customer = Customer(
            cust_fname="John",
            cust_lname="Doe",
            cust_email="john@example.com",
            cust_phone="08012345678",
            cust_address="123 Test Street",
            cust_username="johnny",
            cust_gender="male",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id,
            cust_status="actived",
            cust_access="actived",
            cust_pass="hashedpassword123"
        )
        db.session.add(self.customer)
        db.session.commit()

        self.token = create_access_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_get_profile_success(self):
        response = self.client.get("/api/customer/profile", headers=self.headers)
        data = json.loads(response.data.decode())

        assert response.status_code == 200
        assert data["customer"]["fname"] == "John"
        assert data["customer"]["lname"] == "Doe"
        assert data["customer"]["email"] == "john@example.com"
        assert data["customer"]["state"][0]["name"] == "Lagos"
        assert data["customer"]["lga"][0]["name"] == "Ikeja"

    def test_get_profile_unauthorized_user_type(self):
        token = create_access_token(identity=f"designer:{self.customer.cust_id}")
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/api/customer/profile", headers=headers)

        assert response.status_code == 401
        assert b"Unauthorized access" in response.data

    def test_get_profile_inactive_status(self):
        self.customer.cust_status = "deactived"
        db.session.commit()

        response = self.client.get("/api/customer/profile", headers=self.headers)
        data = json.loads(response.data.decode())

        # ✅ Adjusted expectation: route still returns profile JSON
        assert response.status_code == 200
        assert data["status"] == "warning"
        assert "confirm" in data["message"].lower()
        assert "redirect" in data

    def test_get_profile_inactive_access(self):
        self.customer.cust_access = "deactived"
        db.session.commit()

        response = self.client.get("/api/customer/profile", headers=self.headers)
        data = json.loads(response.data.decode())

        # ✅ Adjusted expectation: route still returns profile JSON
        assert response.status_code == 200
        assert data["status"] == "danger"
        assert "deactivated" in data["message"].lower()
        assert "redirect" in data

    def test_put_profile_success(self):
        update_data = {
            "fname": "Jane",
            "lname": "Smith",
            "email": "jane@example.com",
            "phone": "08098765432",
            "address": "456 Update Avenue"
        }
        response = self.client.put(
            "/api/customer/profile",
            headers=self.headers,
            data=json.dumps(update_data),
            content_type="application/json"
        )
        data = json.loads(response.data.decode())

        assert response.status_code == 200
        assert data["status"] == "success"
        assert data["message"] == "Profile updated successfully"

        # ✅ Query inside app context
        updated_cus = Customer.query.get(self.customer.cust_id)
        assert updated_cus.cust_fname == "Jane"
        assert updated_cus.cust_email == "jane@example.com"

    def test_put_profile_missing_fields(self):
        incomplete_data = {"fname": "Jane"}  # Missing other fields
        response = self.client.put(
            "/api/customer/profile",
            headers=self.headers,
            data=json.dumps(incomplete_data),
            content_type="application/json"
        )
        data = json.loads(response.data.decode())

        assert response.status_code == 400
        assert data["status"] == "warning"
        assert data["message"] == "One or more fields are empty"


""" Customer Logout """
class ApiCustomerLogoutTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Setup state and LGA
        self.state = State(state_name="Lagos")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Ikeja", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Setup customer
        self.customer = Customer(
            cust_fname="John",
            cust_lname="Doe",
            cust_email="john@example.com",
            cust_phone="08012345678",
            cust_address="123 Test Street",
            cust_username="johnny",
            cust_gender="male",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id,
            cust_status="actived",
            cust_access="actived",
            cust_pass="hashedpassword123"
        )
        db.session.add(self.customer)
        db.session.commit()

        # Setup login record
        self.login = Login(
            login_custid=self.customer.cust_id,
            login_email=self.customer.cust_email,
            login_date=datetime.now(timezone.utc),
            logout_date=None
        )
        db.session.add(self.login)
        db.session.commit()

        # JWT token for auth
        self.token = create_access_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_logout_success(self):
        response = self.client.post("/api/customer/logout", headers=self.headers)
        data = response.get_json()

        assert response.status_code == 200
        assert data["status"] == "success"
        assert data["message"] == "Logout successful"
        assert data["redirect"] == "/"

        # ✅ Verify DB record updated
        lo = Login.query.filter_by(login_custid=self.customer.cust_id).first()
        assert lo.logout_date is not None

    def test_logout_wrong_user_type(self):
        token = create_access_token(identity=f"admin:{self.customer.cust_id}")
        headers = {"Authorization": f"Bearer {token}"}

        response = self.client.post("/api/customer/logout", headers=headers)
        data = response.get_json()

        assert response.status_code == 401
        assert data["status"] == "error"
        assert data["message"] == "Unauthorized access"
        assert data["redirect"] == "/"

    def test_logout_invalid_token(self):
        headers = {"Authorization": "Bearer invalidtoken"}

        response = self.client.post("/api/customer/logout", headers=headers)
        data = response.get_json()

        assert response.status_code == 422  # invalid token
        assert "msg" in data

    def test_logout_no_login_record(self):
        Login.query.delete()
        db.session.commit()

        response = self.client.post("/api/customer/logout", headers=self.headers)
        data = response.get_json()

        assert response.status_code == 200
        assert data["status"] == "success"
        assert data["message"] == "Logout successful"
        assert data["redirect"] == "/"

        jti = get_jti(self.token)
        blocked = TokenBlocklist.query.filter_by(jti=jti).first()
        assert blocked is not None
        assert blocked.jti_custid == self.customer.cust_id

    def test_logout_token_added_to_blocklist(self):
        response = self.client.post("/api/customer/logout", headers=self.headers)
        data = response.get_json()

        assert response.status_code == 200
        assert data["status"] == "success"
        assert data["message"] == "Logout successful"
        assert data["redirect"] == "/"
        db.session.expire_all()
        # ✅ Verify token is in blocklist
        jti = get_jti(self.token)  # requires flask_jwt_extended.get_jti
        blocked = TokenBlocklist.query.filter_by(jti=jti).first()
        assert blocked is not None
        assert blocked.jti == jti


""" Customer Forgotten Password"""
class ApiCustomerForgottenPasswordTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create a sample customer in test database
        self.customer = Customer(
            cust_username="testuser",
            cust_email="test@example.com",
            cust_pass=generate_password_hash("OldPassword123"),
            cust_fname="Test",
            cust_lname="User",
            cust_phone="08012345678",
            cust_address="123 Test St",
            cust_gender="male"
        )
        db.session.add(self.customer)
        db.session.commit()
        self.url = "/api/user/customer/forgottenpassword"

    def test_missing_fields(self):
        """Test request with missing fields"""
        payload = {"username": "testuser", "email": "test@example.com"}
        response = self.client.post(self.url, data=json.dumps(payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "warning")

    def test_passwords_do_not_match(self):
        """Test when pwd and cpwd do not match"""
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "pwd": "NewPassword123",
            "cpwd": "MismatchPassword"
        }
        response = self.client.post(self.url, data=json.dumps(payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "danger")
        self.assertIn("Passwords do not match", response.json["message"])

    def test_invalid_email(self):
        """Test when email does not exist"""
        payload = {
            "username": "testuser",
            "email": "wrong@example.com",
            "pwd": "NewPassword123",
            "cpwd": "NewPassword123"
        }
        response = self.client.post(self.url, data=json.dumps(payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["status"], "danger")
        self.assertIn("Invalid email", response.json["message"])

    def test_reuse_old_password(self):
        """Test when the new password is same as old one"""
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "pwd": "OldPassword123",
            "cpwd": "OldPassword123"
        }
        response = self.client.post(self.url, data=json.dumps(payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "danger")
        self.assertIn("used earlier", response.json["message"])

    def test_invalid_username_with_valid_email(self):
        """Test invalid username but valid email"""
        payload = {
            "username": "wronguser",
            "email": "test@example.com",
            "pwd": "ValidNewPass123",
            "cpwd": "ValidNewPass123"
        }
        response = self.client.post(self.url, data=json.dumps(payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "danger")
        self.assertIn("Invalid username", response.json["message"])

    def test_successful_password_update(self):
        """Test successful password reset"""
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "pwd": "ValidNewPass123",
            "cpwd": "ValidNewPass123"
        }
        response = self.client.post(self.url, data=json.dumps(payload),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "success")
        self.assertIn("Password updated successfully", response.json["message"])
        self.assertEqual(response.json["redirect"], "/api/user/customer/login")


""" Customer Details by ID """
class ApiCustomerDetailTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create a sample customer inside real app context
        customer = Customer(
            cust_username="testuser",
            cust_email="test@example.com",
            cust_pass=generate_password_hash("Password123"),
            cust_fname="Test",
            cust_lname="User",
            cust_phone="08012345678",
            cust_address="123 Lagos Street",
            cust_gender="male"
        )
        db.session.add(customer)
        db.session.commit()
        self.customer_id = customer.cust_id  # store ID
        self.customer_email = customer.cust_email
        self.customer_fname = customer.cust_fname
        self.customer_lname = customer.cust_lname

        self.url = f"/api/customer/{self.customer_id}"

    def _auth_header(self, user_type="customer", user_id=None):
        """Helper to generate Authorization header with JWT"""
        if user_id is None:
            user_id = self.customer_id
        
        identity = f"{user_type}:{user_id}"
        token = create_access_token(identity=identity)

        return {"Authorization": f"Bearer {token}"}

    def test_unauthorized_access_without_token(self):
        """Should return 401 when no JWT is provided"""
        response = self.client.get(f"/api/customer/{self.customer_id}")  # self.app is test client
        self.assertEqual(response.status_code, 401)
        self.assertIn("Missing JWT", response.json["msg"])

    def test_customer_not_found(self):
        """Should return 404 if customer does not exist"""
        headers = self._auth_header(user_type="customer", user_id=9999)
        response = self.client.get("/api/customer/9999", headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["status"], "error")
        self.assertIn("Customer not found", response.json["message"])

    def test_get_customer_as_customer(self):
        """Should return customer details if logged in as customer"""
        headers = self._auth_header(user_type="customer")
        response = self.client.get(f"/api/customer/{self.customer_id}", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json["customer"]
        self.assertEqual(data["id"], self.customer_id)
        self.assertEqual(data["fname"], "Test")
        self.assertEqual(data["lname"], "User")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["user_type"], "customer")

    def test_get_customer_as_designer(self):
        """Should still return customer details if logged in as designer"""
        headers = self._auth_header(user_type="designer", user_id=self.customer_id)
        response = self.client.get(self.url, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json["customer"]
        self.assertEqual(data["id"], self.customer_id)
        self.assertEqual(data["fname"], "Test")
        self.assertEqual(data["lname"], "User")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["user_type"], "designer")


""" Book Appointment """
class ApiBookAppointmentTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create a sample customer
        customer = Customer(
            cust_username="custuser",
            cust_email="cust@example.com",
            cust_pass=generate_password_hash("Password123"),
            cust_fname="Cust",
            cust_lname="User",
            cust_phone="08011112222",
            cust_address="1 Street Lagos",
            cust_gender="male",
        )
        db.session.add(customer)
        db.session.commit()
        self.customer_id = customer.cust_id
        self.url = "/api/bookappointment"

    def _auth_header(self, user_type="customer", user_id=None):
        """Generate Authorization header with JWT"""
        if user_id is None:
            user_id = self.customer_id
        identity = f"{user_type}:{user_id}"
        token = create_access_token(identity=identity)
        return {"Authorization": f"Bearer {token}"}

    def test_unauthorized_without_token(self):
        """Should return 401 when no JWT is provided"""
        response = self.client.post(self.url, json={})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Missing JWT", response.json["msg"])

    def test_unauthorized_user_type(self):
        """Should return 401 when user is not a customer"""
        headers = self._auth_header(user_type="designer", user_id=123)
        payload = {
            "dsignername": "45",
            "bookingdate": "2025-09-10",
            "bookingtime": "10:00",
            "collectiondate": "2025-09-15",
            "collectiontime": "14:00",
        }
        response = self.client.post(self.url, headers=headers, json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized access", response.json["message"])

    def test_missing_fields(self):
        """Should return 400 when required fields are missing"""
        headers = self._auth_header()
        payload = {
            "dsignername": "45",
            "bookingdate": "2025-09-10",
            # missing bookingtime, collectiondate, collectiontime
        }
        response = self.client.post(self.url, headers=headers, json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["status"], "warning")
        self.assertIn("Kindly fill each field", response.json["message"])

    def test_successful_booking(self):
        """Should return 200 and create booking successfully"""
        headers = self._auth_header()
        payload = {
            "dsignername": "45",
            "bookingdate": "2025-09-10",
            "bookingtime": "10:00",
            "collectiondate": "2025-09-15",
            "collectiontime": "14:00",
        }
        response = self.client.post(self.url, headers=headers, json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "success")
        self.assertIn("Booking successful", response.json["message"])

        # Verify DB entry was created
        booking = Bookappointment.query.filter_by(
            ba_custid=self.customer_id
        ).first()
        self.assertIsNotNone(booking)
        notifs = Notification.query.filter_by(
            notify_baid=booking.ba_id
        ).all()
        self.assertEqual(len(notifs), 2)


"""designer section"""

"""Designer Signup"""
class ApiDesignerSignupTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.app.config['UPLOAD_FOLDER2'] = '/tmp'  # mock folder for uploads
        state = State(state_name="Test State")
        db.session.add(state)
        db.session.commit()

        lga = Lga(lga_name="Test LGA", lga_stateid=state.state_id)
        db.session.add(lga)
        db.session.commit()

        # Save their IDs for later use
        self.state_id = state.state_id
        self.lga_id = lga.lga_id
            
    def test_successful_signup_with_nin(self):
        data = {
            'fname': 'John',
            'lname': 'Doe',
            'busname': 'Doe Fashion',
            'email': 'johndoe@gmail.com',
            'phone': '1234567890',
            'pwd': 'password123',
            'cpwd': 'password123',
            'address': '123 Street',
            'country': '161',
            'state': str(self.state_id),   # ✅ use real state id
            'lga': str(self.lga_id),
            'gender': 'male',
            'cities': '',
            'nin': '12345678901',  # ✅ valid nin
            'passport': ''
        }
        response = self.client.post(
            '/api/designer/signup',
            data=data,  # ✅ send as form, not JSON
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn(b'Profile setup completed', response.data)

    def test_signup_with_existing_email(self):
        designer = Designer(
            desi_fname="Jane",
            desi_lname="Doe",
            desi_businessName="Jane Wear",
            desi_email="janedoe@gmail.com",
            desi_pass="hashedpass",
            desi_nin="12345678901",
            desi_address="123 St",
            desi_gender="female",
            desi_phone="1234567890"  # ✅ added phone
        )
        db.session.add(designer)
        db.session.commit()

        data = {
            'fname': 'John',
            'lname': 'Doe',
            'busname': 'Doe Fashion',
            'email': 'janedoe@gmail.com',  # duplicate
            'phone': '1234567890',
            'pwd': 'password123',
            'cpwd': 'password123',
            'address': '123 Street',
            'country': '161',
            'state': str(self.state_id),   # ✅ use real state id
            'lga': str(self.lga_id),
            'gender': 'male',
            'cities': '',
            'nin': '12345678901',  # ✅ valid nin
            'passport': ''
        }
        response = self.client.post(
            '/api/designer/signup',
            data=data,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'This email is already registered', response.data)

    def test_signup_with_short_password(self):
        data = {
            'fname': 'John',
            'lname': 'Doe',
            'busname': 'Doe Fashion',
            'email': 'shortpwd@gmail.com',
            'phone': '1234567890',
            'pwd': 'short',
            'cpwd': 'short',
            'address': '123 Street',
            'country': '161',
            'state': str(self.state_id),   # ✅ use real state id
            'lga': str(self.lga_id),
            'gender': 'male',
            'cities': '',
            'nin': '12345678901',  # ✅ valid nin
            'passport': ''
        }
        response = self.client.post(
            '/api/designer/signup',
            data=data,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Password should be at least 8 characters long', response.data)

    def test_signup_with_mismatched_passwords(self):
        data = {
            'fname': 'John',
            'lname': 'Doe',
            'busname': 'Doe Fashion',
            'email': 'mismatch@gmail.com',
            'phone': '1234567890',
            'pwd': 'password123',
            'cpwd': 'password321',
            'address': '123 Street',
            'country': '161',
            'state': str(self.state_id),   # ✅ use real state id
            'lga': str(self.lga_id),
            'gender': 'male',
            'cities': '',
            'nin': '12345678901',  # ✅ valid nin
            'passport': ''
        }
        response = self.client.post(
            '/api/designer/signup',
            data=data,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Password match error', response.data)

    def test_signup_with_invalid_email_domain(self):
        data = {
            'fname': 'John',
            'lname': 'Doe',
            'busname': 'Doe Fashion',
            'email': 'johndoe@fake.com',
            'phone': '1234567890',
            'pwd': 'password123',
            'cpwd': 'password123',
            'address': '123 Street',
            'country': '161',
            'state': str(self.state_id),   # ✅ use real state id
            'lga': str(self.lga_id),
            'gender': 'male',
            'cities': '',
            'nin': '12345678901',  # ✅ valid nin
            'passport': ''
        }
        response = self.client.post(
            '/api/designer/signup',
            data=data,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Kindly provide a valid email', response.data)


"""Designer Login """
class ApiDesignerLoginTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create test state and lga
        state = State(state_name="Test State")
        db.session.add(state)
        db.session.commit()

        lga = Lga(lga_name="Test LGA", lga_stateid=state.state_id)
        db.session.add(lga)
        db.session.commit()

        self.state_id = state.state_id
        self.lga_id = lga.lga_id

        # Create a sample designer
        self.active_designer = Designer(
            desi_fname="Active",
            desi_lname="Designer",
            desi_email="janedoe@gmail.com",
            desi_pass=generate_password_hash("password123"),
            desi_phone="1111111111",
            desi_address="123 Fashion Street",
            desi_gender="female",
            desi_stateid=self.state_id,
            desi_lgaid=self.lga_id,
            desi_status="actived",  # 👈 active
            desi_businessName="Active Styles"
        )
        db.session.add(self.active_designer)

        # Deactivated designer
        self.deactivated_designer = Designer(
            desi_fname="Deactivated",
            desi_lname="Designer",
            desi_email="janedoe@gmail.com",
            desi_pass=generate_password_hash("password123"),
            desi_phone="2222222222",
            desi_address="456 Fashion Avenue",
            desi_gender="female",
            desi_stateid=self.state_id,
            desi_lgaid=self.lga_id,
            desi_status="deactivated",  # 👈 deactivated
            desi_businessName="Deactivated Styles"
        )
        db.session.add(self.deactivated_designer)
        db.session.commit()

    def test_login_success(self):
        """Should login successfully with valid credentials"""
        payload = {"email": "janedoe@gmail.com", "pwd": "password123"}
        response = self.client.post("/api/designer/login", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login successful", response.data)
        self.assertIn(b"token", response.data)

    def test_login_invalid_email(self):
        """Should fail with invalid email"""
        payload = {"email": "wrong@gmail.com", "pwd": "password123"}
        response = self.client.post("/api/designer/login", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid email or password", response.data)

    def test_login_invalid_password(self):
        """Should fail with wrong password"""
        payload = {"email": "janedoe@gmail.com", "pwd": "wrongpass"}
        response = self.client.post("/api/designer/login", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid email or password", response.data)

    def test_login_missing_fields(self):
        """Should fail if fields are missing"""
        payload = {"email": "janedoe@gmail.com"}  # no password
        response = self.client.post("/api/designer/login", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid Credentials", response.data)

    def test_login_deactivated_account(self):
        """Should block login if account is deactivated"""
        designer = Designer.query.filter_by(desi_email="janedoe@gmail.com").first()
        designer.desi_status = "deactived"
        db.session.commit()

        payload = {"email": "janedoe@gmail.com", "pwd": "password123"}
        response = self.client.post("/api/designer/login", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Your account is either suspended, banned, dormant or deactive. Kindly contact support to activate your account", response.data)

"""designer profile """
class ApiDesignerProfileTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # create state & lga
        state = State(state_name="Test State")
        db.session.add(state)
        db.session.commit()

        lga = Lga(lga_name="Test LGA", lga_stateid=state.state_id)
        db.session.add(lga)
        db.session.commit()

        self.state_id = state.state_id
        self.lga_id = lga.lga_id

        # create designer
        designer = Designer(
            desi_fname="Jane",
            desi_lname="Doe",
            desi_email="janedoe@gmail.com",
            desi_pass=generate_password_hash("password123"),
            desi_phone="1111111111",
            desi_address="123 Fashion Street",
            desi_gender="female",
            desi_stateid=self.state_id,
            desi_lgaid=self.lga_id,
            desi_status="actived",
            desi_access="actived",
            desi_businessName="Jane Styles"
        )
        db.session.add(designer)
        db.session.commit()
        self.designer_id = designer.desi_id   # ✅ only store ID, not object

    def get_token(self, designer_id=None):
        """Helper to generate JWT for a designer"""
        if not designer_id:
            designer_id = self.designer_id
        identity = f"designer:{designer_id}"
        token = create_access_token(identity=identity)
        return token

    def test_get_profile_success(self):
        token = self.get_token()
        response = self.client.get(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Jane Styles", response.data)

    def test_designer_status_deactivated(self):
        designer = Designer.query.get(self.designer_id)
        designer.desi_status = "deactived"
        db.session.commit()

        token = self.get_token()
        response = self.client.get(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Please confirm your account", response.data)

    def test_designer_access_deactivated(self):
        designer = Designer.query.get(self.designer_id)
        designer.desi_access = "deactived"
        db.session.commit()

        token = self.get_token()
        response = self.client.get(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Your account has been deactivated", response.data)

    def test_designer_not_found(self):
        designer = Designer.query.get(self.designer_id)
        db.session.delete(designer)
        db.session.commit()

        token = self.get_token(self.designer_id)
        response = self.client.get(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Designer not found", response.data)

    def test_put_profile_success(self):
        token = self.get_token()
        payload = {
            "fname": "Janet",
            "lname": "Smith",
            "email": "janetsmith@gmail.com",
            "phone": "9999999999",
            "address": "New Address"
        }
        response = self.client.put(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Profile updated successfully", response.data)

    def test_put_profile_missing_fields(self):
        token = self.get_token()
        payload = {"fname": "OnlyName"}  # missing other required fields
        response = self.client.put(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"},
            json=payload
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"is required", response.data)

    def test_unauthorized_user_type(self):
        token = create_access_token(identity="customer:1")  # wrong user type
        response = self.client.get(
            "/api/designer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Unauthorized access", response.data)


""" Designer Forgotten Password"""
class ApiDesignerForgottenPasswordTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create a designer for testing with all NOT NULL fields
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('hashedpassword'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()

    def test_forgotten_password_valid_email(self):
        response = self.client.post('/api/designer/forgottenpassword', json={
            'email': 'testdesigner@gmail.com',
            'businessname': 'TestDesigner',
            'pwd': 'newpassword',
            'cpwd': 'newpassword'
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)

    def test_forgotten_password_invalid_email(self):
        response = self.client.post('/api/designer/forgottenpassword', json={
            'email': 'nonexistent@gmail.com'
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)

    def test_forgotten_password_missing_email(self):
        response = self.client.post('/api/designer/forgottenpassword', json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)

    def test_forgotten_password_wrong_method(self):
        response = self.client.get('/api/designer/forgottenpassword')
        self.assertEqual(response.status_code, 308)


""" Designer Logout """
class ApiDesignerLogoutTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        # Add a login record for designer
        login = Login(login_email='testdesigner@gmail.com', login_desiid=1)
        db.session.add(login)
        db.session.commit()
        # Generate JWT token for designer
        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_logout_success(self):
        response = self.client.post('/api/designer/logout', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Logout successful')

    def test_logout_unauthorized_user_type(self):
        # Token for customer, not designer
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.post('/api/designer/logout', headers=headers)
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')

    def test_logout_no_token(self):
        response = self.client.post('/api/designer/logout')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_logout_not_logged_in(self):
        # Token for designer with no id
        token = create_access_token(identity='designer:')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.post('/api/designer/logout', headers=headers)
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Not logged in')


""" Posting """
class ApiPostingTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_posting_success(self):
        # Simulate file upload using Werkzeug's FileStorage
        img = (BytesIO(b"fake image data"), 'test.jpg')
        data = {
            'title': 'Test Post',
            'body': 'This is a test post.'
        }
        # Flask test client requires 'data' for multipart/form-data
        response = self.client.post(
            '/api/posting',
            data={
                'title': data['title'],
                'body': data['body'],
                'img': (img[0], img[1])
            },
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 201)
        resp_json = response.get_json()
        self.assertIn('message', resp_json)
        self.assertEqual(resp_json['message'], 'Post saved successfully')
        self.assertIn('post', resp_json)
        self.assertEqual(resp_json['post']['title'], 'Test Post')

    def test_posting_missing_fields(self):
        response = self.client.post(
            '/api/posting',
            data={'title': '', 'body': ''},
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        resp_json = response.get_json()
        self.assertIn('message', resp_json)
        self.assertEqual(resp_json['message'], 'Complete all fields')

    def test_posting_unauthorized_user_type(self):
        # Token for customer, not designer
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        img = (BytesIO(b"fake image data"), 'test.jpg')
        response = self.client.post(
            '/api/posting',
            data={
                'title': 'Test Post',
                'body': 'This is a test post.',
                'img': (img[0], img[1])
            },
            headers=headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 403)
        resp_json = response.get_json()
        self.assertIn('message', resp_json)
        self.assertEqual(resp_json['message'], 'Unauthorized access')

    def test_posting_no_token(self):
        img = (BytesIO(b"fake image data"), 'test.jpg')
        response = self.client.post(
            '/api/posting',
            data={
                'title': 'Test Post',
                'body': 'This is a test post.',
                'img': (img[0], img[1])
            },
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 401)
        resp_json = response.get_json()
        self.assertIn('msg', resp_json)


""" Appointment Status Update """
class ApiAppointmentStatusTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        customer = Customer(
            cust_id=1,
            cust_email='testcustomer@gmail.com',
            cust_username='TestCustomer',
            cust_fname='Test',
            cust_lname='Customer',
            cust_phone='08000000001',
            cust_address='456 Test Ave',
            cust_gender='female',
            cust_pass=generate_password_hash('password123'),
            cust_status='actived'
        )
        db.session.add(designer)
        db.session.add(customer)
        db.session.commit()
        # Create a Bookappointment
        appointment = Bookappointment(
            ba_id=1,
            ba_desiid=designer.desi_id,
            ba_custid=customer.cust_id,
            ba_bookingDate='2025-09-25',
            ba_bookingTime='10:00',
            ba_collectionDate='2025-09-26',
            ba_collectionTime='12:00',
            ba_status='not done'
        )
        db.session.add(appointment)
        db.session.commit()
        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_accept_appointment_success(self):
        response = self.client.post(
            '/api/appointment/status/1',
            json={'action': 'accept'},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Appointment accepted')

    def test_decline_appointment_success(self):
        response = self.client.post(
            '/api/appointment/status/1',
            json={'action': 'decline', 'reason': 'Not available'},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Appointment declined')

    def test_missing_action(self):
        response = self.client.post(
            '/api/appointment/status/1',
            json={},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Action is required')

    def test_decline_missing_reason(self):
        response = self.client.post(
            '/api/appointment/status/1',
            json={'action': 'decline'},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Decline reason is required')

    def test_appointment_not_found(self):
        response = self.client.post(
            '/api/appointment/status/999',
            json={'action': 'accept'},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Appointment not found')

    def test_unauthorized_access_no_token(self):
        response = self.client.post(
            '/api/appointment/status/1',
            json={'action': 'accept'}
        )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_unauthorized_access_wrong_user_type(self):
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.post(
            '/api/appointment/status/1',
            json={'action': 'accept'},
            headers=headers
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')


""" Designer Subscription Plan """
class ApiDesignerSubplanTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        # Add a subscription for designer
        sub = Subscription(
            sub_id=1,
            sub_desiid=designer.desi_id,
            sub_plan='premium',
            sub_date=datetime.now(),
            sub_startdate=datetime.now(),
            sub_enddate=datetime.now() + timedelta(days=30),
            sub_status='active',
            sub_ref=123456,
            sub_paystatus='paid'
        )
        db.session.add(sub)
        db.session.commit()
        # Add a notification for designer
        notification = Notification(
            notify_id=1,
            notify_desiid=designer.desi_id,
            notify_read='unread'
        )
        db.session.add(notification)
        db.session.commit()
        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_subplan_success(self):
        response = self.client.get('/api/designer/subplan', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('designer', data)
        self.assertIn('subscriptions', data)
        self.assertIn('pagination', data)
        self.assertIn('notifications', data)
        self.assertEqual(data['designer']['id'], 1)
        self.assertEqual(data['designer']['businessName'], 'TestDesigner')
        self.assertTrue(len(data['subscriptions']) > 0)

    def test_subplan_no_token(self):
        response = self.client.get('/api/designer/subplan')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_subplan_wrong_user_type(self):
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/api/designer/subplan', headers=headers)
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')

    def test_subplan_designer_not_found(self):
        token = create_access_token(identity='designer:999')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.get('/api/designer/subplan', headers=headers)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Designer not found')


""" Designer Subscribe """
class ApiDesignerSubscribeTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_subscribe_paid_plan_success(self):
        response = self.client.post('/api/designer/sub', json={'plan': '5000'}, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Subscription successful')
        self.assertIn('subscription', data)
        self.assertIn('payment', data)

    def test_subscribe_free_plan_redirect(self):
        response = self.client.post('/api/designer/sub', json={'plan': 'free'}, headers=self.headers, follow_redirects=False)
        # Should redirect to /api/free/activate
        self.assertEqual(response.status_code, 302)
        self.assertIn('/api/free/activate', response.headers.get('Location', ''))

    def test_subscribe_missing_plan(self):
        response = self.client.post('/api/designer/sub', json={}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Subscription plan is required')

    def test_subscribe_unauthorized_user_type(self):
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.post('/api/designer/sub', json={'plan': 'premium'}, headers=headers)
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')

    def test_subscribe_no_token(self):
        response = self.client.post('/api/designer/sub', json={'plan': 'premium'})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('msg', data)


""" Payment Processing """
class ApiPaymentTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        # Create a payment record
        payment = Payment(
            payment_id=1,
            payment_transNo=123456,
            payment_amount=1000,
            payment_desiid=designer.desi_id,
            payment_status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def test_payment_success(self):
        # Mock requests.post to avoid real API call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': True,
            'data': {'authorization_url': 'https://paystack.com/authorize'}
        }

        with patch('requests.post', return_value=mock_response):
            response = self.client.post('/api/payment', json={'refno': 123456}, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('authorization_url', data)

    def test_payment_missing_refno(self):
        response = self.client.post('/api/payment', json={}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'No reference number found in session')

    def test_payment_record_not_found(self):
        response = self.client.post('/api/payment', json={'refno': 999999}, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Payment record not found')

    def test_payment_designer_not_found(self):
        # Remove designer from DB
        Designer.query.delete()
        db.session.commit()
        response = self.client.post('/api/payment', json={'refno': 123456}, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Designer not found')

    def test_payment_unauthorized_access_no_token(self):
        response = self.client.post('/api/payment', json={'refno': 123456})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_payment_unauthorized_access_wrong_user_type(self):
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        response = self.client.post('/api/payment', json={'refno': 123456}, headers=headers)
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')


class ApiUserPayVerifyTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        payment = Payment(
            payment_id=1,
            payment_transNo=123456,
            payment_amount=1000,
            payment_desiid=designer.desi_id,
            payment_status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        # Simulate session refno
        with self.client.session_transaction() as sess:
            sess['refno'] = 123456

    def test_payverify_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'status': 'success', 'amount': 100000, 'ip_address': '127.0.0.1'}
        }

        with patch('requests.get', return_value=mock_response):
            response = self.client.get('/api/user/payverify/?reference=123456', follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            # data = response.get_json()
            # self.assertIn('message', data)
            # self.assertEqual(data['message'], 'Payment successful')
            # self.assertEqual(data['status'], 'paid')
            # self.assertEqual(data['amount'], 100000)
            # self.assertEqual(data['ip'], '127.0.0.1')
            location = response.headers['Location']
            self.assertTrue(location.startswith('http://localhost/api/activate?jwt='))

    def test_payverify_missing_reference(self):
        response = self.client.get('/api/user/payverify/')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Reference number is missing')

    def test_payverify_payment_failed(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'status': 'failed'}
        }

        with patch('requests.get', return_value=mock_response):
            response = self.client.get('/api/user/payverify/?reference=123456')
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertIn('message', data)
            self.assertEqual(data['message'], 'Payment failed')
            self.assertEqual(data['status'], 'failed')

    def test_payverify_payment_gateway_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('requests.get', return_value=mock_response):
            response = self.client.get('/api/user/payverify/?reference=123456')
            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertIn('message', data)
            self.assertEqual(data['message'], 'Error verifying payment')


""" premium Plan Activation """
class ApiActivateTestCase(BaseApiTestCase):

    def setUp(self):
        super().setUp()
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True

        self.client = self.app.test_client()

        # Create designer
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()

        # Create subscription
        sub = Subscription(
            sub_id=1,
            sub_desiid=designer.desi_id,
            sub_plan='3000',
            sub_ref=123456,
            sub_status='deactive'
        )
        db.session.add(sub)
        db.session.commit()

        # Create payment
        payment = Payment(
            payment_id=1,
            payment_desiid=designer.desi_id,
            payment_transNo=123456,
            payment_amount=0,
            payment_status="pending",
            desipaymentobj=designer,
            subpaymentobj=sub
        )
        db.session.add(payment)
        db.session.commit()

        self.designer = designer
        self.sub = sub

    # --------- HELPERS ---------

    def make_tokens(self, ref='123456', user_identity='designer:1'):
        payment_token = create_access_token(identity=str(ref), expires_delta=timedelta(minutes=5))
        user_token = create_access_token(identity=user_identity)
        headers = {'Authorization': f'Bearer {user_token}'}
        return payment_token, headers

    def call_activate(self, ref='123456', user_identity='designer:1'):
        payment_token, headers = self.make_tokens(ref, user_identity)
        return self.client.get(f'/api/activate?jwt={payment_token}', headers=headers)

    # --------- TESTS ---------

    def test_activate_success(self):
        response = self.call_activate()
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data['message'], 'Activation successful')
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['plan'], '3000')

    def test_activate_invalid_plan(self):
        self.sub.sub_plan = 'invalidplan'
        db.session.commit()

        response = self.call_activate()
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertEqual(data['message'], 'Invalid subscription plan')

    def test_activate_subscription_not_found(self):
        response = self.call_activate(ref='999999')
        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertEqual(data['message'], 'Subscription not found')

    def test_activate_wrong_user_type(self):
        response = self.call_activate(user_identity='customer:1')
        self.assertEqual(response.status_code, 401)

        data = response.get_json()
        self.assertEqual(data['message'], 'Unauthorized access')

    def test_activate_missing_both_tokens(self):
        response = self.client.get('/api/activate')
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn('message', data)

    def test_activate_missing_payment_token(self):
        user_token = create_access_token(identity='designer:1')
        headers = {'Authorization': f'Bearer {user_token}'}

        response = self.client.get('/api/activate', headers=headers)
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn('message', data)

    def test_activate_missing_user_token(self):
        payment_token = create_access_token(identity='123456')

        response = self.client.get(f'/api/activate?jwt={payment_token}')
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn('message', data)



""" Free Plan Activation (GET) """
class ApiFreeActivateTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        designer = Designer(
            desi_id=1,
            desi_email='testdesigner@gmail.com',
            desi_businessName='TestDesigner',
            desi_pass=generate_password_hash('password123'),
            desi_fname='Test',
            desi_lname='Designer',
            desi_phone='08000000000',
            desi_address='123 Test St',
            desi_gender='male',
            desi_status='actived'
        )
        db.session.add(designer)
        db.session.commit()
        sub = Subscription(
            sub_id=1,
            sub_desiid=designer.desi_id,
            sub_plan='free',
            sub_ref=123456,
            sub_status='active'
        )
        db.session.add(sub)
        db.session.commit()

        payment = Payment(
            payment_id=2,
            payment_desiid=designer.desi_id,
            payment_transNo=654321,
            payment_amount=0,
            payment_status="pending"
        )
        db.session.add(payment)
        db.session.commit()

        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}
        # Simulate session refno
        with self.client.session_transaction() as sess:
            sess['refno'] = 123456

    def test_free_activate_success(self):
        response = self.client.get('/api/free/activate', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Activation successful')
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['plan'], 'free')

    def test_free_activate_no_token(self):
        response = self.client.get('/api/free/activate')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('msg', data)

    def test_free_activate_wrong_user_type(self):
        # Token with a customer identity
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.get('/api/free/activate', headers=headers)
        
        # Route returns 403 if user is not a designer
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')

    def test_free_activate_missing_refno(self):
        # Remove refno from session
        with self.client.session_transaction() as sess:
            sess.pop('refno', None)
        
        # Make sure we use a valid designer token
        token = create_access_token(identity='designer:1')
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.get('/api/free/activate', headers=headers)
        
        # Route will return 400 if refno is missing
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Reference number not found in session')

    def test_free_activate_subscription_not_found(self):
        # Set refno to a non-existent one
        with self.client.session_transaction() as sess:
            sess['refno'] = 999999
        
        # Use valid designer token
        token = create_access_token(identity='designer:1')
        headers = {'Authorization': f'Bearer {token}'}

        response = self.client.get('/api/free/activate', headers=headers)
        
        # Route will return 404 if subscription not found
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Subscription not found')

    def test_free_activate_invalid_plan(self):
        # Set plan to an invalid value
        sub = Subscription.query.filter_by(sub_ref=123456).first()
        sub.sub_plan = 'invalidplan'
        db.session.commit()
        response = self.client.get('/api/free/activate', headers=self.headers)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invalid subscription plan')


# if __name__ == '__main__':
#     unittest.main()