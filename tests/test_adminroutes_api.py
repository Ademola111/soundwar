"""
Admin Routes API Test Cases
Comprehensive test suite for all admin endpoints and helper functions
"""

import unittest
import json
from datetime import datetime, date, timedelta, timezone
from werkzeug.security import generate_password_hash
from styleitapp import create_app, db
from styleitapp.models import (
    Admin, Superadmin, Designer, Customer, Posting, Image, Comment, Like,
    Share, Bookappointment, Subscription, Payment, Rating, Report,
    Transaction_payment, Bank, Newsletter, Transfer, Login, Activitylog,
    State, Lga, Countries
)
from flask_jwt_extended import create_access_token, create_refresh_token


class BaseAdminTestCase(unittest.TestCase):
    """Base test case class with common setup for all admin tests"""

    def setUp(self):
        """Set up test client and database"""
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test states and LGAs
        self.state = State(state_name="Test State")
        db.session.add(self.state)
        db.session.commit()

        self.lga = Lga(lga_name="Test LGA", lga_stateid=self.state.state_id)
        db.session.add(self.lga)
        db.session.commit()

        # Create test admin
        self.admin = Admin(
            admin_fname="Test",
            admin_lname="Admin",
            admin_email="testadmin@test.com",
            admin_pass=generate_password_hash("admin123"),
            admin_phone="08000000001",
            admin_gender="male",
            admin_status="active",
            admin_secretword="testsecret",
            admin_address="Test Address",
            admin_pic="test.jpg"
        )
        db.session.add(self.admin)
        db.session.commit()

        # Create test superadmin
        self.superadmin = Superadmin(
            spadmin_fname="Test",
            spadmin_lname="Superadmin",
            spadmin_email="testsuperadmin@test.com",
            spadmin_pass=generate_password_hash("superadmin123"),
            spadmin_phone="08000000002",
            spadmin_gender="female",
            spadmin_status="active",
            spadmin_secretword="supersecret",
            spadmin_address="Test Address",
            spadmin_pic="test.jpg"
        )
        db.session.add(self.superadmin)
        db.session.commit()

        # Create test designer
        self.designer = Designer(
            desi_email="testdesigner@test.com",
            desi_pass=generate_password_hash("designer123"),
            desi_fname="Test",
            desi_lname="Designer",
            desi_phone="08000000003",
            desi_gender="male",
            desi_businessName="Test Design Co",
            desi_status="actived",
            desi_stateid=self.state.state_id,
            desi_lgaid=self.lga.lga_id
        )
        db.session.add(self.designer)
        db.session.commit()

        # Create test customer
        self.customer = Customer(
            cust_email="testcustomer@test.com",
            cust_pass=generate_password_hash("customer123"),
            cust_fname="Test",
            cust_lname="Customer",
            cust_phone="08000000004",
            cust_username="testcustomer",
            cust_gender="female",
            cust_stateid=self.state.state_id,
            cust_lgaid=self.lga.lga_id
        )
        db.session.add(self.customer)
        db.session.commit()

        # Create test posting
        self.posting = Posting(
            post_title="Test Post",
            post_body="Test post body",
            post_desiid=self.designer.desi_id
        )
        db.session.add(self.posting)
        db.session.commit()

        # Create test subscription
        self.subscription = Subscription(
            sub_desiid=self.designer.desi_id,
            sub_plan="5000",
            sub_status="active",
            sub_startdate=str(date.today()),
            sub_enddate=str(date.today() + timedelta(days=30))
        )
        db.session.add(self.subscription)
        db.session.commit()

        # Create test payment
        self.payment = Transaction_payment(
            tpay_desiid=self.designer.desi_id,
            tpay_amount=5000.00,
            tpay_status="paid",
            tpay_currencyicon="NGN"
        )
        db.session.add(self.payment)
        db.session.commit()

        # Create test appointment
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

        # Create admin and superadmin headers
        self.admin_token = create_access_token(identity=f"admin:{self.admin.admin_id}")
        self.superadmin_token = create_access_token(identity=f"superadmin:{self.superadmin.spadmin_id}")
        self.admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
        self.superadmin_headers = {'Authorization': f'Bearer {self.superadmin_token}'}

    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class ApiAdminHomeTestCase(BaseAdminTestCase):
    """Test cases for /api/adminhome/ endpoint"""

    def test_admin_home_not_logged_in(self):
        """Test accessing admin home without authentication"""
        res = self.client.get('/api/adminhome/')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('redirect', data)

    def test_admin_home_as_admin(self):
        """Test accessing admin home as authenticated admin"""
        res = self.client.get('/api/adminhome/', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['admin']['id'], self.admin.admin_id)
        self.assertEqual(data['admin']['firstname'], self.admin.admin_fname)

    def test_admin_home_as_superadmin(self):
        """Test accessing admin home as authenticated superadmin"""
        res = self.client.get('/api/adminhome/', headers=self.superadmin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['superadmin']['id'], self.superadmin.spadmin_id)
        self.assertEqual(data['superadmin']['firstname'], self.superadmin.spadmin_fname)

    def test_admin_home_invalid_token(self):
        """Test accessing admin home with an invalid token"""
        headers = {'Authorization': 'Bearer invalid.token.here'}
        res = self.client.get('/api/adminhome/', headers=headers)
        self.assertIn(res.status_code, [401, 422])

    def test_admin_home_nonexistent_user_token(self):
        """Test accessing admin home with token for non-existent user"""
        token = create_access_token(identity=f"admin:99999")
        headers = {'Authorization': f'Bearer {token}'}
        res = self.client.get('/api/adminhome/', headers=headers)
        # Endpoint should still be reachable; no admin context provided
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, dict)
        # When token references a non-existent admin, response should not include admin/superadmin details
        self.assertNotIn('admin', data)
        self.assertNotIn('superadmin', data)
    
