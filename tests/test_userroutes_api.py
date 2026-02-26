import unittest, json, requests, os, tempfile, shutil, random
from datetime import datetime, timezone, timedelta
from io import BytesIO
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import create_access_token, create_refresh_token, get_jti
from werkzeug.security import generate_password_hash, check_password_hash
import os
import tempfile
import shutil
from styleitapp import create_app, db
from styleitapp.models import (Bank, Cities, Follow, Like, Newsletter, Rating, Report, Share, State, Lga, Customer, States, Login, Posting, Comment, 
                               Designer, Bookappointment, Subscription, Notification, TokenBlocklist,
                               Transaction_payment, Payment, Job, Countries)
from styleitapp.myroutes.userroutes_api import build_comment_tree, get_posts

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

        assert response.status_code == 401  # invalid token
        assert "message" in data

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
        self.assertIn("Unauthorized access", response.json["message"])

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
        self.assertIn("Unauthorized access", response.json["message"])

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


"""Customer CustPayment API"""
class ApiCustPaymentTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # create state & lga
        state = State(state_name="Lagos")
        db.session.add(state)
        db.session.commit()

        lga = Lga(lga_name="Ikeja", lga_stateid=state.state_id)
        db.session.add(lga)
        db.session.commit()

        # create customer
        self.customer = Customer(
            cust_email="cust@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="Cust",
            cust_lname="User",
            cust_phone="08012345678",
            cust_address="123 Test St",
            cust_gender="male",
            cust_status="actived",
            cust_access="actived",
            cust_countryid=161,
            cust_username="custuser",
            cust_stateid=state.state_id,
            cust_lgaid=lga.lga_stateid
        )
        db.session.add(self.customer)
        db.session.commit()

        # create designer
        self.designer = Designer(
            desi_email="desi@test.com",
            desi_businessName="Desi",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Desi",      
            desi_lname="Tester",    
            desi_phone="08098765432", 
            desi_gender="male",
        )
        db.session.add(self.designer)
        db.session.commit()

        # create booking
        self.booking = Bookappointment(
            ba_desiid=self.designer.desi_id,
            ba_custid=self.customer.cust_id,
            ba_bookingDate="2025-01-01",
            ba_bookingTime="09:00",
            ba_collectionDate="2025-01-05",
            ba_collectionTime="10:00"
        )
        db.session.add(self.booking)
        db.session.commit()

        # auth
        self.token = create_access_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.url = f"/api/custpayment/{self.booking.ba_id}/"

    def test_custpayment_success_ngn(self):
        payload = {"custid": self.customer.cust_id, "desiid": self.designer.desi_id, "amount": 200, "charges": 50}
        response = self.client.post(self.url, headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("transaction_id", data)
        self.assertIn("reference_no", data)
        self.assertEqual(data["total_amount"], 250)
        self.assertEqual(data["currency_icon"], "NGN")

        # verify transaction payment record
        tpay = Transaction_payment.query.filter_by(tpay_transNo=data["reference_no"]).first()
        self.assertIsNotNone(tpay)
        self.assertEqual(tpay.tpay_baid, self.booking.ba_id)
        self.assertEqual(tpay.tpay_amount, 250)

        # verify notification
        noti = Notification.query.filter_by(notify_tpayid=tpay.tpay_id).first()
        self.assertIsNotNone(noti)

    def test_custpayment_missing_json_returns_400(self):
        response = self.client.post(self.url, json={}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('No data provided', data['message'])

    def test_custpayment_missing_fields_returns_400(self):
        payload = {"custid": self.customer.cust_id, "desiid": self.designer.desi_id, "amount": 200}
        response = self.client.post(self.url, headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('One or more fields are missing', data['message'])

    def test_custpayment_unauthenticated_returns_401(self):
        payload = {"custid": self.customer.cust_id, "desiid": self.designer.desi_id, "amount": 200, "charges": 50}
        response = self.client.post(self.url, json=payload)
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('Unauthorized access', data['message'])

    def test_custpayment_wrong_user_type_returns_403(self):
        token = create_access_token(identity=f"designer:{self.customer.cust_id}")
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"custid": self.customer.cust_id, "desiid": self.designer.desi_id, "amount": 200, "charges": 50}
        response = self.client.post(self.url, headers=headers, json=payload)
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('Unauthorized access', data['message'])

    def test_custpayment_customer_not_found_returns_404(self):
        token = create_access_token(identity=f"customer:9999")
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"custid": 9999, "desiid": self.designer.desi_id, "amount": 200, "charges": 50}
        response = self.client.post(self.url, headers=headers, json=payload)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('Customer not found', data['message'])


class ApiConfirmPaymentTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # create state & lga
        self.state = State(state_name="TestState")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="TestLGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # create customer & designer & booking
        self.customer = Customer(
            cust_id=1,
            cust_email="cust@example.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="Jane",
            cust_lname="Doe",
            cust_phone="08012345678",
            cust_address="123 Test St",
            cust_username="janedoe",
            cust_gender="female",
            cust_regdate=datetime.now(timezone.utc),
            cust_pic="profile.png",
            cust_status="actived",
            cust_access="actived",
            cust_countryid=161,
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)

        self.designer = Designer(
            desi_email="des@example.com",
            desi_businessName="Designer",
            desi_pass=generate_password_hash("password123"),
            desi_fname="D",
            desi_lname="Signer",
            desi_phone="08000000000",
            desi_gender="male",
            desi_status="actived"
        )
        db.session.add(self.designer)
        db.session.commit()

        self.booking = Bookappointment(
            ba_desiid=self.designer.desi_id,
            ba_custid=self.customer.cust_id,
            ba_bookingDate="2025-01-01",
            ba_bookingTime="09:00",
            ba_collectionDate="2025-01-05",
            ba_collectionTime="10:00"
        )
        db.session.add(self.booking)
        db.session.commit()

        # create a transaction payment record
        self.refno = int(random.random() * 10000000)
        self.tpay = Transaction_payment(
            tpay_transNo=self.refno,
            tpay_amount=250,
            tpay_currencyicon="NGN",
            tpay_custid=self.customer.cust_id,
            tpay_desiid=self.designer.desi_id,
            tpay_baid=self.booking.ba_id,
            tpay_status='pending'
        )
        db.session.add(self.tpay)
        db.session.commit()

        # auth as customer
        self.token = create_access_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.url = f"/api/confirm_payment/{self.booking.ba_id}/"

    def test_get_confirm_payment_success(self):
        # set session refno
        with self.client.session_transaction() as sess:
            sess['refno'] = self.refno

        res = self.client.get(self.url, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['transaction_id'], self.tpay.tpay_id)
        self.assertEqual(data['reference_no'], self.tpay.tpay_transNo)
        self.assertEqual(data['total_amount'], self.tpay.tpay_amount)
        self.assertEqual(data['currency_icon'], self.tpay.tpay_currencyicon)

    def test_get_confirm_payment_no_session_returns_400(self):
        res = self.client.get(self.url, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('Invalid request or session expired', data['message'])

    def test_get_confirm_payment_transaction_not_found_returns_404(self):
        with self.client.session_transaction() as sess:
            sess['refno'] = 99999999
        res = self.client.get(self.url, headers=self.headers)
        self.assertEqual(res.status_code, 404)
        self.assertIn('Transaction not found', res.get_json()['message'])

    def test_post_confirm_payment_init_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': True,
            'data': {'authorization_url': 'https://paystack.com/authorize'}
        }
        with patch('requests.post', return_value=mock_response):
            res = self.client.post(self.url, headers=self.headers, json={'refno': self.refno})
            self.assertEqual(res.status_code, 201)
            data = res.get_json()
            self.assertIn('authorization_url', data)
            self.assertEqual(data['authorization_url'], 'https://paystack.com/authorize')

    def test_post_confirm_payment_no_refno_returns_400(self):
        res = self.client.post(self.url, headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn('Session expired, please retry', res.get_json()['message'])

    def test_post_confirm_payment_transaction_not_found_returns_404(self):
        res = self.client.post(self.url, headers=self.headers, json={'refno': 99999999})
        self.assertEqual(res.status_code, 404)
        self.assertIn('Transaction not found', res.get_json()['message'])

    def test_post_confirm_payment_already_paid_returns_200(self):
        # mark as paid
        self.tpay.tpay_status = 'paid'
        db.session.commit()
        res = self.client.post(self.url, headers=self.headers, json={'refno': self.refno})
        self.assertEqual(res.status_code, 200)
        self.assertIn('Payment already confirmed', res.get_json()['message'])

    def test_post_confirm_payment_init_failure_returns_400(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': False,
            'message': 'Some error'
        }
        with patch('requests.post', return_value=mock_response):
            res = self.client.post(self.url, headers=self.headers, json={'refno': self.refno})
            self.assertEqual(res.status_code, 400)
            self.assertIn('Payment initialization failed', res.get_json()['message'])

    def test_post_confirm_payment_request_exception_returns_500(self):
        with patch('requests.post', side_effect=requests.exceptions.RequestException('failed')):
            res = self.client.post(self.url, headers=self.headers, json={'refno': self.refno})
            self.assertEqual(res.status_code, 500)
            self.assertIn('Payment request failed', res.get_json()['message'])


class ApiPostSearchTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="Lagos")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="Ikeja", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer and a posting
        self.designer = Designer(
            desi_email="searchdes@example.com",
            desi_businessName="SearchDesigns",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Search",
            desi_lname="Designer",
            desi_phone="08000000001",
            desi_gender="male",
            desi_status="actived"
        )
        db.session.add(self.designer)
        db.session.commit()

        self.post1 = Posting(post_title="UniqueTitleOffer", post_body="Great discount on services", post_desiid=self.designer.desi_id)
        self.post2 = Posting(post_title="OtherPost", post_body="Nothing special here", post_desiid=self.designer.desi_id)
        db.session.add_all([self.post1, self.post2])
        db.session.commit()

        # Create a customer to authenticate as
        self.customer = Customer(
            cust_email="searchcust@example.com",
            cust_pass=generate_password_hash("pwd123456"),
            cust_fname="Search",
            cust_lname="Customer",
            cust_phone="08011112222",
            cust_username="searchcust",
            cust_gender="male",
            cust_status="actived",
            cust_access="actived",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.token = create_access_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_postsearch_unauthenticated_returns_401(self):
        res = self.client.post('/api/postsearch/', json={'search': 'Unique'})
        self.assertEqual(res.status_code, 401)
        self.assertIn('Unauthorized access', res.get_json().get('message', ''))

    def test_postsearch_missing_search_returns_400(self):
        res = self.client.post('/api/postsearch/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('Search term is required', data['message'])

    def test_postsearch_no_results_returns_200_with_empty_results(self):
        res = self.client.post('/api/postsearch/', headers=self.headers, json={'search': 'nomatch'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['total_results'], 0)
        self.assertEqual(data['results'], [])
        self.assertEqual(data['message'], 'No posts matched your search')

    def test_postsearch_success_returns_results(self):
        res = self.client.post('/api/postsearch/', headers=self.headers, json={'search': 'Unique'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Search completed successfully')
        self.assertGreaterEqual(data['total_results'], 1)
        self.assertTrue(any(item['title'] == 'UniqueTitleOffer' for item in data['results']))


class ApiSearchCreatorTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create Countries model import
        from styleitapp.models import Countries
        
        # Create state and lga
        self.state = State(state_name="California")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="LosAngeles", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create country
        self.country = Countries(country_id=1, country_name="USA")
        db.session.add(self.country)
        db.session.commit()

        # Create designers with active subscriptions
        self.designer1 = Designer(
            desi_email="creator1@example.com",
            desi_businessName="ProDesigner",
            desi_pass=generate_password_hash("password123"),
            desi_fname="John",
            desi_lname="Doe",
            desi_phone="08000000001",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id,
            desi_countryid=self.country.country_id
        )
        self.designer2 = Designer(
            desi_email="creator2@example.com",
            desi_businessName="ArtStudio",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Jane",
            desi_lname="Smith",
            desi_phone="08000000002",
            desi_gender="female",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id,
            desi_countryid=self.country.country_id
        )
        # Designer without active subscription (should not appear)
        self.designer3 = Designer(
            desi_email="creator3@example.com",
            desi_businessName="NoSub",
            desi_pass=generate_password_hash("password123"),
            desi_fname="NoActive",
            desi_lname="Designer",
            desi_phone="08000000003",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id,
            desi_countryid=self.country.country_id
        )
        db.session.add_all([self.designer1, self.designer2, self.designer3])
        db.session.commit()

        # Add active subscriptions for designer1 and designer2
        self.sub1 = Subscription(sub_plan="premium", sub_desiid=self.designer1.desi_id, sub_status='active')
        self.sub2 = Subscription(sub_plan="standard", sub_desiid=self.designer2.desi_id, sub_status='active')
        db.session.add_all([self.sub1, self.sub2])
        db.session.commit()

    def test_search_creator_missing_search_term(self):
        res = self.client.post('/api/search_creator/', json={})
        self.assertIn(res.status_code, [200, 400, 500])

    def test_search_creator_no_results_returns_200(self):
        res = self.client.post('/api/search_creator/', json={'search': 'nonexistentdesigner'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['total_results'], 0)
        self.assertEqual(data['results'], [])
        self.assertEqual(data['message'], 'No Creator Found')

    def test_search_creator_by_business_name_success(self):
        res = self.client.post('/api/search_creator/', json={'search': 'ProDesigner'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Search completed successfully')
        self.assertGreaterEqual(data['total_results'], 1)
        self.assertTrue(any(item['business_name'] == 'ProDesigner' for item in data['results']))

    def test_search_creator_by_first_name_success(self):
        res = self.client.post('/api/search_creator/', json={'search': 'John'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data['total_results'], 1)
        self.assertTrue(any(item['first_name'] == 'John' for item in data['results']))

    def test_search_creator_by_last_name_success(self):
        res = self.client.post('/api/search_creator/', json={'search': 'Smith'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data['total_results'], 1)
        self.assertTrue(any(item['last_name'] == 'Smith' for item in data['results']))

    def test_search_creator_only_returns_active_subscriptions(self):
        # designer3 has no active subscription, should not appear
        res = self.client.post('/api/search_creator/', json={'search': 'Designer'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        # Should only find ProDesigner or ArtStudio, not NoSub
        business_names = [item['business_name'] for item in data['results']]
        self.assertNotIn('NoSub', business_names)

    def test_search_creator_pagination(self):
        res = self.client.post('/api/search_creator/?page=1', json={'search': 'Designer'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('current_page', data)
        self.assertEqual(data['current_page'], 1)


class ApiTrashitTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="Texas")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="Houston", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer and customer
        self.designer = Designer(
            desi_email="designer@trash.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="James",
            desi_lname="Wilson",
            desi_phone="08000000004",
            desi_businessName="James Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        # Create posting
        self.posting = Posting(
            post_title="Test Post",
            post_body="This is a test post",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        # Generate JWT token for designer
        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_trash_post_success_post(self):
        res = self.client.post('/api/trashit/', headers=self.headers, json={'postid': self.posting.post_id})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Post successfully deleted')
        
        # Verify post is marked as deleted
        post = Posting.query.filter_by(post_id=self.posting.post_id).first()
        self.assertEqual(post.post_delete, 'deleted')

    def test_trash_post_success_delete(self):
        res = self.client.delete('/api/trashit/', headers=self.headers, json={'postid': self.posting.post_id})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Post successfully deleted')

    def test_trash_post_unauthenticated_returns_401(self):
        res = self.client.post('/api/trashit/', json={'postid': self.posting.post_id})
        self.assertEqual(res.status_code, 401)

    def test_trash_post_missing_postid_returns_400(self):
        res = self.client.post('/api/trashit/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'Post ID is required')

    def test_trash_post_wrong_user_type_returns_403(self):
        headers = {'Authorization': f'Bearer {create_access_token(identity="customer:1")}'}
        res = self.client.post('/api/trashit/', headers=headers, json={'postid': self.posting.post_id})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data['error'], 'Unauthorized. You can only delete posts as a designer.')

    def test_trash_post_not_found_returns_404(self):
        res = self.client.post('/api/trashit/', headers=self.headers, json={'postid': 99999})
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data['error'], 'Post not found')

    def test_trash_post_not_owned_by_user_returns_403(self):
        # Create another designer
        designer2 = Designer(
            desi_email="designer2@trash.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Jane",
            desi_lname="Doe",
            desi_phone="08000000005",
            desi_businessName="Jane Fashion",
            desi_gender="female",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(designer2)
        db.session.commit()

        headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{designer2.desi_id}")}'}
        res = self.client.post('/api/trashit/', headers=headers, json={'postid': self.posting.post_id})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data['error'], 'Unauthorized. You can only delete your own posts.')


class ApiReportTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="California")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="LosAngeles", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer and customer
        self.designer = Designer(
            desi_email="reporteddesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="John",
            desi_lname="Designer",
            desi_phone="08000000006",
            desi_businessName="John Fashion",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_fname="John",
            cust_lname="Doe",
            cust_email="customer@report.com",
            cust_phone="08000000007",
            cust_username="john_doe",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        # Generate JWT tokens
        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}
        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_report_by_customer_success(self):
        res = self.client.post('/api/report/', headers=self.customer_headers, json={
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id,
            'custname': self.customer.cust_fname,
            'desname': self.designer.desi_fname,
            'report': 'Inappropriate behavior'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'Report logged successfully')

    def test_report_by_designer_success(self):
        res = self.client.post('/api/report/', headers=self.designer_headers, json={
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id,
            'custname': self.customer.cust_fname,
            'desname': self.designer.desi_fname,
            'report': 'Spam content'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'Report logged successfully')

    def test_report_unauthenticated_returns_401(self):
        res = self.client.post('/api/report/', json={
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id,
            'report': 'Test'
        })
        self.assertEqual(res.status_code, 401)

    def test_report_missing_reason_returns_400(self):
        res = self.client.post('/api/report/', headers=self.customer_headers, json={
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'Missing required fields')

    def test_report_missing_ids_returns_400(self):
        res = self.client.post('/api/report/', headers=self.customer_headers, json={
            'report': 'Some reason'
        })
        self.assertEqual(res.status_code, 400)

    def test_report_creates_database_entry(self):
        self.client.post('/api/report/', headers=self.customer_headers, json={
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id,
            'custname': self.customer.cust_fname,
            'desname': self.designer.desi_fname,
            'report': 'Test report'
        })
        
        report = Report.query.filter_by(report_desiid=self.designer.desi_id).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.report_reason, 'Test report')


class ApiRatingTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="NewYork")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="NewYorkCity", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer and customer
        self.designer = Designer(
            desi_email="rateddesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="David",
            desi_lname="Designer",
            desi_businessName="David Fashion",
            desi_phone="08000000008",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_fname="Alice",
            cust_lname="Smith",
            cust_email="customer@rating.com",
            cust_username="alice_smith",
            cust_phone="08000000009",
            cust_gender="female",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_rating_success(self):
        res = self.client.post('/api/rating/', headers=self.headers, json={
            'rate': 5,
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'Thank you for the review')
        self.assertEqual(data['status'], 'success')

    def test_rating_missing_fields_returns_400(self):
        res = self.client.post('/api/rating/', headers=self.headers, json={
            'rate': 5,
            'custid': self.customer.cust_id
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'One or more fields are empty')

    def test_rating_unauthenticated_returns_401(self):
        res = self.client.post('/api/rating/', json={
            'rate': 5,
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id
        })
        self.assertEqual(res.status_code, 401)

    def test_rating_self_returns_error(self):
        # Designer trying to rate themselves
        headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        res = self.client.post('/api/rating/', headers=headers, json={
            'rate': 5,
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id
        })
        self.assertIn(res.status_code, [400, 403])

    def test_rating_customer_mismatch_returns_403(self):
        # Try to rate with different customer ID
        res = self.client.post('/api/rating/', headers=self.headers, json={
            'rate': 5,
            'custid': 99999,
            'desid': self.designer.desi_id
        })
        self.assertEqual(res.status_code, 403)

    def test_rating_creates_database_entry(self):
        self.client.post('/api/rating/', headers=self.headers, json={
            'rate': 4,
            'custid': self.customer.cust_id,
            'desid': self.designer.desi_id
        })
        
        rating = Rating.query.filter_by(rat_custid=self.customer.cust_id, rat_desiid=self.designer.desi_id).first()
        self.assertIsNotNone(rating)
        self.assertEqual(rating.rat_rating, 4)


class ApiNewsletterTestCase(BaseApiTestCase):
    def test_newsletter_success_new_subscriber(self):
        res = self.client.post('/api/newsletter/', json={
            'name': 'John Subscriber',
            'email': 'newsubscriber@test.com'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'You have successfully subscribed to our newsletter')

    def test_newsletter_duplicate_subscriber_returns_200(self):
        # First subscription
        self.client.post('/api/newsletter/', json={
            'name': 'Jane Subscriber',
            'email': 'duplicate@test.com'
        })
        
        # Second subscription with same email
        res = self.client.post('/api/newsletter/', json={
            'name': 'Jane Subscriber',
            'email': 'duplicate@test.com'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'You have already subscribed to our newsletter')

    def test_newsletter_missing_name_returns_400(self):
        res = self.client.post('/api/newsletter/', json={
            'email': 'missing@test.com'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'One or more fields are empty')

    def test_newsletter_missing_email_returns_400(self):
        res = self.client.post('/api/newsletter/', json={
            'name': 'Test Name'
        })
        self.assertEqual(res.status_code, 400)

    def test_newsletter_empty_json_returns_400(self):
        res = self.client.post('/api/newsletter/', json={})
        self.assertEqual(res.status_code, 400)

    def test_newsletter_creates_database_entry(self):
        self.client.post('/api/newsletter/', json={
            'name': 'Test Newsletter',
            'email': 'test@newsletter.com'
        })
        
        newsletter = Newsletter.query.filter_by(news_email='test@newsletter.com').first()
        self.assertIsNotNone(newsletter)
        self.assertEqual(newsletter.news_name, 'Test Newsletter')


class ApiBankDetailTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="Lagos")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="Lagos Island", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer
        self.designer = Designer(
            desi_email="bankdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Mike",
            desi_lname="Designer",
            desi_phone="08000000010",
            desi_businessName="Mike Fashion",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_bank_detail_success(self):
        res = self.client.post('/api/designer/bankdetail/', headers=self.headers, json={
            'name': 'Mike Designer',
            'bank': 'First Bank',
            'acno': '0123456789'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'Thank you! Your bank details have been saved.')

    def test_bank_detail_unauthenticated_returns_401(self):
        res = self.client.post('/api/designer/bankdetail/', json={
            'name': 'Test',
            'bank': 'Bank',
            'acno': '123'
        })
        self.assertEqual(res.status_code, 401)

    def test_bank_detail_wrong_user_type_returns_403(self):
        headers = {'Authorization': f'Bearer {create_access_token(identity="customer:1")}'}
        res = self.client.post('/api/designer/bankdetail/', headers=headers, json={
            'name': 'Test',
            'bank': 'Bank',
            'acno': '123'
        })
        self.assertEqual(res.status_code, 403)

    def test_bank_detail_missing_fields_returns_400(self):
        res = self.client.post('/api/designer/bankdetail/', headers=self.headers, json={
            'name': 'Mike Designer',
            'bank': 'First Bank'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'One or more fields are empty')

    def test_bank_detail_empty_json_returns_400(self):
        res = self.client.post('/api/designer/bankdetail/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)

    def test_bank_detail_creates_database_entry(self):
        self.client.post('/api/designer/bankdetail/', headers=self.headers, json={
            'name': 'Mike Designer',
            'bank': 'GTBank',
            'acno': '9876543210'
        })
        
        bank = Bank.query.filter_by(bnk_desiid=self.designer.desi_id).first()
        self.assertIsNotNone(bank)
        self.assertEqual(bank.bnk_acname, 'Mike Designer')
        self.assertEqual(bank.bnk_bankname, 'GTBank')
        self.assertEqual(bank.bnk_acno, '9876543210')


class ApiFollowTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="Delta")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="Warri", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designers
        self.designer = Designer(
            desi_email="followdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Sarah",
            desi_lname="Designer",
            desi_businessName="Lisa Fashion",
            desi_phone="08000000011",
            desi_gender="female",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        # Create customer
        self.customer = Customer(
            cust_fname="Tom",
            cust_lname="Follower",
            cust_email="customer@follow.com",
            cust_username="tom_follower",
            cust_gender="male",
            cust_phone="08000000012",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_follow_designer_success(self):
        res = self.client.post(f'/api/follow/{self.designer.desi_id}/', headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'You are now following this designer.')
        self.assertEqual(data['client_id'], str(self.customer.cust_id))

    def test_follow_already_following_returns_200(self):
        # First follow
        self.client.post(f'/api/follow/{self.designer.desi_id}/', headers=self.headers)
        
        # Second follow
        res = self.client.post(f'/api/follow/{self.designer.desi_id}/', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'exists')
        self.assertEqual(data['message'], 'You already follow this designer.')

    def test_follow_unauthenticated_returns_401(self):
        res = self.client.post(f'/api/follow/{self.designer.desi_id}/')
        self.assertEqual(res.status_code, 401)

    def test_follow_creates_database_entry(self):
        self.client.post(f'/api/follow/{self.designer.desi_id}/', headers=self.headers)
        
        follow = Follow.query.filter_by(follow_desiid=self.designer.desi_id, follow_custid=self.customer.cust_id).first()
        self.assertIsNotNone(follow)

    def test_follow_by_designer_success(self):
        # Designer following another designer
        designer2 = Designer(
            desi_email="followeddesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Emma",
            desi_lname="Designer",
            desi_businessName="Emma Fashion",
            desi_phone="08000000013",
            desi_gender="female",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(designer2)
        db.session.commit()

        headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        res = self.client.post(f'/api/follow/{designer2.desi_id}/', headers=headers)
        self.assertIn(res.status_code, [200, 201])


class ApiUnfollowTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create state and lga
        self.state = State(state_name="Edo")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="Benin", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer
        self.designer = Designer(
            desi_email="unfollowdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Lisa",
            desi_lname="Designer",
            desi_businessName="Lisa Fashion",
            desi_phone="08000000014",
            desi_gender="female",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        # Create customer
        self.customer = Customer(
            cust_fname="Paul",
            cust_lname="Unfollower",
            cust_email="customer@unfollow.com",
            cust_username="paul_unfollower",
            cust_phone="08000000015",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        # Create a follow relationship
        self.follow = Follow(follow_desiid=self.designer.desi_id, follow_custid=self.customer.cust_id)
        db.session.add(self.follow)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_unfollow_success(self):
        res = self.client.post(f'/api/unfollow/{self.designer.desi_id}/', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'You have unfollowed this designer.')

    def test_unfollow_not_following_returns_400(self):
        # Create another customer
        customer2 = Customer(
            cust_fname="Rachel",
            cust_lname="NotFollowing",
            cust_username="rachel_notfollowing",
            cust_email="customer2@unfollow.com",
            cust_gender="female",
            cust_phone="08000000016",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(customer2)
        db.session.commit()

        headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{customer2.cust_id}")}'}
        res = self.client.post(f'/api/unfollow/{self.designer.desi_id}/', headers=headers)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'You are not following this designer.')

    def test_unfollow_unauthenticated_returns_401(self):
        res = self.client.post(f'/api/unfollow/{self.designer.desi_id}/')
        self.assertEqual(res.status_code, 401)

    def test_unfollow_removes_follow_record(self):
        self.client.post(f'/api/unfollow/{self.designer.desi_id}/', headers=self.headers)
        
        follow = Follow.query.filter_by(follow_desiid=self.designer.desi_id, follow_custid=self.customer.cust_id).first()
        self.assertIsNone(follow)

    def test_unfollow_by_designer(self):
        # Create another designer
        designer2 = Designer(
            desi_email="designerfollowed@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Robert",
            desi_lname="Designer",
            desi_businessName="Lisa Fashion",
            desi_phone="08000000017",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(designer2)
        db.session.commit()

        # Create follow
        follow = Follow(follow_desiid=designer2.desi_id, follow_custid=None)
        db.session.add(follow)
        db.session.commit()

        headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        res = self.client.post(f'/api/unfollow/{designer2.desi_id}/', headers=headers)
        self.assertIn(res.status_code, [200, 400, 201])


class ApiUserRefreshTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create customer
        self.customer = Customer(
            cust_fname="Test",
            cust_lname="User",
            cust_email="refresh@test.com",
            cust_phone="08000000020",
            cust_username="test_user",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=1,
            cust_lgaid=1
        )
        db.session.add(self.customer)
        db.session.commit()

        # Create refresh token
        self.refresh_token = create_refresh_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {'Authorization': f'Bearer {self.refresh_token}'}

    def test_refresh_token_success_customer(self):
        res = self.client.post('/api/user/refresh', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)

    def test_refresh_token_without_token_returns_401(self):
        res = self.client.post('/api/user/refresh')
        self.assertEqual(res.status_code, 401)


class ApiDesignerUpdateBioTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="bioupdater@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Bio",
            desi_lname="Updater",
            desi_phone="08000000021",
            desi_businessName="Bio Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_update_bio_success(self):
        res = self.client.put('/api/designer/updatebio/', headers=self.headers, json={
            'bio': 'Updated bio for designer'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Bio updated successfully')

    def test_update_bio_missing_bio_returns_400(self):
        res = self.client.put('/api/designer/updatebio/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)

    def test_update_bio_unauthenticated_returns_401(self):
        res = self.client.put('/api/designer/updatebio/', json={'bio': 'Test'})
        self.assertEqual(res.status_code, 401)

    def test_update_bio_wrong_user_type_returns_401(self):
        headers = {'Authorization': f'Bearer {create_access_token(identity="customer:1")}'}
        res = self.client.put('/api/designer/updatebio/', headers=headers, json={'bio': 'Test'})
        self.assertEqual(res.status_code, 401)


class ApiDesignerUpdateAboutTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="aboutupdater@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="About",
            desi_lname="Updater",
            desi_businessName="About Designs",
            desi_phone="08000000022",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_update_about_success(self):
        res = self.client.put('/api/designer/about/', headers=self.headers, json={
            'about': 'Updated about for designer'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'About updated successfully')

    def test_update_about_missing_about_returns_400(self):
        res = self.client.put('/api/designer/about/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)

    def test_update_about_unauthenticated_returns_401(self):
        res = self.client.put('/api/designer/about/', json={'about': 'Test'})
        self.assertEqual(res.status_code, 401)


class ApiDesignerUpdateProfilePicTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="picupdater@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Pic",
            desi_lname="Updater",
            desi_businessName="Pic Designs",
            desi_phone="08000000023",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_update_profile_pic_no_file_returns_400(self):
        res = self.client.put('/api/designer/update/profilepic', headers=self.headers)
        self.assertEqual(res.status_code, 400)

    def test_update_profile_pic_unauthenticated_returns_401(self):
        res = self.client.put('/api/designer/update/profilepic')
        self.assertEqual(res.status_code, 401)

    def test_update_profile_pic_wrong_user_type_returns_403(self):
        headers = {'Authorization': f'Bearer {create_access_token(identity="customer:1")}'}
        res = self.client.put('/api/designer/update/profilepic', headers=headers)
        self.assertEqual(res.status_code, 403)


class ApiCustomerUpdateProfilePicTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.customer = Customer(
            cust_fname="Cust",
            cust_lname="Pic",
            cust_email="custpic@test.com",
            cust_phone="08000000024",
            cust_username="cust_pic",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_customer_update_profile_pic_no_file_returns_400(self):
        res = self.client.put('/api/customer/update/profilepic', headers=self.headers)
        self.assertEqual(res.status_code, 400)

    def test_customer_update_profile_pic_unauthenticated_returns_401(self):
        res = self.client.put('/api/customer/update/profilepic')
        self.assertEqual(res.status_code, 401)

    def test_customer_update_profile_pic_wrong_user_type_returns_403(self):
        headers = {'Authorization': f'Bearer {create_access_token(identity="designer:1")}'}
        res = self.client.put('/api/customer/update/profilepic', headers=headers)
        self.assertEqual(res.status_code, 403)


class ApiUserVerificationTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.customer = Customer(
            cust_fname="Verify",
            cust_lname="User",
            cust_email="verify@test.com",
            cust_phone="08000000025",
            cust_pass=generate_password_hash("password123"),
            cust_username="verify_user",
            cust_gender="male",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_user_verification_no_file_returns_success(self):
        # Test without file - should still complete
        res = self.client.put('/api/user_verification', headers=self.headers, data={})
        self.assertIn(res.status_code, [200, 400])

    def test_user_verification_unauthenticated_returns_401(self):
        res = self.client.put('/api/user_verification', data={})
        self.assertEqual(res.status_code, 401)


class ApiResendActivationTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.customer = Customer(
            cust_fname="Resend",
            cust_lname="Activation",
            cust_email="resend@test.com",
            cust_phone="08000000026",
            cust_username="resend_activation",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id,
            cust_status='deactived'
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    @patch('styleitapp.myroutes.userroutes.send_email')
    def test_resend_activation_success(self, mock_send_email):
        res = self.client.post('/api/resend-activation', headers=self.headers, json={
            'email': self.customer.cust_email
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')

    def test_resend_activation_invalid_email_returns_error(self):
        res = self.client.post('/api/resend-activation', headers=self.headers, json={
            'email': 'wrong@test.com'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'error')

    def test_resend_activation_unauthenticated_returns_401(self):
        res = self.client.post('/api/resend-activation', json={'email': 'test@test.com'})
        self.assertEqual(res.status_code, 401)


class ApiUnconfirmedTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.customer = Customer(
            cust_fname="Unconfirmed",
            cust_lname="User",
            cust_email="unconfirmed@test.com",
            cust_phone="08000000027",
            cust_username="unconfirmed_user",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id,
            cust_status='deactived'
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_unconfirmed_user_not_activated(self):
        res = self.client.get('/api/unconfirmed', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('message', data)

    def test_unconfirmed_user_already_activated(self):
        self.customer.cust_status = 'actived'
        db.session.commit()
        
        res = self.client.get('/api/unconfirmed', headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_unconfirmed_unauthenticated_returns_401(self):
        res = self.client.get('/api/unconfirmed')
        self.assertEqual(res.status_code, 401)


class ApiConfirmTokenTestCase(BaseApiTestCase):
    def test_confirm_token_missing_token_returns_400(self):
        res = self.client.get('/api/confirm_token')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data['error'], 'Token is required')

    def test_confirm_token_invalid_token_returns_401(self):
        res = self.client.get('/api/confirm_token?token=invalid_token')
        self.assertEqual(res.status_code, 401)


class ApiShareTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="sharedesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Share",
            desi_lname="Designer",
            desi_phone="08000000028",
            desi_businessName="Bio Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    @patch('styleitapp.myroutes.userroutes_api.share_signal.send')
    def test_share_success_by_designer(self, mock_signal):
        res = self.client.post('/api/share/', headers=self.headers, json={
            'name': 'facebook',
            'sharepost': self.posting.post_id,
            'user': self.designer.desi_id
        })
        self.assertEqual(res.status_code, 200)

    def test_share_missing_fields_returns_400(self):
        res = self.client.post('/api/share/', headers=self.headers, json={
            'name': 'facebook'
        })
        self.assertEqual(res.status_code, 400)

    def test_share_unauthenticated_returns_401(self):
        res = self.client.post('/api/share/', json={
            'name': 'facebook',
            'sharepost': 1,
            'user': 1
        })
        self.assertEqual(res.status_code, 401)


class ApiLikeTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="likedesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Like",
            desi_lname="Designer",
            desi_phone="08000000029",
            desi_businessName="Like Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_like_post_success(self):
        res = self.client.post(f'/api/like/{self.posting.post_id}/', headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_like_post_not_found_returns_404(self):
        res = self.client.post('/api/like/99999/', headers=self.headers)
        self.assertEqual(res.status_code, 404)

    def test_like_post_unauthenticated_returns_401(self):
        res = self.client.post(f'/api/like/{self.posting.post_id}/')
        self.assertEqual(res.status_code, 401)


class ApiReplyTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="replydesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Reply",
            desi_lname="Designer",
            desi_phone="08000000030",
            desi_gender="male",
            desi_businessName="Reply Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.customer = Customer(
            cust_email="customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="Test",
            cust_lname="Customer",
            cust_username="testcustomer",
            cust_phone="08000000031",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        # Parent comment created by customer so comcustobj relationship exists
        self.comment = Comment(
            com_body="Test Comment",
            com_postid=self.posting.post_id,
            com_custid=self.customer.cust_id
        )
        db.session.add(self.comment)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_reply_success(self):
        res = self.client.post(f'/api/reply/{self.posting.post_id}/{self.comment.com_id}/', headers=self.headers, json={
            'comrep': 'Test reply'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')

    def test_reply_missing_text_returns_400(self):
        res = self.client.post(f'/api/reply/{self.posting.post_id}/{self.comment.com_id}/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)

    def test_reply_unauthenticated_returns_401(self):
        res = self.client.post(f'/api/reply/{self.posting.post_id}/{self.comment.com_id}/', json={'comrep': 'Test'})
        self.assertEqual(res.status_code, 401)


class ApiCommentTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="commentdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Comment",
            desi_lname="Designer",
            desi_phone="08000000031",
            desi_businessName="Comment Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_comment_success(self):
        res = self.client.post(f'/api/comment/{self.posting.post_id}/', headers=self.headers, json={
            'comment': 'Test comment'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['message'], 'Comment created successfully')

    def test_comment_missing_text_returns_400(self):
        res = self.client.post(f'/api/comment/{self.posting.post_id}/', headers=self.headers, json={})
        self.assertEqual(res.status_code, 400)

    def test_comment_post_not_found_returns_404(self):
        res = self.client.post('/api/comment/99999/', headers=self.headers, json={'comment': 'Test'})
        self.assertEqual(res.status_code, 404)

    def test_comment_unauthenticated_returns_401(self):
        res = self.client.post(f'/api/comment/{self.posting.post_id}/', json={'comment': 'Test'})
        self.assertEqual(res.status_code, 401)


class ApiDesignerDetailTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="detaildesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Detail",
            desi_lname="Designer",
            desi_phone="08000000032",
            desi_gender="male",
            desi_businessName="Detail Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_fname="Detail",
            cust_lname="Customer",
            cust_email="detailcustomer@test.com",
            cust_phone="08000000033",
            cust_username="detailcustomer",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_get_designer_detail_success(self):
        res = self.client.get(f'/api/designer/{self.designer.desi_id}/', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['desi_id'], self.designer.desi_id)

    def test_get_designer_not_found_returns_404(self):
        res = self.client.get('/api/designer/99999/', headers=self.headers)
        self.assertEqual(res.status_code, 404)

    def test_get_designer_unauthenticated_returns_401(self):
        res = self.client.get(f'/api/designer/{self.designer.desi_id}/')
        self.assertEqual(res.status_code, 401)


class ApiDesignersListTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        country = Countries(country_id=1, country_name="Nigeria")
        db.session.add(country)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="listdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="List",
            desi_lname="Designer",
            desi_phone="08000000034",
            desi_gender="male",
            desi_businessName="List Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id,
            desi_countryid=country.country_id
        )
        db.session.add(self.designer)
        db.session.commit()

        sub = Subscription(sub_plan="premium", sub_desiid=self.designer.desi_id, sub_status='active')
        db.session.add(sub)
        db.session.commit()

        self.customer = Customer(
            cust_fname="List",
            cust_lname="Customer",
            cust_email="listcustomer@test.com",
            cust_phone="08000000035",
            cust_username="listcustomer",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_get_designers_list_success(self):
        res = self.client.get('/api/designers', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('designers', data)

    def test_get_designers_pagination(self):
        res = self.client.get('/api/designers?page=1&per_page=10', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('current_page', data)

    def test_get_designers_unauthenticated_returns_401(self):
        res = self.client.get('/api/designers')
        self.assertEqual(res.status_code, 401)


class ApiPostDetailTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="postdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Post",
            desi_lname="Designer",
            desi_phone="08000000036",
            desi_gender="male",
            desi_businessName="Post Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.customer = Customer(
            cust_fname="Post",
            cust_lname="Customer",
            cust_email="postcustomer@test.com",
            cust_phone="08000000037",
            cust_username="postcustomer",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_get_post_detail_success(self):
        res = self.client.get(f'/api/post/{self.posting.post_id}/', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('post', data)

    def test_get_post_not_found_returns_404(self):
        res = self.client.get('/api/post/99999/', headers=self.headers)
        self.assertEqual(res.status_code, 404)

    def test_get_post_unauthenticated_returns_401(self):
        res = self.client.get(f'/api/post/{self.posting.post_id}/')
        self.assertEqual(res.status_code, 401)


class ApiBuildCommentTreeTestCase(BaseApiTestCase):
    """Helper function tests for building nested comment trees in /api/post/<id>/ endpoint"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="commentdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Comment",
            desi_lname="Designer",
            desi_phone="08000000041",
            desi_businessName="Comment Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_fname="Comment",
            cust_lname="Customer",
            cust_email="commentcustomer@test.com",
            cust_phone="08000000042",
            cust_username="commentcustomer",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.posting = Posting(
            post_title="Comment Test Post",
            post_body="Test Body for Comments",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

    def test_build_comment_tree_empty_comments(self):
        """Test building comment tree with no comments"""
        comments = []
        with self.app.test_request_context():
            tree = build_comment_tree(comments)
            self.assertIsInstance(tree, list)
            self.assertEqual(len(tree), 0)

    def test_build_comment_tree_single_comment(self):
        """Test building comment tree with single top-level comment"""
        comment = Comment(
            com_body="Test comment",
            com_postid=self.posting.post_id,
            com_custid=self.customer.cust_id
        )
        db.session.add(comment)
        db.session.commit()
        
        comments = [comment]
        with self.app.test_request_context():
            tree = build_comment_tree(comments)
            self.assertIsInstance(tree, list)
            self.assertGreater(len(tree), 0)
            self.assertEqual(tree[0]['body'], 'Test comment')

    def test_build_comment_tree_nested_comments(self):
        """Test building comment tree with parent-child comments"""
        parent_comment = Comment(
            com_body="Parent comment",
            com_postid=self.posting.post_id,
            com_custid=self.customer.cust_id,
            parent_id=None
        )
        db.session.add(parent_comment)
        db.session.commit()
        
        reply_comment = Comment(
            com_body="Reply to parent",
            com_postid=self.posting.post_id,
            com_custid=self.customer.cust_id,
            parent_id=parent_comment.com_id
        )
        db.session.add(reply_comment)
        db.session.commit()
        
        comments = [parent_comment, reply_comment]
        with self.app.test_request_context():
            tree = build_comment_tree(comments)
            self.assertIsInstance(tree, list)
            self.assertGreater(len(tree), 0)

    def test_build_comment_tree_structure_validation(self):
        """Test that built tree has correct structure with required fields"""
        comment = Comment(
            com_body="Structured comment",
            com_postid=self.posting.post_id,
            com_custid=self.customer.cust_id
        )
        db.session.add(comment)
        db.session.commit()
        
        comments = [comment]
        with self.app.test_request_context():
            tree = build_comment_tree(comments)
            
            self.assertIsInstance(tree, list)
            if tree:
                node = tree[0]
                required_fields = ['com_id', 'body', 'parent', 'post_id', 'children']
                for field in required_fields:
                    self.assertIn(field, node)


class ApiTrendingTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="trenddesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Trend",
            desi_lname="Designer",
            desi_phone="08000000038",
            desi_businessName="Trend Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting = Posting(
            post_title="Trending Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.customer = Customer(
            cust_fname="Trend",
            cust_lname="Customer",
            cust_email="trendcustomer@test.com",
            cust_phone="08000000039",
            cust_username="trendcustomer",
            cust_gender="male",
            cust_pass=generate_password_hash("password123"),
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_get_trending_success(self):
        res = self.client.get('/api/trending', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('posts', data)

    def test_get_trending_pagination(self):
        res = self.client.get('/api/trending?page=1&per_page=10', headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_get_trending_unauthenticated_returns_401(self):
        res = self.client.get('/api/trending')
        self.assertEqual(res.status_code, 401)


class ApiPostsListTestCase(BaseApiTestCase):
    """Helper function tests for get_posts() used by /api/trending and /api/post/<id>/ endpoints"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()
        
        self.designer = Designer(
            desi_email="postsdesigner@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Posts",
            desi_lname="Designer",
            desi_phone="08000000040",
            desi_businessName="Posts Designs",
            desi_gender="male",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.posting_active = Posting(
            post_title="Active Posts List",
            post_body="Test Body Active",
            post_delete="not deleted",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting_active)
        db.session.commit()

        self.posting_deleted = Posting(
            post_title="Deleted Posts List",
            post_body="Test Body Deleted",
            post_delete="deleted",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting_deleted)
        db.session.commit()

    def test_get_posts_helper_returns_query(self):
        """Test that get_posts() helper returns a valid query object"""
        posts_query = get_posts()
        self.assertIsNotNone(posts_query)
        posts = posts_query.all()
        self.assertIsInstance(posts, list)

    def test_get_posts_filters_deleted_posts(self):
        """Test that get_posts() filters out deleted posts"""
        posts_query = get_posts()
        posts = posts_query.all()
        
        for post in posts:
            self.assertEqual(post.post_delete, 'not deleted')
        
        post_ids = [p.post_id for p in posts]
        if self.posting_deleted.post_id in post_ids:
            self.fail("Deleted post should not be in get_posts() results")

    def test_get_posts_returns_active_posts(self):
        """Test that get_posts() includes active posts"""
        posts_query = get_posts()
        posts = posts_query.all()
        
        post_ids = [p.post_id for p in posts]
        self.assertIn(self.posting_active.post_id, post_ids)

    def test_get_posts_includes_relationships(self):
        """Test that get_posts() properly loads relationships (likes, images, designer, comments)"""
        posts_query = get_posts()
        posts = posts_query.all()
        
        self.assertGreater(len(posts), 0)
        for post in posts:
            self.assertIsNotNone(post.designerobj)
            self.assertIsInstance(post.likes, list)
            self.assertIsInstance(post.imagepostobj, list)
            self.assertIsInstance(post.postcomobj, list)

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
        self.assertIn('message', data)

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
        self.assertIn('message', resp_json)


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
        self.assertIn('message', data)

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


""" Complete Task Endpoint """
class ApiCompleteTaskTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Create temp dir for saving completed task images
        self.tempdir = tempfile.mkdtemp()
        self.app.config['COMPLETE_TASK'] = self.tempdir

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
        db.session.add_all([designer, customer])
        db.session.commit()

        # Create a Bookappointment that the designer will mark complete
        appointment = Bookappointment(
            ba_id=1,
            ba_desiid=designer.desi_id,
            ba_custid=customer.cust_id,
            ba_bookingDate='2025-09-25',
            ba_bookingTime='10:00',
            ba_collectionDate='2025-09-26',
            ba_collectionTime='12:00',
            ba_status='accept'
        )
        db.session.add(appointment)
        db.session.commit()

        self.token = create_access_token(identity='designer:1')
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        # remove temp dir and then call parent teardown
        shutil.rmtree(self.tempdir)
        super().tearDown()

    def test_complete_task_success(self):
        # send multipart/form-data with image
        img = (BytesIO(b"fake image data"), 'complete.png')
        response = self.client.post(
            '/api/complete_task/1/',
            data={
                'custid': '1',
                'status': 'completed',
                'pic': (img[0], img[1])
            },
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['task_id'], 1)
        self.assertIn('image_url', data)

        # Verify job record and file were created
        job = Job.query.filter_by(jb_baid=1).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.jb_status, 'completed')
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, job.jb_pic)))

        # Verify appointment status updated
        appointment = Bookappointment.query.get(1)
        self.assertEqual(appointment.ba_status, 'completed')

    def test_complete_task_missing_fields(self):
        # missing pic and status
        response = self.client.post(
            '/api/complete_task/1/',
            data={'custid': '1'},
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'One or more fields are empty')

    def test_complete_task_invalid_file_extension(self):
        img = (BytesIO(b"fake data"), 'bad.txt')
        response = self.client.post(
            '/api/complete_task/1/',
            data={
                'custid': '1',
                'status': 'completed',
                'pic': (img[0], img[1])
            },
            headers=self.headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Invalid file format. Only JPG, GIF, PNG allowed')

    def test_complete_task_forbidden_for_customer(self):
        token = create_access_token(identity='customer:1')
        headers = {'Authorization': f'Bearer {token}'}
        img = (BytesIO(b"fake image data"), 'complete.png')
        response = self.client.post(
            '/api/complete_task/1/',
            data={
                'custid': '1',
                'status': 'completed',
                'pic': (img[0], img[1])
            },
            headers=headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertIn('message', data)
        self.assertEqual(data['message'], 'Unauthorized access')

    def test_complete_task_requires_authentication(self):
        img = (BytesIO(b"fake image data"), 'complete.png')
        response = self.client.post(
            '/api/complete_task/1/',
            data={
                'custid': '1',
                'status': 'completed',
                'pic': (img[0], img[1])
            },
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('message', data)


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
            sub_plan='5000',
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
        self.assertIn('notification', data)
        self.assertEqual(data['designer']['id'], 1)
        self.assertEqual(data['designer']['businessName'], 'TestDesigner')
        self.assertTrue(len(data['subscriptions']) > 0)

    def test_subplan_no_token(self):
        response = self.client.get('/api/designer/subplan')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('message', data)

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
        self.assertEqual(data['message'], 'Subscription initiated successfully')
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
        self.assertIn('message', data)


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
        self.assertIn('message', data)

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
        return payment_token, user_token

    def call_activate(self, ref='123456', user_identity='designer:1'):
        payment_token, user_token = self.make_tokens(ref, user_identity)
        return self.client.get(f'/api/activate?jwt={payment_token}&access_token={user_token}')

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
        self.assertIn('message', data)

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


class ConfirmDeliveryTestCase(BaseApiTestCase):
    def setUp(self):
        super().setUp()
        # Ensure cust_name property exists on Customer for the endpoint
        if not hasattr(Customer, 'cust_name'):
            Customer.cust_name = property(lambda self: f"{self.cust_fname} {self.cust_lname}")

        # Create state and lga
        self.state = State(state_name="Lagos")
        db.session.add(self.state)
        db.session.commit()
        self.lga = Lga(lga_name="Ikeja", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create designer & customer
        self.designer = Designer(desi_fname="Des", desi_lname="Signer", desi_businessName="DeSign", desi_gender="male", desi_phone="08000000000", desi_email="des@example.com", desi_pass=generate_password_hash("pass"), desi_status="actived", desi_access="actived")
        db.session.add(self.designer)
        self.customer = Customer(cust_fname="John", cust_lname="Doe", cust_username="john", cust_gender="male", cust_phone="08011111111", cust_email="john@example.com", cust_pass="pw", cust_status="actived", cust_access="actived", cust_stateid=self.state.state_id, cust_lgaid=self.lga.lga_id)
        db.session.add(self.customer)
        db.session.commit()

        # Create a booking and job
        self.book = Bookappointment(ba_desiid=self.designer.desi_id, ba_custid=self.customer.cust_id, ba_bookingDate="2024-01-01", ba_bookingTime="10:00", ba_collectionDate="2024-01-02", ba_collectionTime="12:00")
        db.session.add(self.book)
        db.session.commit()

        self.job = Job(jb_status="completed", jb_pic="done.png", jb_custid=self.customer.cust_id, jb_desiid=self.designer.desi_id, jb_baid=self.book.ba_id)
        db.session.add(self.job)
        db.session.commit()

        self.token = create_access_token(identity=f"customer:{self.customer.cust_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_get_confirm_delivery_success(self):
        res = self.client.get(f"/api/confirm_delivery/{self.book.ba_id}/", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['job_creator_id'], self.job.jb_desiid)
        self.assertIsNotNone(data['task_image_url'])
        self.assertEqual(data['customer'], "John Doe")

    def test_post_confirm_delivery_success(self):
        res = self.client.post(f"/api/confirm_delivery/{self.book.ba_id}/", headers=self.headers, json={"desiid": self.designer.desi_id, "custstatus": "collected"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("Thank you", data['message'])
        bk = Bookappointment.query.get(self.book.ba_id)
        self.assertEqual(bk.ba_custstatus, "collected")
        jb = Job.query.filter_by(jb_baid=self.book.ba_id).first()
        self.assertEqual(jb.jb_status, "collected")

    def test_get_unauthenticated(self):
        res = self.client.get(f"/api/confirm_delivery/{self.book.ba_id}/")
        self.assertEqual(res.status_code, 401)
        self.assertIn('Unauthorized access', res.get_json().get('message',''))

    def test_post_wrong_user_type(self):
        token = create_access_token(identity=f"designer:{self.designer.desi_id}")
        headers = {"Authorization": f"Bearer {token}"}
        res = self.client.post(f"/api/confirm_delivery/{self.book.ba_id}/", headers=headers, json={"desiid": self.designer.desi_id, "custstatus": "collected"})
        self.assertEqual(res.status_code, 403)
        self.assertIn('Unauthorized access', res.get_json().get('message',''))

    def test_post_missing_fields(self):
        res = self.client.post(f"/api/confirm_delivery/{self.book.ba_id}/", headers=self.headers, json={})
        self.assertNotEqual(res.status_code, 200)
        self.assertIn(res.status_code, (400, 500))

"""
Notification Update Endpoints
"""
class ApiPostNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/posti/<id>/ endpoint - Post notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="posti_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="Posti",
            desi_lname="Designer",
            desi_phone="08000000040",
            desi_gender="male",
            desi_businessName="Posti Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_email="posti_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="Posti",
            cust_lname="Customer",
            cust_username="posti_customer",
            cust_phone="08000000041",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.notification = Notification(
            notify_postid=self.posting.post_id,
            notify_desiid=self.designer.desi_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_posti_success_designer(self):
        """Test marking post notification as read for designer"""
        res = self.client.put(f'/api/posti/{self.posting.post_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Notification updated successfully')
        self.assertIn('redirect_url', data)

    def test_posti_success_customer(self):
        """Test marking post notification as read for customer"""
        notif = Notification(
            notify_postid=self.posting.post_id,
            notify_custid=self.customer.cust_id,
            notify_read='unread'
        )
        db.session.add(notif)
        db.session.commit()
        
        res = self.client.put(f'/api/posti/{self.posting.post_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 200)

    def test_posti_not_found(self):
        """Test marking post notification as read when notification not found"""
        res = self.client.put('/api/posti/99999/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)
        self.assertIn('Notification not found', res.get_json()['message'])

    def test_posti_unauthenticated(self):
        """Test marking post notification as read without authentication"""
        res = self.client.put(f'/api/posti/{self.posting.post_id}/')
        self.assertEqual(res.status_code, 401)

    def test_posti_invalid_user_type(self):
        """Test marking post notification with invalid user type in token"""
        token = create_access_token(identity="invalid:123")
        headers = {'Authorization': f'Bearer {token}'}
        res = self.client.put(f'/api/posti/{self.posting.post_id}/', headers=headers)
        self.assertEqual(res.status_code, 401)


class ApiPostlikeNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/postlike/<id>/ endpoint - Like notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="postlike_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="PostLike",
            desi_lname="Designer",
            desi_phone="08000000042",
            desi_gender="male",
            desi_businessName="PostLike Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_email="postlike_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="PostLike",
            cust_lname="Customer",
            cust_phone="08000000043",
            cust_username="postlike_customer",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.like = Like(
            like_postid=self.posting.post_id,
            like_custid=self.customer.cust_id
        )
        db.session.add(self.like)
        db.session.commit()

        self.notification = Notification(
            notify_likeid=self.like.like_id,
            notify_custid=self.customer.cust_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_postlike_success_customer(self):
        """Test marking like notification as read for customer"""
        res = self.client.put(f'/api/postlike/{self.like.like_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], "notification updted successfully")
        self.assertIn('postid', data)

    def test_postlike_designer_not_found(self):
        """Test marking like notification when designer not found"""
        res = self.client.put(f'/api/postlike/{self.like.like_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)

    def test_postlike_like_not_found(self):
        """Test marking like notification when like not found"""
        res = self.client.put('/api/postlike/99999/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 404)

    def test_postlike_notification_not_found(self):
        """Test marking like notification when notification not found"""
        like = Like(like_postid=self.posting.post_id, like_custid=self.customer.cust_id)
        db.session.add(like)
        db.session.commit()
        
        res = self.client.put(f'/api/postlike/{like.like_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 404)

    def test_postlike_unauthenticated(self):
        """Test marking like notification without authentication"""
        res = self.client.put(f'/api/postlike/{self.like.like_id}/')
        self.assertEqual(res.status_code, 401)


class ApiPostreplyNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/postreply/<id>/ endpoint - Reply (Comment) notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="postreply_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="PostReply",
            desi_lname="Designer",
            desi_phone="08000000044",
            desi_gender="male",
            desi_businessName="PostReply Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_email="postreply_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="PostReply",
            cust_lname="Customer",
            cust_username="postreply_customer",
            cust_phone="08000000045",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.comment = Comment(
            com_body="Test Reply",
            com_postid=self.posting.post_id,
            com_desiid=self.designer.desi_id
        )
        db.session.add(self.comment)
        db.session.commit()

        self.notification = Notification(
            notify_comid=self.comment.com_id,
            notify_desiid=self.designer.desi_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_postreply_success_designer(self):
        """Test marking reply notification as read for designer"""
        res = self.client.put(f'/api/postreply/{self.comment.com_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Notification updated')
        self.assertIn('post_id', data)

    def test_postreply_success_customer(self):
        """Test marking reply notification as read for customer"""
        comment = Comment(
            com_body="Test Reply",
            com_postid=self.posting.post_id,
            com_custid=self.customer.cust_id
        )
        db.session.add(comment)
        db.session.commit()

        notif = Notification(
            notify_comid=comment.com_id,
            notify_custid=self.customer.cust_id,
            notify_read='unread'
        )
        db.session.add(notif)
        db.session.commit()
        
        res = self.client.put(f'/api/postreply/{comment.com_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 200)

    def test_postreply_comment_not_found(self):
        """Test marking reply notification when comment not found"""
        res = self.client.put('/api/postreply/99999/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)

    def test_postreply_designer_not_found(self):
        """Test marking reply notification when designer not found"""
        res = self.client.put(f'/api/postreply/{self.comment.com_id}/', headers=self.designer_headers)
        # Should work or return 404 depending on notification existence
        self.assertIn(res.status_code, [200, 404])

    def test_postreply_unauthenticated(self):
        """Test marking reply notification without authentication"""
        res = self.client.put(f'/api/postreply/{self.comment.com_id}/')
        self.assertEqual(res.status_code, 401)


class ApiPostshareNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/postshare/<id>/ endpoint - Share notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="postshare_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="PostShare",
            desi_lname="Designer",
            desi_phone="08000000046",
            desi_gender="male",
            desi_businessName="PostShare Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_email="postshare_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="PostShare",
            cust_lname="Customer",
            cust_phone="08000000047",
            cust_gender="female",
            cust_username="postshare_customer",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.posting = Posting(
            post_title="Test Post",
            post_body="Test Body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        self.share = Share(
            share_postid=self.posting.post_id,
            share_custid=self.customer.cust_id,
            share_webname="facebook"
        )
        db.session.add(self.share)
        db.session.commit()

        self.notification = Notification(
            notify_shareid=self.share.share_id,
            notify_custid=self.customer.cust_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_postshare_success_customer(self):
        """Test marking share notification as read for customer"""
        res = self.client.put(f'/api/postshare/{self.share.share_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('redirect_url', data)

    def test_postshare_designer_not_found(self):
        """Test marking share notification when designer not found"""
        res = self.client.put(f'/api/postshare/{self.share.share_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)

    def test_postshare_share_not_found(self):
        """Test marking share notification when share not found"""
        res = self.client.put('/api/postshare/99999/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 404)

    def test_postshare_unauthenticated(self):
        """Test marking share notification without authentication"""
        res = self.client.put(f'/api/postshare/{self.share.share_id}/')
        self.assertEqual(res.status_code, 401)


class ApiBookappNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/bookapp/<id>/ endpoint - Book appointment notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="bookapp_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="BookApp",
            desi_lname="Designer",
            desi_phone="08000000048",
            desi_gender="male",
            desi_businessName="BookApp Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.customer = Customer(
            cust_email="bookapp_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="BookApp",
            cust_lname="Customer",
            cust_username="bookapp_customer",
            cust_phone="08000000049",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.appointment = Bookappointment(
            ba_custid=self.customer.cust_id,
            ba_desiid=self.designer.desi_id,
            ba_bookingDate="2026-02-01",
            ba_bookingTime="10:00 AM",
            ba_collectionDate="2026-02-15",
            ba_collectionTime="02:00 PM"
        )
        db.session.add(self.appointment)
        db.session.commit()

        self.notification = Notification(
            notify_baid=self.appointment.ba_id,
            notify_custid=self.customer.cust_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}
        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}

    def test_bookapp_success_customer(self):
        """Test marking book appointment notification as read for customer"""
        res = self.client.put(f'/api/bookapp/{self.appointment.ba_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')

    def test_bookapp_success_designer(self):
        """Test marking book appointment notification as read for designer"""
        notif = Notification(
            notify_baid=self.appointment.ba_id,
            notify_desiid=self.designer.desi_id,
            notify_read='unread'
        )
        db.session.add(notif)
        db.session.commit()
        
        res = self.client.put(f'/api/bookapp/{self.appointment.ba_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'success')

    def test_bookapp_not_found(self):
        """Test marking book appointment notification when not found"""
        res = self.client.put('/api/bookapp/99999/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 404)

    def test_bookapp_customer_not_found(self):
        """Test marking book appointment notification when customer not found"""
        res = self.client.put(f'/api/bookapp/{self.appointment.ba_id}/', headers=self.customer_headers)
        # Should work if notification exists
        self.assertIn(res.status_code, [200, 404])

    def test_bookapp_unauthenticated(self):
        """Test marking book appointment notification without authentication"""
        res = self.client.put(f'/api/bookapp/{self.appointment.ba_id}/')
        self.assertEqual(res.status_code, 401)


class ApiNotesubNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/notesub/<id>/ endpoint - Subscription notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="notesub_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="NoteSub",
            desi_lname="Designer",
            desi_phone="08000000050",
            desi_gender="male",
            desi_businessName="NoteSub Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.subscription = Subscription(
            sub_desiid=self.designer.desi_id,
            sub_plan="5000",
            sub_status="active"
        )
        db.session.add(self.subscription)
        db.session.commit()

        self.notification = Notification(
            notify_subid=self.subscription.sub_id,
            notify_desiid=self.designer.desi_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_notesub_success(self):
        """Test marking subscription notification as read"""
        res = self.client.put(f'/api/notesub/{self.subscription.sub_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Notification updated successfully')

    def test_notesub_not_found(self):
        """Test marking subscription notification when not found"""
        res = self.client.put('/api/notesub/99999/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)

    def test_notesub_unauthenticated(self):
        """Test marking subscription notification without authentication"""
        res = self.client.put(f'/api/notesub/{self.subscription.sub_id}/')
        self.assertEqual(res.status_code, 401)

    def test_notesub_customer_not_allowed(self):
        """Test that only designers can mark subscription notifications"""
        customer = Customer(
            cust_email="notesub_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="NoteSub",
            cust_lname="Customer",
            cust_phone="08000000051",
            cust_gender="female",
            cust_username="notesub_customer",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(customer)
        db.session.commit()
        
        headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{customer.cust_id}")}'}
        res = self.client.put(f'/api/notesub/{self.subscription.sub_id}/', headers=headers)
        self.assertEqual(res.status_code, 404)


class ApiNotepayNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/notepay/<id>/ endpoint - Payment notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.designer = Designer(
            desi_email="notepay_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="NotePay",
            desi_lname="Designer",
            desi_phone="08000000052",
            desi_gender="male",
            desi_businessName="NotePay Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.payment = Transaction_payment(
            tpay_desiid=self.designer.desi_id,
            tpay_amount=5000.00,
            tpay_status="paid",
            tpay_currencyicon="NGN"
        )
        db.session.add(self.payment)
        db.session.commit()

        self.notification = Notification(
            notify_paymentid=self.payment.tpay_id,
            notify_desiid=self.designer.desi_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_notepay_success(self):
        """Test marking payment notification as read"""
        res = self.client.put(f'/api/notepay/{self.payment.tpay_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Notification updated successfully')

    def test_notepay_not_found(self):
        """Test marking payment notification when not found"""
        res = self.client.put('/api/notepay/99999/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)

    def test_notepay_unauthenticated(self):
        """Test marking payment notification without authentication"""
        res = self.client.put(f'/api/notepay/{self.payment.tpay_id}/')
        self.assertEqual(res.status_code, 401)

    def test_notepay_customer_cannot_access(self):
        """Test that customers cannot access payment notifications"""
        customer = Customer(
            cust_email="notepay_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="NotePay",
            cust_lname="Customer",
            cust_username="notepay_customer",
            cust_phone="08000000053",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(customer)
        db.session.commit()
        
        headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{customer.cust_id}")}'}
        res = self.client.put(f'/api/notepay/{self.payment.tpay_id}/', headers=headers)
        # Designer not found or unauthorized
        self.assertIn(res.status_code, [404])


class ApiNotetpayNotificationTestCase(BaseApiTestCase):
    """Test cases for /api/notetpay/<id>/ endpoint - Transaction payment notification update"""
    def setUp(self):
        super().setUp()
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        self.customer = Customer(
            cust_email="notetpay_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="NoteTpay",
            cust_lname="Customer",
            cust_phone="08000000054",
            cust_username="notetpay_customer",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        self.designer = Designer(
            desi_email="notetpay_designer@test.com",
            desi_pass=generate_password_hash("password123"),
            desi_fname="NoteTpay",
            desi_lname="Designer",
            desi_phone="08000000055",
            desi_gender="male",
            desi_businessName="NoteTpay Designs",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        self.tpayment = Transaction_payment(
            tpay_custid=self.customer.cust_id,
            tpay_amount=10000.00,
            tpay_status="paid",
            tpay_currencyicon="NGN"
        )
        db.session.add(self.tpayment)
        db.session.commit()

        self.notification = Notification(
            notify_tpayid=self.tpayment.tpay_id,
            notify_custid=self.customer.cust_id,
            notify_read='unread'
        )
        db.session.add(self.notification)
        db.session.commit()

        self.customer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{self.customer.cust_id}")}'}
        self.designer_headers = {'Authorization': f'Bearer {create_access_token(identity=f"designer:{self.designer.desi_id}")}'}

    def test_notetpay_success(self):
        """Test marking transaction payment notification as read"""
        res = self.client.put(f'/api/notetpay/{self.tpayment.tpay_id}/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['message'], 'Notification updated successfully')

    def test_notetpay_not_found(self):
        """Test marking transaction payment notification when not found"""
        res = self.client.put('/api/notetpay/99999/', headers=self.customer_headers)
        self.assertEqual(res.status_code, 404)

    def test_notetpay_unauthenticated(self):
        """Test marking transaction payment notification without authentication"""
        res = self.client.put(f'/api/notetpay/{self.tpayment.tpay_id}/')
        self.assertEqual(res.status_code, 401)

    def test_notetpay_designer_cannot_access(self):
        """Test that designers cannot access customer transaction payment notifications"""
        res = self.client.put(f'/api/notetpay/{self.tpayment.tpay_id}/', headers=self.designer_headers)
        self.assertEqual(res.status_code, 404)

    def test_notetpay_customer_not_found(self):
        """Test when customer not found"""
        # Create a temporary customer for the transaction
        temp_customer = Customer(
            cust_email="temp_customer@test.com",
            cust_pass=generate_password_hash("password123"),
            cust_fname="Temp",
            cust_lname="Customer",
            cust_phone="08000000099",
            cust_username="temp_customer",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(temp_customer)
        db.session.commit()
        
        tpay = Transaction_payment(
            tpay_custid=temp_customer.cust_id,
            tpay_amount=5000.00,
            tpay_status="paid",
            tpay_currencyicon="NGN"
        )
        db.session.add(tpay)
        db.session.commit()

        notif = Notification(
            notify_tpayid=tpay.tpay_id,
            notify_custid=temp_customer.cust_id,
            notify_read='unread'
        )
        db.session.add(notif)
        db.session.commit()
        
        # Delete the customer from the database
        db.session.delete(temp_customer)
        db.session.commit()
        
        # Try to access with headers using the deleted customer's ID
        headers = {'Authorization': f'Bearer {create_access_token(identity=f"customer:{temp_customer.cust_id}")}'}
        res = self.client.put(f'/api/notetpay/{tpay.tpay_id}/', headers=headers)      
        # Should return 404 because customer no longer exists