class AdminLoginTestCase(BaseAdminTestCase):
    """Test cases for /api/admin/login/ endpoint"""

    def test_admin_login_success(self):
        """Test successful admin login"""
        res = self.client.post('/api/admin/login/', 
                               json={
                                   'email': 'testadmin@test.com',
                                   'pwd': 'admin123'
                               })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('message', data)
        self.assertIn('token', data)
        self.assertIn('refresh_token', data)
        self.assertIn(data['admin']['role'], 'admin')
        self.assertIn(data['admin']['id'], self.admin.admin_id)

    def test_superadmin_login_success(self):
        """Test successful superadmin login"""
        res = self.client.post('/api/admin/login/',
                               json={
                                   'email': 'testsuperadmin@test.com',
                                   'pwd': 'superadmin123'
                               })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn(data['superadmin']['role'], 'superadmin')
        self.assertIn('token', data)

    def test_admin_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        res = self.client.post('/api/admin/login/',
                               json={
                                   'email': 'testadmin@test.com',
                                   'pwd': 'wrongpassword'
                               })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn('Invalid credentials', data['message'])

    def test_admin_login_empty_fields(self):
        """Test login with empty fields"""
        res = self.client.post('/api/admin/login/',
                               json={
                                   'email': '',
                                   'pwd': 'admin123'
                               })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('empty', data['message'].lower())

    def test_admin_login_deactivated_account(self):
        """Test login with deactivated admin account"""
        self.admin.admin_status = 'deactive'
        db.session.commit()
        
        res = self.client.post('/api/admin/login/',
                               json={
                                   'email': 'testadmin@test.com',
                                   'pwd': 'admin123'
                               })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn('deactivated', data['message'])


# class AdminForgottenPasswordTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/forgottenpassword endpoint"""

#     def test_forgotten_password_admin_success(self):
#         """Test successful password reset for admin"""
#         res = self.client.post('/api/admin/forgottenpassword',
#                                json={
#                                    'username': 'testsecret',
#                                    'email': 'testadmin@test.com',
#                                    'pwd': 'newadmin123',
#                                    'cpwd': 'newadmin123'
#                                })
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertEqual(data['status'], 'success')
#         self.assertIn('updated', data['message'].lower())

#     def test_forgotten_password_superadmin_success(self):
#         """Test successful password reset for superadmin"""
#         res = self.client.post('/api/admin/forgottenpassword',
#                                json={
#                                    'username': 'supersecret',
#                                    'email': 'testsuperadmin@test.com',
#                                    'pwd': 'newsuperadmin123',
#                                    'cpwd': 'newsuperadmin123'
#                                })
#         self.assertEqual(res.status_code, 200)

#     def test_forgotten_password_mismatch(self):
#         """Test password reset with mismatched passwords"""
#         res = self.client.post('/api/admin/forgottenpassword',
#                                json={
#                                    'username': 'testsecret',
#                                    'email': 'testadmin@test.com',
#                                    'pwd': 'newadmin123',
#                                    'cpwd': 'differentpassword'
#                                })
#         self.assertEqual(res.status_code, 400)
#         data = res.get_json()
#         self.assertIn('not match', data['message'].lower())

#     def test_forgotten_password_empty_fields(self):
#         """Test password reset with empty fields"""
#         res = self.client.post('/api/admin/forgottenpassword',
#                                json={
#                                    'username': '',
#                                    'email': 'testadmin@test.com',
#                                    'pwd': 'newadmin123',
#                                    'cpwd': 'newadmin123'
#                                })
#         self.assertEqual(res.status_code, 400)

#     def test_forgotten_password_invalid_email(self):
#         """Test password reset with invalid email"""
#         res = self.client.post('/api/admin/forgottenpassword',
#                                json={
#                                    'username': 'testsecret',
#                                    'email': 'nonexistent@test.com',
#                                    'pwd': 'newadmin123',
#                                    'cpwd': 'newadmin123'
#                                })
#         self.assertEqual(res.status_code, 404)


# class AdminLogoutTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/logout/ endpoint"""

#     def test_admin_logout_success(self):
#         """Test successful admin logout"""
#         res = self.client.post('/api/admin/logout/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('successfully', data['message'].lower())

#     def test_superadmin_logout_success(self):
#         """Test successful superadmin logout"""
#         res = self.client.post('/api/admin/logout/', headers=self.superadmin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_logout_without_authentication(self):
#         """Test logout without authentication"""
#         res = self.client.post('/api/admin/logout/')
#         self.assertEqual(res.status_code, 401)


# class AdminRefreshTokenTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/refresh endpoint"""

#     def test_admin_refresh_token(self):
#         """Test refreshing admin access token"""
#         refresh_token = create_refresh_token(identity=f"admin:{self.admin.admin_id}")
#         headers = {'Authorization': f'Bearer {refresh_token}'}

#         res = self.client.post('/api/admin/refresh', headers=headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('access_token', data)
#         self.assertIsInstance(data.get('access_token'), str)

#     def test_admin_home_invalid_token(self):
#         """Test accessing admin home with an invalid token"""
#         headers = {'Authorization': 'Bearer invalid.token.here'}
#         res = self.client.get('/api/adminhome/', headers=headers)
#         self.assertIn(res.status_code, [401, 422])

#     def test_admin_home_nonexistent_user_token(self):
#         """Test accessing admin home with token for non-existent user"""
#         token = create_access_token(identity=f"admin:99999")
#         headers = {'Authorization': f'Bearer {token}'}
#         res = self.client.get('/api/adminhome/', headers=headers)
#         self.assertIn(res.status_code, [401, 404])
#         """Test refreshing admin access token"""
#         refresh_token = create_refresh_token(identity=f"admin:{self.admin.admin_id}")
#         headers = {'Authorization': f'Bearer {refresh_token}'}
        
#         res = self.client.post('/api/admin/refresh', headers=headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('access_token', data)

#     def test_superadmin_refresh_token(self):
#         """Test refreshing superadmin access token"""
#         refresh_token = create_refresh_token(identity=f"superadmin:{self.superadmin.spadmin_id}")
#         headers = {'Authorization': f'Bearer {refresh_token}'}
        
#         res = self.client.post('/api/admin/refresh', headers=headers)
#         self.assertEqual(res.status_code, 200)


# # ============================================================================
# # DASHBOARD & ACTIVITY TESTS
# # ============================================================================

# class AdminDashboardTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/dashboard/ endpoint"""

#     def test_dashboard_as_admin(self):
#         """Test accessing dashboard as admin"""
#         res = self.client.get('/api/admin/dashboard/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('total_users', data)
#         self.assertIn('total_creator', data)
#         self.assertIn('total_client', data)

#     def test_dashboard_as_superadmin(self):
#         """Test accessing dashboard as superadmin"""
#         res = self.client.get('/api/admin/dashboard/', headers=self.superadmin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_dashboard_without_authentication(self):
#         """Test accessing dashboard without authentication"""
#         res = self.client.get('/api/admin/dashboard/')
#         self.assertEqual(res.status_code, 401)


# class AdminActivityNavigationTestCase(BaseAdminTestCase):
#     """Test cases for activity navigation endpoints"""

#     def test_previous_day_activity(self):
#         """Test /api/activity/prev/ endpoint"""
#         res = self.client.get('/api/activity/prev/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('count', data)

#     def test_next_day_activity(self):
#         """Test /api/activity/next endpoint"""
#         res = self.client.get('/api/activity/next', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_previous_week_activity(self):
#         """Test /api/activity/prevweek/ endpoint"""
#         res = self.client.get('/api/activity/prevweek/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_next_week_activity(self):
#         """Test /api/activity/nextweek/ endpoint"""
#         res = self.client.get('/api/activity/nextweek/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_previous_month_activity(self):
#         """Test /api/activity/prevmonth/ endpoint"""
#         res = self.client.get('/api/activity/prevmonth/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_next_month_activity(self):
#         """Test /api/activity/nextmonth/ endpoint"""
#         res = self.client.get('/api/activity/nextmonth/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_previous_year_activity(self):
#         """Test /api/activity/prevyear/ endpoint"""
#         res = self.client.get('/api/activity/prevyear/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)

#     def test_next_year_activity(self):
#         """Test /api/activity/nextyear/ endpoint"""
#         res = self.client.get('/api/activity/nextyear/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)


# # ============================================================================
# # CONTENT MANAGEMENT TESTS
# # ============================================================================

# class AdminTrendingTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/trending/ endpoint"""

#     def test_get_trending_posts(self):
#         """Test retrieving trending posts"""
#         res = self.client.get('/api/admin/trending/', headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('posts', data)


# class AdminPostDetailTestCase(BaseAdminTestCase):
#     """Test cases for /api/adminpost/<id>/ endpoint"""

#     def test_get_post_detail_success(self):
#         """Test retrieving post detail as admin"""
#         res = self.client.get(f'/api/adminpost/{self.posting.post_id}/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertEqual(data['post'], self.posting.post_id)

#     def test_get_post_detail_not_found(self):
#         """Test retrieving non-existent post"""
#         res = self.client.get('/api/adminpost/99999/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 404)

#     def test_get_post_detail_without_auth(self):
#         """Test retrieving post detail without authentication"""
#         res = self.client.get(f'/api/adminpost/{self.posting.post_id}/')
#         self.assertEqual(res.status_code, 401)


# class AdminBanTestCase(BaseAdminTestCase):
#     """Test cases for /api/ban endpoint"""

#     def test_ban_user_success(self):
#         """Test banning a user"""
#         res = self.client.post('/api/ban',
#                               headers=self.admin_headers,
#                               json={
#                                   'userid': self.customer.cust_id,
#                                   'usertype': 'customer'
#                               })
#         self.assertIn(res.status_code, [200, 404])

#     def test_ban_invalid_user(self):
#         """Test banning non-existent user"""
#         res = self.client.post('/api/ban',
#                               headers=self.admin_headers,
#                               json={
#                                   'userid': 99999,
#                                   'usertype': 'customer'
#                               })
#         self.assertEqual(res.status_code, 404)


# class AdminTrashTestCase(BaseAdminTestCase):
#     """Test cases for /api/trash/ endpoint"""

#     def test_trash_post_success(self):
#         """Test moving post to trash"""
#         res = self.client.post('/api/trash/',
#                               headers=self.admin_headers,
#                               json={'postid': self.posting.post_id})
#         self.assertIn(res.status_code, [200, 404])

#     def test_trash_invalid_post(self):
#         """Test trashing non-existent post"""
#         res = self.client.post('/api/trash/',
#                               headers=self.admin_headers,
#                               json={'postid': 99999})
#         self.assertEqual(res.status_code, 404)


# # ============================================================================
# # USER MANAGEMENT TESTS
# # ============================================================================

# class AdminDesignersListTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/designers/ endpoint"""

#     def test_get_all_designers(self):
#         """Test retrieving all designers"""
#         res = self.client.get('/api/admin/designers/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('designers', data)

#     def test_get_designers_pagination(self):
#         """Test designers list with pagination"""
#         res = self.client.get('/api/admin/designers/?page=1',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)


# class AdminCustomersListTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/allcustomers/ endpoint"""

#     def test_get_all_customers(self):
#         """Test retrieving all customers"""
#         res = self.client.get('/api/admin/allcustomers/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('customers', data)


# class AdminDesignerDetailTestCase(BaseAdminTestCase):
#     """Test cases for /api/designers/<id>/ endpoint"""

#     def test_get_designer_detail_success(self):
#         """Test retrieving designer details"""
#         res = self.client.get(f'/api/designers/{self.designer.desi_id}/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertEqual(data['Creator'], self.designer.desi_id)

#     def test_get_designer_detail_not_found(self):
#         """Test retrieving non-existent designer"""
#         res = self.client.get('/api/designers/99999/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 404)


# class AdminCustomerDetailTestCase(BaseAdminTestCase):
#     """Test cases for /api/customers/<id>/ endpoint"""

#     def test_get_customer_detail_success(self):
#         """Test retrieving customer details"""
#         res = self.client.get(f'/api/customers/{self.customer.cust_id}/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertEqual(data['client'], self.customer.cust_id)

#     def test_get_customer_detail_not_found(self):
#         """Test retrieving non-existent customer"""
#         res = self.client.get('/api/customers/99999/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 404)


# class AdminDeactivateTestCase(BaseAdminTestCase):
#     """Test cases for /api/deactivat/ endpoint"""

#     def test_deactivate_user(self):
#         """Test deactivating a user"""
#         res = self.client.post('/api/deactivat/',
#                               headers=self.admin_headers,
#                               json={
#                                   'userid': self.customer.cust_id,
#                                   'usertype': 'customer'
#                               })
#         self.assertIn(res.status_code, [200, 404])


# class AdminActivateTestCase(BaseAdminTestCase):
#     """Test cases for /api/activat/ endpoint"""

#     def test_activate_user(self):
#         """Test activating a deactivated user"""
#         # First deactivate the customer
#         self.customer.cust_status = 'deactived'
#         db.session.commit()
        
#         res = self.client.post('/api/activat/',
#                               headers=self.admin_headers,
#                               json={
#                                   'userid': self.customer.cust_id,
#                                   'usertype': 'customer'
#                               })
#         self.assertIn(res.status_code, [200, 404])


# # ============================================================================
# # SEARCH TESTS
# # ============================================================================

# class AdminSearchTestCase(BaseAdminTestCase):
#     """Test cases for /api/adminsearch/ endpoint"""

#     def test_search_posts(self):
#         """Test searching posts"""
#         res = self.client.post('/api/adminsearch/',
#                               headers=self.admin_headers,
#                               json={'query': 'Test'})
#         self.assertEqual(res.status_code, 200)

#     def test_search_empty_query(self):
#         """Test search with empty query"""
#         res = self.client.post('/api/adminsearch/',
#                               headers=self.admin_headers,
#                               json={'query': ''})
#         self.assertIn(res.status_code, [200, 400])


# class AdminSearchDesignerTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/search_creator/ endpoint"""

#     def test_search_designer(self):
#         """Test searching for designers"""
#         res = self.client.post('/api/admin/search_creator/',
#                               headers=self.admin_headers,
#                               json={'query': 'Test'})
#         self.assertEqual(res.status_code, 200)


# class AdminSearchCustomerTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/search_client/ endpoint"""

#     def test_search_customer(self):
#         """Test searching for customers"""
#         res = self.client.post('/api/admin/search_client/',
#                               headers=self.admin_headers,
#                               json={'query': 'Test'})
#         self.assertEqual(res.status_code, 200)


# class AdminSearchSubscriptionTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/search_subcription/ endpoint"""

#     def test_search_subscription(self):
#         """Test searching for subscriptions"""
#         res = self.client.post('/api/admin/search_subcription/',
#                               headers=self.admin_headers,
#                               json={'query': 'premium'})
#         self.assertEqual(res.status_code, 200)


# class AdminSearchBookingTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/search_booking_appointment/ endpoint"""
#     def test_admin_refresh_token(self):
#         """Test refreshing admin access token"""
#         refresh_token = create_refresh_token(identity=f"admin:{self.admin.admin_id}")
#         headers = {'Authorization': f'Bearer {refresh_token}'}

#         res = self.client.post('/api/admin/refresh', headers=headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('access_token', data)
#         self.assertIsInstance(data.get('access_token'), str)

# class AdminAppointmentsTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/appointments endpoint"""

#     def test_get_all_appointments(self):
#         """Test retrieving all appointments"""
#         res = self.client.get('/api/admin/appointments',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('appointments', data)


# class AdminPaymentTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/payment endpoint"""

#     def test_get_all_payments(self):
#         """Test retrieving all payments"""
#         res = self.client.get('/api/admin/payment',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('payments', data)


# class AdminSubscriptionTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/subscription endpoint"""

#     def test_get_all_subscriptions(self):
#         """Test retrieving all subscriptions"""
#         res = self.client.get('/api/admin/subscription',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)
#         data = res.get_json()
#         self.assertIn('subscriptions', data)


# class AdminReportTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/report endpoint"""

#     def test_get_all_reports(self):
#         """Test retrieving all reports"""
#         res = self.client.get('/api/admin/report',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)


# class AdminStaffActivityTestCase(BaseAdminTestCase):
#     """Test cases for /api/staffactivity endpoint"""

#     def test_get_staff_activity(self):
#         """Test retrieving staff activity"""
#         res = self.client.get('/api/staffactivity',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 200)


# # ============================================================================
# # PAYMENT & TRANSFER TESTS
# # ============================================================================

# class AdminApprovePaymentTestCase(BaseAdminTestCase):
#     """Test cases for /api/approve/<id>/ endpoint"""

#     def test_approve_payment_success(self):
#         """Test approving a payment"""
#         res = self.client.get(f'/api/approve/{self.payment.tpay_id}/',
#                              headers=self.admin_headers)
#         self.assertIn(res.status_code, [200, 404])

#     def test_approve_invalid_payment(self):
#         """Test approving non-existent payment"""
#         res = self.client.get('/api/approve/99999/',
#                              headers=self.admin_headers)
#         self.assertEqual(res.status_code, 404)


# class AdminSendFundTestCase(BaseAdminTestCase):
#     """Test cases for /api/sendfund/ endpoint"""

#     def test_send_fund_success(self):
#         """Test sending funds to designer"""
#         res = self.client.post('/api/sendfund/',
#                               headers=self.admin_headers,
#                               json={
#                                   'designer_id': self.designer.desi_id,
#                                   'amount': 5000.00
#                               })
#         self.assertIn(res.status_code, [200, 404])


# class AdminFinalizeTransferTestCase(BaseAdminTestCase):
#     """Test cases for /api/finalize_transfer endpoint"""

#     def test_finalize_transfer(self):
#         """Test finalizing fund transfer"""
#         res = self.client.post('/api/finalize_transfer',
#                               headers=self.admin_headers,
#                               json={'transfer_id': 1})
#         self.assertIn(res.status_code, [200, 404])


# class AdminVerifyTransferTestCase(BaseAdminTestCase):
#     """Test cases for /api/verify_transfer endpoint"""

#     def test_verify_transfer(self):
#         """Test verifying fund transfer"""
#         res = self.client.post('/api/verify_transfer',
#                               headers=self.admin_headers,
#                               json={'transfer_id': 1})
#         self.assertIn(res.status_code, [200, 404])


# # ============================================================================
# # ADMIN MANAGEMENT TESTS
# # ============================================================================

# class AdminSignupTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin/signup/ endpoint"""

#     def test_admin_signup_success(self):
#         """Test creating new admin account"""
#         res = self.client.post('/api/admin/signup/',
#                               headers=self.superadmin_headers,
#                               json={
#                                   'fname': 'New',
#                                   'lname': 'Admin',
#                                   'email': 'newadmin@test.com',
#                                   'pwd': 'password123',
#                                   'cpwd': 'password123',
#                                   'phone': '08000000010',
#                                   'gender': 'male',
#                                   'secretword': 'newsecret',
#                                   'address': 'New Address'
#                               })
#         self.assertIn(res.status_code, [200, 201, 400])

#     def test_admin_signup_duplicate_email(self):
#         """Test signup with duplicate email"""
#         res = self.client.post('/api/admin/signup/',
#                               headers=self.superadmin_headers,
#                               json={
#                                   'fname': 'New',
#                                   'lname': 'Admin',
#                                   'email': 'testadmin@test.com',
#                                   'pwd': 'password123',
#                                   'cpwd': 'password123',
#                                   'phone': '08000000010',
#                                   'gender': 'male',
#                                   'secretword': 'newsecret',
#                                   'address': 'New Address'
#                               })
#         self.assertIn(res.status_code, [400, 409])


# # ============================================================================
# # NOTIFICATION & COMMUNICATION TESTS
# # ============================================================================

# class AdminMailNotificationTestCase(BaseAdminTestCase):
#     """Test cases for /api/mail-notification endpoint"""

#     def test_send_mail_notification(self):
#         """Test sending mail notification"""
#         res = self.client.post('/api/mail-notification',
#                               headers=self.admin_headers,
#                               json={
#                                   'recipient_id': self.customer.cust_id,
#                                   'subject': 'Test Subject',
#                                   'message': 'Test Message'
#                               })
#         self.assertIn(res.status_code, [200, 400, 404])


# # ============================================================================
# # MISCELLANEOUS TESTS
# # ============================================================================

# class AdminSearchReferenceTestCase(BaseAdminTestCase):
#     """Test cases for /api/searchref/ endpoint"""

#     def test_search_reference(self):
#         """Test searching reference data"""
#         res = self.client.post('/api/searchref/',
#                               headers=self.admin_headers,
#                               json={'query': 'test'})
#         self.assertIn(res.status_code, [200, 400])


# class AdminDeactivateAccountTestCase(BaseAdminTestCase):
#     """Test cases for /api/admin_deactivate endpoint"""

#     def test_admin_deactivate_user(self):
#         """Test admin deactivating user"""
#         res = self.client.post('/api/admin_deactivate',
#                               headers=self.superadmin_headers,
#                               json={
#                                   'userid': self.customer.cust_id,
#                                   'usertype': 'customer'
#                               })
#         self.assertIn(res.status_code, [200, 404])


# class AdminWebhookTestCase(BaseAdminTestCase):
#     """Test cases for /api/webhookupdate/ endpoint"""

#     def test_webhook_update(self):
#         """Test webhook update"""
#         res = self.client.post('/api/webhookupdate/',
#                               json={'event': 'payment.success'})
#         self.assertIn(res.status_code, [200, 400])


# if __name__ == '__main__':
#     unittest.main()
