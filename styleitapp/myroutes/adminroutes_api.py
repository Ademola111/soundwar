from ast import stmt
import os, math, random, json, requests
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import desc, func, extract, or_, case, select, text
from flask import Blueprint, current_app, render_template, request, redirect, session, jsonify
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity, create_access_token, verify_jwt_in_request, create_refresh_token
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from styleitapp import db, csrf
from styleitapp.junk import styleit, spamming
from styleitapp.models import (Designer, Customer, Posting, Image,
                               Comment, Like, Share, Bookappointment, Countries,
                               Subscription, Payment, Admin, TokenBlocklist, Superadmin, Rating,
                               Report, Transaction_payment, Bank, Newsletter,
                               Bankcodes, Transfer, Login, Activitylog, State, Lga)
from styleitapp import mail

admin_api_bp = Blueprint("admin_api", __name__)
rows_per_page = 12
rows_page = 3

"""homepage"""
@admin_api_bp.route('/api/adminhome/', methods=['GET'])
def api_admin_home():
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        pass

    admin = get_jwt_identity()
    spadmin = get_jwt_identity()

    # User is already logged in as admin
    if admin:
        adm = db.session.get(Admin, admin) if admin else None
        return jsonify({'redirect': '/api/admin/dashboard/',
                        'admin': {
                            'id': adm.admin_id if adm else None,
                            'firstname': adm.admin_fname if adm else None,
                            'lastname': adm.admin_lname if adm else None
                        }
                        })
    # User is already logged in as superadmin
    elif spadmin:
        spa = db.session.get(Superadmin, spadmin) if spa else None
        return jsonify({'redirect': '/api/admin/dashboard/',
                        'superadmin': {
                            'id': spa.spadmin_id if spa else None,
                            'firstname': spa.spadmin_fname if spa else None,
                            'lastname': spa.spadmin_lname if spa else None
                        }
                        })
    else:
        return jsonify({
            'status': 'unauthenticated',
            'message': 'No valid admin session found.'
        }), 401



"""login"""
@csrf.exempt
@admin_api_bp.route('/api/admin/login/', methods=['POST'])
def admin_login_api():
    if request.method == "POST":
        email = request.json.get('email')
        pwd = request.json.get('pwd')
        # print(f"Your email is {email}", f"Your password is {pwd}")
        # validating form data field
        if not email or not pwd:
            return jsonify({"message": "One or more fields are empty"}), 400

        # check credentials
        adm = db.session.query(Admin).filter(Admin.admin_email == email).first()
        spa = db.session.query(Superadmin).filter(Superadmin.spadmin_email == email).first()
        # print(f"spa is {spa}")
        if adm and adm.admin_status == 'active':
            if check_password_hash(adm.admin_pass, pwd):
                # print(check_password_hash(adm.admin_pass, pwd))
                session['admin'] = adm.admin_id
                access_token = create_access_token(identity=f"admin:{adm.admin_id}")
                refresh_token = create_refresh_token(identity=f"admin:{adm.admin_id}")
                lo = Login(login_email=adm.admin_email, login_adminid=adm.admin_id, last_active_at=datetime.now(timezone.utc))
                db.session.add(lo)
                db.session.commit()
                return jsonify({"message": "Login successful",
                                "redirect": "/api/admin/dashboard/",
                                "token":access_token,
                                "refresh_token":refresh_token,
                                "admin":{
                                    "role":"admin",
                                    "id": adm.admin_id,
                                    "firstname": adm.admin_fname,
                                    "lastname":adm.admin_lname,
                                    "email":adm.admin_email,
                                    "profile_pic":f"https://styleitafrica.pythonanywhere.com/static/images/profile/admin/{adm.admin_pic}",
                                    "status":adm.admin_status,
                                    "access":adm.admin_secretword,
                                    "phone":adm.admin_phone,
                                    "address":adm.admin_address,
                                    "gender":adm.admin_gender
                                }
                                }), 200
        elif spa and spa.spadmin_status == 'active':
            if check_password_hash(spa.spadmin_pass, pwd):
                session['superadmin'] = spa.spadmin_id
                access_token = create_access_token(identity=f"superadmin:{spa.spadmin_id}")
                refresh_token = create_refresh_token(identity=f"superadmin:{spa.spadmin_id}")
                lo = Login(login_email=spa.spadmin_email, login_spadminid=spa.spadmin_id, last_active_at=datetime.now(timezone.utc))
                db.session.add(lo)
                db.session.commit()
                return jsonify({"message": "Login successful",
                                "redirect": "/api/admin/dashboard/",
                                "token":access_token,
                                "refresh_token":refresh_token,
                                "superadmin":{
                                    "role":"superadmin",
                                    "id": spa.spadmin_id,
                                    "firstname": spa.spadmin_fname,
                                    "lastname":spa.spadmin_lname,
                                    "email":spa.spadmin_email,
                                    "profile_pic":f"https://styleitafrica.pythonanywhere.com/static/images/profile/admin/{spa.spadmin_pic}",
                                    "status":spa.spadmin_status,
                                    "access":spa.spadmin_secretword,
                                    "phone":spa.spadmin_phone,
                                    "address":spa.spadmin_address,
                                    "gender":spa.spadmin_gender
                                }
                                }), 200
        else:
            if adm and adm.admin_status == 'deactive':
                return jsonify({"message": "Your account has been deactivated. Please contact support."}), 403
            elif spa and spa.spadmin_status == 'deactive':
                return jsonify({"message": "Your account has been deactivated. Please contact support."}), 403

            return jsonify({"message": "Invalid credentials."}), 401
    return jsonify({"message": "Method not allowed"}), 405


"""Admin Forgotten Password"""
@csrf.exempt
@admin_api_bp.route('/api/admin/forgottenpassword', methods=['POST'])
def api_admin_forgotten_password():
    admin = session.get('admin')
    spadmin = session.get('superadmin')
    if admin or spadmin:
        return jsonify({'status': 'redirect',
                        'message': 'Already logged in', 'redirect_url': '/api/admin/dashboard/'}), 403

    data = request.json
    username = data.get('username')
    email = data.get('email')
    pwd = data.get('pwd')
    cpwd = data.get('cpwd')

    # Validate fields
    if not username or not email or not pwd or not cpwd:
        return jsonify({'status': 'error', 'message': 'One or more fields are empty'}), 400
    elif pwd != cpwd:
        return jsonify({'status': 'error', 'message': 'Password and confirmation do not match'}), 400

    hashed_pwd = generate_password_hash(pwd)
    cust = Admin.query.filter_by(admin_email=email).first()
    spa = Superadmin.query.filter_by(spadmin_email=email).first()

    if cust:
        if cust.admin_status == 'deactive':
            return jsonify({'status': 'error', 'message': 'Record cannot be found'}), 404
        elif check_password_hash(cust.admin_pass, pwd):
            return jsonify({'status': 'error', 'message': 'This password has been used earlier'}), 400
        elif cust.admin_secretword == username:
            cust.admin_pass = hashed_pwd
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Password updated successfully'}), 200

    elif spa:
        if spa.spadmin_status == 'deactive':
            return jsonify({'status': 'error', 'message': 'Record cannot be found'}), 404
        elif check_password_hash(spa.spadmin_pass, pwd):
            return jsonify({'status': 'error', 'message': 'This password has been used earlier'}), 400
        elif spa.spadmin_secretword == username:
            spa.spadmin_pass = hashed_pwd
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Password updated successfully'}), 200

    return jsonify({'status': 'error', 'message': 'Invalid email address or secret word'}), 404


"""Admin and Superadmin Dashboard"""
@admin_api_bp.route('/api/admin/dashboard/', methods=['GET'])
@jwt_required()
def api_dashboard():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    # Queries
    subq_likes = db.session.query(Like.like_postid, func.count(Like.like_id).label('like_count')).group_by(Like.like_postid).subquery()
    subq_comments = db.session.query(Comment.com_postid, func.count(Comment.com_id).label('com_count')).group_by(Comment.com_postid).subquery()
    subq_shares = db.session.query(Share.share_postid, func.count(Share.share_id).label('share_count')).group_by(Share.share_postid).subquery()

    pstn = db.session.query(Posting).outerjoin(subq_likes, Posting.post_id == subq_likes.c.like_postid)\
        .outerjoin(subq_comments, Posting.post_id == subq_comments.c.com_postid)\
        .outerjoin(subq_shares, Posting.post_id == subq_shares.c.share_postid)\
        .filter(Posting.post_id == Image.image_postid)\
        .order_by(desc(subq_likes.c.like_count), desc(subq_comments.c.com_count),
                  desc(subq_shares.c.share_count), desc(Posting.post_date)).all()

    # Additional data
    appt = Bookappointment.query.order_by(desc(Bookappointment.ba_id)).all()
    appt2 = Bookappointment.query.order_by(desc(Bookappointment.ba_id)).limit(10).all()
    pymt = Payment.query.order_by(desc(Payment.payment_id)).all()
    pymt2 = Payment.query.order_by(desc(Payment.payment_id)).limit(10).all()
    sublist = Subscription.query.order_by(desc(Subscription.sub_date)).all()
    sublist2 = Subscription.query.order_by(desc(Subscription.sub_date)).limit(10).all()
    srepo = Report.query.order_by(desc(Report.report_id)).all()
    srepo2 = Report.query.order_by(desc(Report.report_id)).limit(10).all()
    desi = Designer.query.all()
    desi2 = Designer.query.limit(10).all()
    cust = Customer.query.all()
    cust2 = Customer.query.limit(10).all()
    state = State.query.all()
    lga = Lga.query.all()
    cust_banned = Customer.query.filter_by(cust_status='banned').all()
    desi_banned = Designer.query.filter_by(desi_status='banned').all()
    banned = len(cust_banned) + len(desi_banned)
    cust_suspended = Customer.query.filter_by(cust_status='suspended').all()
    desi_suspended = Designer.query.filter_by(desi_status='suspended').all()
    suspended = len(cust_suspended) + len(desi_suspended)
    total_admin = Admin.query.all()
    total_transaction = Transaction_payment.query.all()
    tpayn= sum(tp.tpay_amount for tp in total_transaction)
    payn = sum(pm.payment_amount for pm in pymt)
    total_revenue = tpayn + payn
    
    active_time = db.session.query(
    case((Login.login_custid != None, Login.login_custid),
    else_=Login.login_desiid).label("user_id"), func.sum((
            func.strftime('%s', func.coalesce(Login.logout_date, func.current_timestamp())) -
            func.strftime('%s', Login.login_date)
        )).label("total_active_seconds")).group_by("user_id").all()

    # Time-based data
    current_date = datetime.now()
    # end_date = current_date + timedelta(days=1)
    week_start = current_date - timedelta(days=current_date.weekday())
    week_end = week_start + timedelta(days=7)
    month_start = datetime(current_date.year, current_date.month, 1)
    month_end = datetime(current_date.year + (current_date.month // 12), ((current_date.month % 12) + 1), 1)
    year_start = datetime(current_date.year, 1, 1)
    year_end = datetime(current_date.year + 1, 1, 1)

    if admin:
        adm = db.session.get(Admin, admin)
        prof = adm  # Assuming you have serialize() method on your model
        day_data = Activitylog.query.filter(
            extract('day', Activitylog.date) == current_date.day,
            Activitylog.adminid == adm.admin_id).all()
        week_data = Activitylog.query.filter(
            Activitylog.date >= week_start, Activitylog.date < week_end,
            Activitylog.adminid == adm.admin_id).all()
        month_data = Activitylog.query.filter(
            Activitylog.date >= month_start, Activitylog.date < month_end,
            Activitylog.adminid == adm.admin_id).all()
        year_data = Activitylog.query.filter(
            Activitylog.date >= year_start, Activitylog.date < year_end,
            Activitylog.adminid == adm.admin_id).all()


        return jsonify({
            'user': {"admin_id":prof.admin_id if prof else None, "firstname":prof.admin_fname if prof else None,
                "lastname":prof.admin_lname if prof else None, "admin_gender":prof.admin_gender if prof else None, "admin_phone":prof.admin_phone if prof else None,
                "admin_email":prof.admin_email if prof else None, "admin_address":prof.admin_address if prof else None,
                "admin_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/admin/{prof.admin_pic}" if prof else None,
                "admin_secret": prof.admin_secretword if prof else None
                },
            'posts': [{"postId":po.post_id if po else None, "postTitle":po.post_title if po else None,
                "content":po.post_body if po else None,
                "date":po.post_date if po else None, "postSuspend":po.post_suspend if po else None,
                "postDelete":po.post_delete if po else None,
                "postCreator":po.designerobj.desi_businessName if po.designerobj else None,
                "image":[{"postImage":img.image_name if img else None,
                          "postImageUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"} for img in po.imagepostobj],
                } for po in pstn],
            'appointments': [{"booking_id": bk.ba_id, 'date':bk.ba_date if bk else None, 'booking_date':bk.ba_bookingDate if bk else None, 'booking_time':bk.ba_bookingTime if bk else None,
                "collectionTime":bk.ba_collectionTime if bk else None, "collectionDate": bk.ba_collectionDate if bk else None,
                "status":bk.ba_status if bk else None,
                "collectionStatus": bk.ba_custstatus if bk else None, "paymentStatus": bk.ba_paystatus if bk else None,
                "reason": bk.ba_reason if bk else None,
                "client_username": bk.custbaobj.cust_username if bk.custbaobj else None,
                "clientCountry":bk.custbaobj.custcountry.country_name if bk.custbaobj.custcountry else None,
                "clientPhone":bk.custbaobj.cust_phone if bk.custbaobj else None, "client_firstname":bk.custbaobj.cust_fname if bk.custbaobj else None,
                "client_lastname":bk.custbaobj.cust_lname if bk.custbaobj else None,
                "creator_businessName": bk.desibaobj.desi_businessName if bk.desibaobj else None,
                "creator_country":bk.desibaobj.desicountry.country_name if bk.desibaobj and bk.desibaobj.desicountry else None,
                "creatorPhone":bk.desibaobj.desi_phone if bk.desibaobj else None, "creator_firstname":bk.desibaobj.desi_fname if bk.desibaobj else None,
                "creatorlname":bk.desibaobj.desi_lname if bk.desibaobj else None} for bk in appt2],
            'payments': [{"paymentID":pay.payment_id if pay else None, "payment_transNo":pay.payment_transNo if pay else None,
                          "patment_transdate":pay.payment_transdate if pay else None, "payment_Amount":pay.payment_amount if pay else None,
                          "payment_status":pay.payment_status if pay else None,
                          "payment_by":pay.desipaymentobj.desi_businessName if pay.desipaymentobj else None,
                          "payment_for":pay.subpaymentobj.sub_plan if pay.subpaymentobj else None} for pay in pymt2],
            'subscriptions': [{"sub_plan":s.sub_plan if s else None, "sub_date":s.sub_date if s else None, "startdate":s.sub_startdate if s else None,
                               "enddate":s.sub_enddate if s else None, "refno":s.sub_ref if s else None, "status":s.sub_status if s else None,
                               "sub_payment_status":s.sub_paystatus if s else None, "sub_by":s.subdesiobj.desi_businessName if s else None,
                               } for s in sublist2],
            'reports': [{"report_id": r.report_id if r else None, "report_date":r.report_date if r else None, "reason":r.report_reason if r else None, "Client_reported":r.reporter if r else None,
                         "client_username":r.custreportobj.cust_username if r.custreportobj else "",
                         "creator_reported":r.desireportobj.desi_businessName if r.desireportobj else ""}
                         for r in srepo2],
            'designers': [{'designer_id': des.desi_id if des else None,'firstname': des.desi_fname if des else None,'lastname': des.desi_lname if des else None,
                           'email': des.desi_email if des else None,'phone': des.desi_phone if des else None,'address': des.desi_address if des else None,
                            'profile_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{des.desi_pic}" if des else None, 'gender':des.desi_gender if des else None,
                            "businessName":des.desi_businessName if des else None,'registerDate':des.desi_regdate if des else None,
                            'status': des.desi_status if des else None,'access': des.desi_access if des else None,
                            'state': [{'id': st.state_id if st else None, 'name': st.state_name if st else None} for st in state if st.state_id==des.desi_stateid],
                            'lga': [{'id': lg.lga_id if lg else None, 'name': lg.lga_name if lg else None} for lg in lga if lg.lga_id==des.desi_lgaid]
                            }
                            for des in desi2],
            'customers': [{'id': cus.cust_id if cus else None,'firstname': cus.cust_fname if cus else None, 'lastname': cus.cust_lname if cus else None,
                           'email': cus.cust_email if cus else None, 'phone': cus.cust_phone if cus else None, 'address': cus.cust_address if cus else None,
                           'username':cus.cust_username if cus else None, 'gender': cus.cust_gender if cus else None, 'registerDate': cus.cust_regdate if cus else None,
                           'profilePic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{cus.cust_pic}" if cus else None, 'status': cus.cust_status if cus else None, 'access': cus.cust_access if cus else None,
                           'state': [{'id': st.state_id if st else None, 'name': st.state_name if st else None} for st in state if st.state_id==cus.cust_stateid],
                           'lga': [{'id': lg.lga_id if lg else None, 'name': lg.lga_name if lg else None} for lg in lga if lg.lga_id==cus.cust_lgaid]
                           }
                           for cus in cust2],
            "daily_active_login_time":len(active_time),
            'day_activity': len(day_data),
            'week_activity': len(week_data),
            'month_activity': len(month_data),
            'year_activity': len(year_data),
            "total_post": len(pstn),
            "total_appointment":len(appt),
            "total_payment":f"{payn:,.2f}", #f"{sum(piy.payment_amount for piy in pymt):,.2f}",
            "total_subscription": len(sublist),
            "total_report":len(srepo),
            "total_creator": len(desi),
            "total_client":len(cust),
            "total_banned_users": banned,
            "total_suspended_users": suspended,
            "total_users": len(desi) + len(cust),
            "total_admin": len(total_admin),
            "total_transaction": f"{tpayn:,.2f}", #f"{sum(tpy.tpay_amount for tpy in total_transaction):,.2f}",
            "total_revenue": f"{total_revenue:,.2f}"
        })
    else:
        spa = db.session.get(Superadmin, spadmin)
        day_data = Activitylog.query.filter(
            extract('day', Activitylog.date) == current_date.day,
            Activitylog.spadminid == spa.spadmin_id).all()
        week_data = Activitylog.query.filter(
            Activitylog.date >= week_start, Activitylog.date < week_end,
            Activitylog.spadminid == spa.spadmin_id).all()
        month_data = Activitylog.query.filter(
            Activitylog.date >= month_start, Activitylog.date < month_end,
            Activitylog.spadminid == spa.spadmin_id).all()
        year_data = Activitylog.query.filter(
            Activitylog.date >= year_start, Activitylog.date < year_end,
            Activitylog.spadminid == spa.spadmin_id).all()

        return jsonify({
            'user': {"spadmin_id":spa.spadmin_id, "firstname":spa.spadmin_fname,
                "lastname":spa.spadmin_lname, "spadmin_gender":spa.spadmin_gender if spa else None, "spadmin_phone":spa.spadmin_phone if spa else None,
                "spadmin_email":spa.spadmin_email if spa else None, "spadmin_address":spa.spadmin_address if spa else None,
                "spadmin_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/spadmin/{spa.spadmin_pic}" if spa else None,
                "spadmin_secret": spa.spadmin_secretword if spa else None},
            'posts': [{"postId":po.post_id, "postTitle":po.post_title,
                "content":po.post_body,
                "date":po.post_date, "postSuspend":po.post_suspend,
                "postDelete":po.post_delete,
                "postCreator":po.designerobj.desi_businessName,
                "image":[{"postImage":img.image_name,
                          "postImageUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"} for img in po.imagepostobj],
                } for po in pstn],
            'appointments': [{"booking_id": bk.ba_id if bk else None, 'date':bk.ba_date if bk else None, 'booking_date':bk.ba_bookingDate if bk else None, 'booking_time':bk.ba_bookingTime if bk else None,
                "collectionTime":bk.ba_collectionTime if bk else None, "collectionDate": bk.ba_collectionDate if bk else None,
                "status":bk.ba_status if bk else None,
                "collectionStatus": bk.ba_custstatus if bk else None, "paymentStatus": bk.ba_paystatus if bk else None,
                "reason": bk.ba_reason if bk else None,
                "clientName": bk.custbaobj.cust_username if bk.custbaobj else None,
                "clientCountry":bk.custbaobj.custcountry.country_name if bk.custbaobj.custcountry else None,
                "clientPhone":bk.custbaobj.cust_phone if bk.custbaobj else None, "client_firstname":bk.custbaobj.cust_fname if bk.custbaobj else None,
                "client_lastname":bk.custbaobj.cust_lname if bk.custbaobj else None,
                "creator_businessName": bk.desibaobj.desi_businessName if bk.desibaobj else None,
                "creator_country":bk.desibaobj.desicountry.country_name if bk.desibaobj and bk.desibaobj.desicountry else None,
                "creatorPhone":bk.desibaobj.desi_phone if bk.desibaobj else None, "creator_firstname":bk.desibaobj.desi_fname if bk.desibaobj else None,
                "creator_lastname":bk.desibaobj.desi_lname if bk.desibaobj else None} for bk in appt2],
            'payments': [{"paymentID":pay.payment_id if pay else None, "payment_transNo":pay.payment_transNo if pay else None,
                          "patment_transdate":pay.payment_transdate if pay else None, "payment_Amount":pay.payment_amount if pay else None,
                          "payment_status":pay.payment_status if pay else None,
                          "payment_by":pay.desipaymentobj.desi_businessName if pay.desipaymentobj else None,
                          "payment_for":pay.subpaymentobj.sub_plan if pay.subpaymentobj else None} for pay in pymt2],
            'subscriptions': [{"sub_plan":s.sub_plan if s else None, "sub_date":s.sub_date if s else None, "startdate":s.sub_startdate if s else None,
                               "enddate":s.sub_enddate if s else None, "refno":s.sub_ref if s else None, "status":s.sub_status if s else None,
                               "sub_payment_status":s.sub_paystatus if s else None, "sub_by":s.subdesiobj.desi_businessName if s else None,
                               } for s in sublist2],
            'reports': [{"report_id": r.report_id if r else None, "report_date":r.report_date if r else None, "reason":r.report_reason if r else None, "Client_reported":r.reporter if r else None,
                         "client_username":r.custreportobj.cust_username if r.custreportobj else "",
                         "creator_reported":r.desireportobj.desi_businessName if r.desireportobj else ""}
                         for r in srepo2],
            'designers': [{'designer_id': des.desi_id if des else None,'firstname': des.desi_fname if des else None,'lastname': des.desi_lname if des else None,
                           'email': des.desi_email if des else None,'phone': des.desi_phone if des else None,'address': des.desi_address if des else None,
                            'profile_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{des.desi_pic}" if des else None, 'gender':des.desi_gender if des else None,
                            "businessName":des.desi_businessName if des else None,'registerDate':des.desi_regdate if des else None,
                            'status': des.desi_status if des else None,'access': des.desi_access if des else None,
                            'state': [{'id': st.state_id if st else None, 'name': st.state_name if st else None} for st in state if st.state_id==des.desi_stateid],
                            'lga': [{'id': lg.lga_id if lg else None, 'name': lg.lga_name if lg else None} for lg in lga if lg.lga_id==des.desi_lgaid]
                            }
                            for des in desi2],
            'customers': [{'id': cus.cust_id if cus else None,'firstname': cus.cust_fname if cus else None, 'lastname': cus.cust_lname if cus else None,
                           'email': cus.cust_email if cus else None, 'phone': cus.cust_phone if cus else None, 'address': cus.cust_address if cus else None,
                           'username':cus.cust_username if cus else None, 'gender': cus.cust_gender if cus else None, 'registerDate': cus.cust_regdate if cus else None,
                           'profilePic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{cus.cust_pic}" if cus else None, 'status': cus.cust_status if cus else None, 'access': cus.cust_access if cus else None,
                           'state': [{'id': st.state_id if st else None, 'name': st.state_name if st else None} for st in state if st.state_id==cus.cust_stateid],
                           'lga': [{'id': lg.lga_id if lg else None, 'name': lg.lga_name if lg else None} for lg in lga if lg.lga_id==cus.cust_lgaid]
                           }
                           for cus in cust2],
            "daily_active_login_time":len(active_time),
            'day_activity': len(day_data),
            'week_activity': len(week_data),
            'month_activity': len(month_data),
            'year_activity': len(year_data),
            "total_post": len(pstn),
            "total_appointment":len(appt),
            "total_payment": f"{payn:,.2f}", #f"{sum(piy.payment_amount for piy in pymt):,.2f}",
            "total_subscription": len(sublist),
            "total_report":len(srepo),
            "total_creator": len(desi),
            "total_client":len(cust),
            "total_banned_users": banned,
            "total_suspended_users": suspended,            
            "total_users": len(desi) + len(cust),
            "total_admin": len(total_admin),
            "total_transaction": f"{tpayn:,.2f}", # f"{sum(tpy.tpay_amount for tpy in total_transaction):,.2f}",
            "total_revenue": f"{total_revenue:,.2f}"
        })


"""previous day activity"""
@csrf.exempt
@admin_api_bp.route('/api/activity/prev/', methods=['GET'])
@jwt_required()
def previous_day_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    last_admin_active(userid, user_type)
    current_date = datetime.now()
    previous_day = current_date - timedelta(days=1)

    if admin:
        previous_day_data = db.session.query(Activitylog).filter(
            extract('day', Activitylog.date) >= extract('day', previous_day),
            extract('day', Activitylog.date) < extract('day', current_date),
            Activitylog.adminid == adm.admin_id
        ).all()
        return jsonify({'count': previous_day_data if previous_day_data else 0}), 200

    elif spadmin:
        previous_day_data = db.session.query(Activitylog).filter(
            extract('day', Activitylog.date) >= extract('day', previous_day),
            extract('day', Activitylog.date) < extract('day', current_date),
            Activitylog.spadminid == spa.spadmin_id
        ).all()
        return jsonify({'count': previous_day_data if previous_day_data else 0}), 200

    return jsonify({'error': 'Invalid user role'}), 400


"""next day activity"""
@admin_api_bp.route('/api/activity/next', methods=['GET'])
@jwt_required()
def next_day_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    last_admin_active(userid, user_type)
    current_date = datetime.now()
    next_day = current_date + timedelta(days=1)

    if admin:
        next_day_data = db.session.query(Activitylog).filter(
            extract('day', Activitylog.date) >= extract('day', current_date),
            extract('day', Activitylog.date) < extract('day', next_day),
            Activitylog.adminid == adm.admin_id
        ).all()
    elif spadmin:
        next_day_data = db.session.query(Activitylog).filter(
            extract('day', Activitylog.date) >= extract('day', current_date),
            extract('day', Activitylog.date) < extract('day', next_day),
            Activitylog.spadminid == spa.spadmin_id
        ).all()
    else:
        next_day_data = []

    return jsonify({
        'count': len(next_day_data),
        'date_checked': current_date.strftime('%Y-%m-%d')
    })


"""previous week activity"""
@admin_api_bp.route('/api/activity/prevweek/', methods=['GET'])
@jwt_required()
def previous_week_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    last_admin_active(userid, user_type)
    current_date = datetime.now()
    previous_week = current_date - timedelta(weeks=1)
    endweek = previous_week + timedelta(days=6)

    if admin:
        previous_week_data = db.session.query(Activitylog).filter(
            Activitylog.date >= previous_week,
            Activitylog.date < endweek,
            Activitylog.adminid == adm.admin_id
        ).all()
        return jsonify({'count': len(previous_week_data)})

    elif spadmin:
        previous_week_data = db.session.query(Activitylog).filter(
            Activitylog.date >= previous_week,
            Activitylog.date < endweek,
            Activitylog.spadminid == spa.spadmin_id
        ).all()
        return jsonify({'count': len(previous_week_data)})


"""next week activity"""
@admin_api_bp.route('/api/activity/nextweek/', methods=['GET'])
@jwt_required()
def next_week_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    current_date = datetime.now()
    next_week_start = current_date + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=7)

    if admin:
        adm = db.session.get(Admin, admin)
        next_week_data = db.session.query(Activitylog).filter(
            Activitylog.date >= next_week_start,
            Activitylog.date < next_week_end,
            Activitylog.adminid == adm.admin_id
        ).all()
        return jsonify({"count": len(next_week_data)})

    elif spadmin:
        spa = db.session.get(Superadmin, spadmin)
        next_week_data = db.session.query(Activitylog).filter(
            Activitylog.date >= next_week_start,
            Activitylog.date < next_week_end,
            Activitylog.spadminid == spa.spadmin_id
        ).all()
        return jsonify({"count": len(next_week_data)})


"""previous month activity"""
@admin_api_bp.route('/api/activity/prevmonth/', methods=['GET'])
@jwt_required()
def previous_month_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    # Current date and previous month range
    current_date = datetime.now()
    month_start = datetime(current_date.year, current_date.month, 1)
    previous_month = month_start - timedelta(days=1)

    if admin:
        adm = db.session.get(Admin, admin)
        previous_month_data = db.session.query(Activitylog).filter(
            Activitylog.date >= previous_month,
            Activitylog.date < month_start,
            Activitylog.adminid == adm.admin_id
        ).all()
    elif spadmin:
        spa = db.session.get(Superadmin, spadmin)
        previous_month_data = db.session.query(Activitylog).filter(
            Activitylog.date >= previous_month,
            Activitylog.date < month_start,
            Activitylog.spadminid == spa.spadmin_id
        ).all()

    return jsonify({'count': len(previous_month_data)})


"""next week activity"""
@admin_api_bp.route('/api/activity/nextmonth/', methods=['GET'])
@jwt_required()
def next_month_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    current_date = datetime.now()
    month_start = datetime(current_date.year, current_date.month, 1)
    month_end = (month_start.replace(month=month_start.month + 1)
                 if month_start.month < 12
                 else month_start.replace(year=month_start.year + 1, month=1))

    if admin:
        adm = db.session.get(Admin, admin)
        next_month_data = db.session.query(Activitylog).filter(
            Activitylog.date >= month_start,
            Activitylog.date < month_end,
            Activitylog.adminid == adm.admin_id
        ).all()
        return jsonify({'count': len(next_month_data)})

    elif spadmin:
        spa = db.session.get(Superadmin, spadmin)
        next_month_data = db.session.query(Activitylog).filter(
            Activitylog.date >= month_start,
            Activitylog.date < month_end,
            Activitylog.spadminid == spa.spadmin_id
        ).all()
        return jsonify({'count': len(next_month_data)})

"""previous year activity"""
@admin_api_bp.route('/api/activity/prevyear/', methods=['GET'])
@jwt_required()
def previous_year_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    current_date = datetime.now()
    current_year = current_date.year
    previous_year = current_date.replace(year=current_date.year - 1)

    if admin:
        adm = db.session.get(Admin, admin)
        previous_year_data = db.session.query(Activitylog).filter(
            Activitylog.date >= previous_year,
            Activitylog.date < datetime(current_year, 1, 1),
            Activitylog.adminid == adm.admin_id
        ).all()
    elif spadmin:
        spa = db.session.get(Superadmin, spadmin)
        previous_year_data = db.session.query(Activitylog).filter(
            Activitylog.date >= previous_year,
            Activitylog.date < datetime(current_year, 1, 1),
            Activitylog.spadminid == spa.spadmin_id
        ).all()
    else:
        return jsonify({'error': 'User not recognized'}), 403

    return jsonify({'count': len(previous_year_data)}), 200


"""next year activity"""
@admin_api_bp.route('/api/activity/nextyear/', methods=['GET'])
@jwt_required()
def next_year_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    # Get current and next year
    current_date = datetime.now()
    current_year = current_date.year
    next_year_start = datetime(current_year + 1, 1, 1)
    next_year_end = datetime(current_year + 2, 1, 1)

    if admin:
        adm = db.session.get(Admin, admin)
        previous_year_data = db.session.query(Activitylog).filter(
            Activitylog.date >= next_year_start,
            Activitylog.date < next_year_end,
            Activitylog.adminid == adm.admin_id
        ).all()
    elif spadmin:
        spa = db.session.get(Superadmin, spadmin)
        previous_year_data = db.session.query(Activitylog).filter(
            Activitylog.date >= next_year_start,
            Activitylog.date < next_year_end,
            Activitylog.spadminid == spa.spadmin_id
        ).all()

    return jsonify({
        'count': len(previous_year_data),
        'status': 'success'
    })



"""Trending section"""
@admin_api_bp.route('/api/admin/trending/', methods=['GET'])
@jwt_required()
def api_admin_trending():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    today = date.today()
    results = []

    # Choose user context
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None

    # Subqueries
    subq_likes = db.session.query(Like.like_postid, func.count(Like.like_id).label('like_count')) \
        .group_by(Like.like_postid).subquery()
    subq_comments = db.session.query(Comment.com_postid, func.count(Comment.com_id).label('com_count')) \
        .group_by(Comment.com_postid).subquery()
    subq_shares = db.session.query(Share.share_postid, func.count(Share.share_id).label('share_count')) \
        .group_by(Share.share_postid).subquery()

    # Main query
    posts = db.session.query(Posting) \
        .outerjoin(subq_likes, Posting.post_id == subq_likes.c.like_postid) \
        .outerjoin(subq_comments, Posting.post_id == subq_comments.c.com_postid) \
        .outerjoin(subq_shares, Posting.post_id == subq_shares.c.share_postid) \
        .filter(extract('day', Posting.post_date) == extract('day', today),
                extract('month', Posting.post_date) == extract('month', today),
                extract('year', Posting.post_date) == extract('year', today)) \
        .order_by(desc(subq_likes.c.like_count), desc(subq_comments.c.com_count),
                  desc(subq_shares.c.share_count), desc(Posting.post_date)) \
        .limit(1000).all()

    # Format results for JSON
    for po in posts:
        like_count = db.session.query(func.count(Like.like_id)).filter(Like.like_postid == po.post_id).scalar()
        comment_count = db.session.query(func.count(Comment.com_id)).filter(Comment.com_postid == po.post_id).scalar()
        share_count = db.session.query(func.count(Share.share_id)).filter(Share.share_postid == po.post_id).scalar()

        results.append({
            "like_count": like_count if like_count else 0,
            "comment_count": comment_count if comment_count else 0,
            "share_count": share_count if share_count else 0,
            "postId":po.post_id, "postTitle":po.post_title,
            "content":po.post_body,
            "date":po.post_date, "postSuspend":po.post_suspend,
            "postDelete":po.post_delete,
            "postCreator":po.designerobj.desi_businessName,
            "image":[{"postImage":img.image_name,
                        "postImageUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"} for img in po.imagepostobj]
            # Add more post fields as needed
        })

    return jsonify({
        "success": True,
        "posts": results,
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None
    }), 200


""" post detail session """
@admin_api_bp.route('/api/adminpost/<id>/', methods=['GET'])
@jwt_required()
def api_admin_post(id):
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None

    # Fetch the post
    compost = Posting.query.filter_by(post_id=id).first()
    if not compost:
        return jsonify({'error': 'Post not found'}), 404

    # Fetch related data
    pstn = db.session.query(Posting).filter(Posting.post_id == Image.image_postid,
                                            Posting.post_id == id).first()

    comnt = db.session.query(Comment).filter(Comment.com_postid == compost.post_id)\
                                     .order_by(Comment.path.asc()).all()

    # share = db.session.query(Share).filter(Share.share_postid == compost.post_id).all()

    # likes = Like.query.filter(Like.like_postid == compost.post_id).all()

    # Convert data to dictionaries (assumes you have to_dict() methods or serialize manually)
    post_data = {"id":pstn.post_id, "title":pstn.post_title, "body":pstn.post_body, "suspend":pstn.post_suspend,
         "delete":pstn.post_delete, "image":[{"imageName":img.image_name, "imageUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"}
                                             for img in pstn.imagepostobj],
         "creator":pstn.designerobj.desi_businessName, "date":pstn.post_date.isoformat(),
         "post_comment":[
             {"com_body":com.com_body, "com_date":com.com_date.isoformat(), "com_suspend": com.com_suspend,
              "com_delete":com.com_delete, "client_com": com.comcustobj.cust_username if com.comcustobj else"",
              "creator_com": com.comdesiobj.desi_businessName if com.comdesiobj else "" }
              for com in pstn.postcomobj]} if pstn else None,
    comments_data = {'comments_reply': [{"replies":comment.com_body, "replies_id":comment.com_id,
                                         "parent":comment.parent_id, "post_id":comment.com_postid,
                                         "reply_date":comment.com_date} for comment in comnt]},

    comment_count = {"Comment_Count": len(pstn.postcomobj) if pstn else 0}
    shares_count = {"shares_Count": len(pstn.sharepostobj) if pstn else 0}
    likes_count = {"likes_Count": len(pstn.likes) if pstn else 0}

    return jsonify({
        'post': post_data,
        'comments': comments_data,
        'shares': shares_count,
        'likes': likes_count,
        'coment_count': comment_count,
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None
    }), 200


"""ban section"""
@csrf.exempt
@admin_api_bp.route('/api/ban', methods=['POST'])
@jwt_required()
def ban_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None

    data = request.get_json()
    postid = data.get('postid')
    comid = data.get('comid')
    url = request.url

    if not postid and not comid:
        return jsonify({'error': 'postid or comid is required'}), 400

    try:
        if adm:
            if postid:
                posi = Posting.query.filter_by(post_id=postid).first()
                if not posi:
                    return jsonify({'error': 'Post not found'}), 404
                posi.post_suspend = 'suspended'
                posi.post_adminid = adm.admin_id
                db.session.commit()

                actlog = Activitylog(adminid=adm.admin_id, link=url)
                db.session.add(actlog)
                db.session.commit()
                return jsonify({'message': 'Post suspended by admin'}), 200

            elif comid:
                posi = Comment.query.filter_by(com_id=comid).first()
                if not posi:
                    return jsonify({'error': 'Comment not found'}), 404
                posi.com_suspend = 'suspended'
                posi.com_adminid = adm.admin_id
                db.session.commit()

                actlog = Activitylog(adminid=adm.admin_id, link=url)
                db.session.add(actlog)
                db.session.commit()
                return jsonify({'message': 'Comment suspended by admin'}), 200

        elif spa:
            if postid:
                posi = Posting.query.filter_by(post_id=postid).first()
                if not posi:
                    return jsonify({'error': 'Post not found'}), 404
                posi.post_suspend = 'suspended'
                posi.post_spadminid = spa.spadmin_id
                db.session.commit()

                actlog = Activitylog(spadminid=spa.spadmin_id, link=url)
                db.session.add(actlog)
                db.session.commit()
                return jsonify({'message': 'Post suspended by superadmin'}), 200

            elif comid:
                posi = Comment.query.filter_by(com_id=comid).first()
                if not posi:
                    return jsonify({'error': 'Comment not found'}), 404
                posi.com_suspend = 'suspended'
                posi.com_spadminid = spa.spadmin_id
                db.session.commit()

                actlog = Activitylog(spadminid=spa.spadmin_id, link=url)
                db.session.add(actlog)
                db.session.commit()
                return jsonify({'message': 'Comment suspended by superadmin'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



"""delete section"""
@csrf.exempt
@admin_api_bp.route('/api/trash/', methods=['POST'])
@jwt_required()
def trashapi():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    postid = request.json.get('postid')
    comid = request.json.get('comid')
    url = request.url

    if not postid and not comid:
        return jsonify({'error': 'Post ID or Comment ID must be provided'}), 400

    if postid:
        posting = Posting.query.filter_by(post_id=postid).first()
        if not posting:
            return jsonify({'error': 'Post not found'}), 404
        posting.post_delete = 'deleted'

        if admin:
            posting.post_adminid = admin
            db.session.add(Activitylog(adminid=admin, link=url))
        elif spadmin:
            posting.post_spadminid = spadmin
            db.session.add(Activitylog(spadminid=spadmin, link=url))

        db.session.commit()
        return jsonify({'message': 'Post successfully deleted'}), 200

    if comid:
        comment = Comment.query.filter_by(com_id=comid).first()
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        comment.com_delete = 'deleted'

        if admin:
            comment.com_adminid = admin
            db.session.add(Activitylog(adminid=admin, link=url))
        elif spadmin:
            comment.com_spadminid = spadmin
            db.session.add(Activitylog(spadminid=spadmin, link=url))

        db.session.commit()
        return jsonify({'message': 'Comment successfully deleted'}), 200


"""All Designers """
@admin_api_bp.route('/api/admin/designers/', methods=['GET'])
@jwt_required()
def api_admin_designers():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    page = request.args.get('page', 1, type=int)
    designers_paginated = Designer.query.paginate(page=page, per_page=rows_page)

    designers_list = [
        {
            'id':desi.desi_id, 'businessName': desi.desi_businessName,       # Assuming you have a desi_id linking to the designer
            'state': desi.stateobj2.state_name if desi.stateobj2.state_name else desi.desi_state,
            'lga':desi.lgaobj2.lga_name if desi.lgaobj2.lga_name else desi.desi_city,
            "Country": desi.desicountry.country_name if desi.desicountry else None,
            "profil_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{desi.desi_pic}" if desi.desi_pic else None,
            'firstname': desi.desi_fname, 'lastname': desi.desi_lname, 'email': desi.desi_email,
            'status': desi.desi_status, 'access': desi.desi_access,
            'gender': desi.desi_gender, 'registerDate': desi.desi_regdate,
            # Add more fields as needed
        } for desi in designers_paginated.items
    ]

    response = {
        'designers': designers_list,
        'pagination': {
            'page': designers_paginated.page,
            'pages': designers_paginated.pages,
            'total': designers_paginated.total,
            'has_next': designers_paginated.has_next,
            'has_prev': designers_paginated.has_prev,
            "admin":admin if admin else None,
            "spadmin":spadmin if spadmin else None
        }
    }

    return jsonify(response)


"""All Customers """
@admin_api_bp.route('/api/admin/allcustomers/', methods=['GET'])
@jwt_required()
def api_admin_customers():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', rows_page, type=int)
    customers = Customer.query.paginate(page=page, per_page=per_page)

    customer_list = [{
        'id':cus.cust_id, 'firstname': cus.cust_fname, 'lastname': cus.cust_lname,
        'email': cus.cust_email, 'phone': cus.cust_phone,
        'address': cus.cust_address, 'username':cus.cust_username,
        'gender': cus.cust_gender, 'registerDate': cus.cust_regdate,
        'profilePic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{cus.cust_pic}" if cus.cust_pic else None, 'status': cus.cust_status,
        'access': cus.cust_access, "country": cus.custcountry.country_name if cus.custcountry else None,
        'state': cus.stateobj.state_name if cus.stateobj.state_name else cus.cust_state,
        'lga': cus.lgaobj.lga_name if cus.lgaobj.lga_name else cus.cust_city
    } for cus in customers.items]

    return jsonify({
        'customers': customer_list,
        'total': customers.total,
        'page': customers.page,
        'pages': customers.pages,
        'has_next': customers.has_next,
        'has_prev': customers.has_prev,
        "admin":admin if admin else None,
        "spadmin":spadmin if spadmin else None
    })


"""Designers Details """
@admin_api_bp.route('/api/designers/<id>/', methods=['GET'])
@jwt_required()
def api_admin_desi_detail(id):
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    desi = Designer.query.filter(Designer.desi_id == id).first()

    if not desi:
        return jsonify({'error': 'Designer not found'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', rows_page, type=int)
    ratings = Rating.query.filter_by(rat_desiid=desi.desi_id).all()
    ratin = Rating.query.filter_by(rat_desiid=desi.desi_id).paginate(page=page, per_page=per_page, error_out=False)
    total_ratings = len(ratings)
    avg_rating = round(sum(r.rat_rating for r in ratings) / total_ratings, 2) if total_ratings > 0 else None

    # Count occurrences of each rating 1–5
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        rating_counts[r.rat_rating] += 1

    # Percentages
    rating_percentages = {
        star: round((count / total_ratings) * 100, 2) if total_ratings > 0 else 0
        for star, count in rating_counts.items()
        }

    star_summary = [
        {
            "star": star,
            "count": rating_counts[star],
            "percentage": rating_percentages[star]
        }
        for star in range(1, 6)
    ]

    # userdata = Login.query.filter_by(login_desiid=desi.desi_id).order_by(desc(Login.login_date)).paginate(page=page, per_page=per_page, error_out=False)
    pport=Report.query.filter_by(report_desiid=desi.desi_id).all()
    reports = Report.query.filter_by(report_desiid=desi.desi_id).paginate(page=page, per_page=per_page, error_out=False)
    total_reports = len(pport)
    daily_logins = (db.session.query(func.count(Login.login_id))
                    .filter(func.date(Login.login_date) == date.today(),
                            Login.login_desiid==desi.desi_id).scalar())
    seven_days_ago = datetime.now() - timedelta(days=7)
    weekly_logins = (db.session.query(func.count(Login.login_id))
                     .filter(Login.login_date >= seven_days_ago,
                             Login.login_desiid == desi.desi_id).scalar())
    today = datetime.now()
    monthly_logins = (db.session.query(func.count(Login.login_id))
                      .filter(func.extract('month', Login.login_date) == today.month,
                              func.extract('year', Login.login_date) == today.year,
                              Login.login_desiid == desi.desi_id).scalar())

    # You can customize what fields you want to send
    design_data = {
        'id':desi.desi_id, 'businessName': desi.desi_businessName,       # Assuming you have a desi_id linking to the designer
        'state': desi.stateobj2.state_name if desi.stateobj2.state_name else desi.desi_state,
        'lga':desi.lgaobj2.lga_name if desi.lgaobj2.lga_name else desi.desi_city,
        "Country": desi.desicountry.country_name if desi.desicountry else None, 'address':desi.desi_address,
        "profil_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{desi.desi_pic}" if desi.desi_pic else None, 'access': desi.desi_access,
        'firstname': desi.desi_fname, 'lastname': desi.desi_lname, 'email': desi.desi_email,
        'status': desi.desi_status, 'phone_no': desi.desi_phone,
        'gender': desi.desi_gender, 'registerDate': desi.desi_regdate,
        "average_rating": avg_rating,
        "total_ratings": total_ratings,
        "rating_counts": rating_counts,
        "rating_percentages": rating_percentages,
        "star_summary": star_summary,
        "total_report": total_reports,
        "report": [{
            "report_id": rp.report_id, "report_date":rp.report_date, "reason": rp.report_reason, "reporter": rp.reporter,
            "reported_businessName": rp.desireportobj.desi_businessName, "reported_firstname": rp.desireportobj.desi_fname,
            "reported_lastname": rp.desireportobj.desi_lname
            } for rp in reports.items],
        "rating":[{
            "rating_id": rat.rat_id, "rating_date": rat.rat_date, "rating_value": rat.rat_rating,
            "rater_names": rat.custratobj.cust_fname + " " + rat.custratobj.cust_lname, "rater_username": rat.custratobj.cust_username,
            "rater_profilePic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{rat.custratobj.cust_pic}" if rat.custratobj.cust_pic else None
            } for rat in ratin.items],
        "daily_logins": daily_logins,
        "weekly_logins": weekly_logins,
        "monthly_logins": monthly_logins
        # "creator_login_details":[{
        #         "login_id":dat.login_id, "login_email":dat.login_email, "login_date":dat.login_date, "logout_date":dat.logout_date,
        #         "loggedin_user": dat.desiloginobj.desi_businessName if dat.desiloginobj else None
        #         } for dat in userdata.items]
        # Add other fields as needed
    }

    return jsonify({
        'Creator': design_data,
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None,
        "reports_has_next": reports.has_next,
        "reports_has_prev": reports.has_prev,
        "reports_pages": reports.page,
        "reports_per_page": reports.per_page,
        "rating_has_next": ratin.has_next,
        "rating_has_prev": ratin.has_prev,
        "rating_pages": ratin.page,
        "rating_per_page": ratin.per_page,
        # "userdata_has_next": userdata.has_next,
        # "userdata_has_prev": userdata.has_prev,
        # "userdata_pages": userdata.page,
        # "userdata_per_page": userdata.per_page
    })


"""Customers Details """
@admin_api_bp.route('/api/customers/<id>/', methods=['GET'])
@jwt_required()
def api_admin_cust_detail(id):
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    cus = Customer.query.filter(Customer.cust_id == id).first()

    if not cus:
        return jsonify({'error': 'Customer not found'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', rows_page, type=int)
    pport=Report.query.filter_by(report_custid=cus.cust_id).all()
    reports=Report.query.filter_by(report_custid=cus.cust_id).paginate(page=page, per_page=per_page, error_out=False)
    total_reports = len(pport)
    # userdata = Login.query.filter_by(login_custid=cus.cust_id).order_by(desc(Login.login_date)).paginate(page=page, per_page=per_page, error_out=False)
    daily_logins = (db.session.query(func.count(Login.login_id))
                    .filter(func.date(Login.login_date) == date.today(),
                            Login.login_custid==cus.cust_id).scalar())
    seven_days_ago = datetime.now() - timedelta(days=7)
    weekly_logins = (db.session.query(func.count(Login.login_id))
                     .filter(Login.login_date >= seven_days_ago,
                             Login.login_custid==cus.cust_id).scalar())
    today = datetime.now()
    monthly_logins = (db.session.query(func.count(Login.login_id))
                      .filter(func.extract('month', Login.login_date) == today.month,
                              func.extract('year', Login.login_date) == today.year,
                              Login.login_custid==cus.cust_id).scalar())

    customer_data = {
        'id':cus.cust_id, 'firstname': cus.cust_fname, 'lastname': cus.cust_lname,
        'email': cus.cust_email, 'phone': cus.cust_phone,
        'address': cus.cust_address, 'username':cus.cust_username,
        'gender': cus.cust_gender, 'registerDate': cus.cust_regdate,
        'profilePic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{cus.cust_pic}" if cus.cust_pic else None, 'status': cus.cust_status,
        'access': cus.cust_access, "country": cus.custcountry.country_name if cus.custcountry else None,
        'state': cus.stateobj.state_name if cus.stateobj.state_name else cus.cust_state,
        'lga': cus.lgaobj.lga_name if cus.lgaobj.lga_name else cus.cust_city,
        "total_report": total_reports,
        "report": [{
            "report_id": rp.report_id, "report_date":rp.report_date, "reason": rp.report_reason, "reporter": rp.reporter,
            "reported_username": rp.custreportobj.cust_username, "reported_firstname": rp.custreportobj.cust_fname,
            "reported_lastname": rp.custreportobj.cust_lname
            } for rp in reports.items],
        "daily_logins": daily_logins,
        "weekly_logins": weekly_logins,
        "monthly_logins": monthly_logins
        # "client_login_details":[{
        #         "login_id":dat.login_id, "login_email":dat.login_email, "login_date":dat.login_date, "logout_date":dat.logout_date,
        #         "loggedin_user": dat.custloginobj.cust_username if dat.custloginobj else None
        #         } for dat in userdata.items]
        # Add other relevant fields from your Customer model
    }

    return jsonify({
        'client': customer_data,
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None,
        "has_next": reports.has_next,
        "has_prev": reports.has_prev,
        # "userdata_has_next": userdata.has_next,
        # "userdata_has_prev": userdata.has_prev,
        # "userdata_pages": userdata.page,
        # "userdata_per_page": userdata.per_page,
        "pages": reports.page,
        "per_page": reports.per_page
    }), 200


"""admin and superadmin logout session"""
@csrf.exempt
@admin_api_bp.route('/api/admin/logout/', methods=['POST'])
@jwt_required()
def api_admin_logout():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    if admin:
        jti = get_jwt()["jti"]

        session.pop('admin', None)
        lo = Login.query.filter_by(login_adminid=admin, logout_date=None).first()
        if lo:
            lo.logout_date = datetime.now(timezone.utc)
            db.session.commit()
            db.session.add(TokenBlocklist(jti=jti, jti_adminid=int(admin)))
            db.session.commit()
        return jsonify({'status': 'success', 'message': 'Admin logged out successfully'}), 200

    if spadmin:
        jti = get_jwt()["jti"]

        session.pop('superadmin', None)
        lo = Login.query.filter_by(login_spadminid=spadmin, logout_date=None).first()
        if lo:
            lo.logout_date = datetime.now(timezone.utc)
            db.session.commit()
            db.session.add(TokenBlocklist(jti=jti, jti_spadminid=int(spadmin)))
            db.session.commit()
        return jsonify({'status': 'success', 'message': 'Superadmin logged out successfully'}), 200


"""Error 404 page"""
@admin_api_bp.errorhandler(404)
def page_not_found_api(error):
    admin = session.get('admin')
    spadmin = session.get('superadmin')

    if admin is None and spadmin is None:
        return jsonify({
            'success': False,
            'error': 404,
            'message': 'Page not found',
            'auth': False
        }), 404
    else:
        adm = db.session.get(Admin, admin)
        spa = db.session.get(Superadmin, spadmin)
        return jsonify({
            'success': False,
            'error': 404,
            'message': 'Page not found',
            'auth': True,
            "admin":adm.admin_id if adm else None,
            "spadmin":spa.spadmin_id if spa else None
        }), 404


"""Search section post"""
@csrf.exempt
@admin_api_bp.route('/api/adminsearch/', methods=['POST'])
@jwt_required()
def admin_search_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    data = request.get_json()
    word = data.get('search', '')
    page = request.args.get('page', 1, type=int)

    query = (Posting.query.outerjoin(Designer, Posting.post_id == Designer.desi_id)
             .filter(
                 or_(
                     Posting.post_title.ilike(f'%{word}%'),
                     Posting.post_body.ilike(f'%{word}%'),
                     Designer.desi_businessName.ilike(f'%{word}%'),
                     Designer.desi_fname.ilike(f'%{word}%'),
                     Designer.desi_lname.ilike(f'%{word}%')
                 ))
             .order_by(desc(Posting.post_id)))

    paginated = query.paginate(page=page, per_page=rows_page)

    results = []
    for post in paginated.items:
        designer = Designer.query.get(post.post_id)
        results.append({
            'post_id': post.post_id,
            'post_title': post.post_title,
            'post_body': post.post_body,
            'designer': {
                'business_name': designer.desi_businessName if designer else '',
                'firstname': designer.desi_fname if designer else '',
                'lastname': designer.desi_lname if designer else ''
            },
            "image":[{"imageName":img.image_name, "imageUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"} for img in post.imagepostobj]
        })

    return jsonify({
        'search_term': word,
        'results': results,
        'page': page,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev,
        'total_pages': paginated.pages,
        'total_results': paginated.total,
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None
    })


"""Search creator section"""
@csrf.exempt
@admin_api_bp.route('/api/admin/search_creator/', methods=['POST'])
@jwt_required()
def api_adminsearch_designer():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    word=request.json.get('search')
    # print("This is word under search post", word)
    page = request.args.get('page', 1, type=int)  # Get page number from query params

    # Perform search in Designer and Lga tables, only fetching active designers
    wordsearch = (Designer.query
             .join(Lga, Designer.desi_lgaid == Lga.lga_id)
             .join(State, Designer.desi_stateid == State.state_id)
             .join(Countries, Designer.desi_countryid == Countries.country_id)
             .join(Subscription, Designer.desi_id == Subscription.sub_desiid)
             .filter(
                 or_(
                     Designer.desi_businessName.ilike(f"%{word}%"),
                     Designer.desi_fname.ilike(f"%{word}%"),
                     Designer.desi_lname.ilike(f"%{word}%"),
                     Lga.lga_name.ilike(f"%{word}%"),
                     State.state_name.ilike(f"%{word}%"),
                     Designer.desi_state.ilike(f"%{word}%"),   # international states
                     Designer.desi_city.ilike(f"%{word}%"),   # international cities
                     Countries.country_name.ilike(f"%{word}%")
                 )
             )
             .order_by(desc(Designer.desi_id))
             .paginate(page=page, per_page=rows_page, error_out=False))
    # print(wordsearch)

    # Format search results
    search_results = [{
        'id': desi.desi_id,
        'business_name': desi.desi_businessName,
        'first_name': desi.desi_fname,
        'last_name': desi.desi_lname, "email": desi.desi_email, "gender": desi.desi_gender,
        'state': desi.stateobj2.state_name if desi.stateobj2 else None,
        'city': desi.desi_city, "status": desi.desi_status,
        'lga': desi.lgaobj2.lga_name if desi.lgaobj2 else None
    } for desi in wordsearch.items]

    if wordsearch.total==0:
        return jsonify({
            'message': 'No Creator Found',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200
    else:
        return jsonify({
            'message': 'Search completed successfully',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200


"""Search customer section"""
@csrf.exempt
@admin_api_bp.route('/api/admin/search_client/', methods=['POST'])
@jwt_required()
def api_adminsearch_customer():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    word=request.json.get('search')
    # print("This is word under search post", word)
    page = request.args.get('page', 1, type=int)  # Get page number from query params

    # Perform search in Designer and Lga tables, only fetching active designers
    wordsearch = (Customer.query
             .join(Lga, Customer.cust_lgaid == Lga.lga_id)
             .join(State, Customer.cust_stateid == State.state_id)
             .join(Countries, Customer.cust_countryid == Countries.country_id)
             .filter(
                 or_(
                     Customer.cust_username.ilike(f"%{word}%"),
                     Customer.cust_fname.ilike(f"%{word}%"),
                     Customer.cust_lname.ilike(f"%{word}%"),
                     Lga.lga_name.ilike(f"%{word}%"),
                     State.state_name.ilike(f"%{word}%"),
                     Customer.cust_state.ilike(f"%{word}%"),   # international states
                     Customer.cust_city.ilike(f"%{word}%"),   # international cities
                     Countries.country_name.ilike(f"%{word}%")
                 )
             )
             .order_by(desc(Customer.cust_id))
             .paginate(page=page, per_page=rows_page, error_out=False))
    # print(wordsearch)

    # Format search results
    search_results = [{
        'id': cust.cust_id,
        'username': cust.cust_username,
        'first_name': cust.cust_fname,
        'last_name': cust.cust_lname, "email": cust.cust_email, "gender": cust.cust_gender,
        'state': cust.stateobj.state_name if cust.stateobj else None,
        'city': cust.cust_city, "status": cust.cust_status,
        'lga': cust.lgaobj.lga_name if cust.lgaobj else None
    } for cust in wordsearch.items]

    if wordsearch.total==0:
        return jsonify({
            'message': 'No Customer Found',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200
    else:
        return jsonify({
            'message': 'Search completed successfully',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200


"""Search subscription section"""
@csrf.exempt
@admin_api_bp.route('/api/admin/search_subcription/', methods=['POST'])
@jwt_required()
def api_adminsearch_subscription():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    word=request.json.get('search')
    # print("This is word under search post", word)
    page = request.args.get('page', 1, type=int)  # Get page number from query params

    # Perform search in Designer and Lga tables, only fetching active designers
    wordsearch = (Subscription.query
             .join(Designer, Subscription.sub_desiid == Designer.desi_id)
             .filter(
                 or_(
                     Designer.desi_businessName.ilike(f"%{word}%"),
                     Designer.desi_fname.ilike(f"%{word}%"),
                     Designer.desi_lname.ilike(f"%{word}%"),
                     Subscription.sub_plan.ilike(f"%{word}%"),
                     Subscription.sub_ref.ilike(f"%{word}%"),
                     Subscription.sub_status.ilike(f"%{word}%"),
                     Subscription.sub_paystatus.ilike(f"%{word}%"),
                     Subscription.sub_date.ilike(f"%{word}%"),
                     Subscription.sub_startdate.ilike(f"%{word}%"),
                     Subscription.sub_enddate.ilike(f"%{word}%")
                 )
             )
             .order_by(desc(Subscription.sub_id))
             .paginate(page=page, per_page=rows_page, error_out=False))
    # print(wordsearch)

    # Format search results
    search_results = [{
        'creator_id': desi.subdesiobj.desi_id if desi.subdesiobj else None,
        'business_name': desi.subdesiobj.desi_businessName if desi.subdesiobj else None,
        'first_name': desi.subdesiobj.desi_fname if desi.subdesiobj else None,
        'last_name': desi.subdesiobj.desi_lname if desi.subdesiobj else None,
        "email": desi.subdesiobj.desi_email if desi.subdesiobj else None,
        "gender": desi.subdesiobj.desi_gender if desi.subdesiobj else None,
        'sub_id': desi.sub_id, 'plan': desi.sub_plan, "sub_status": desi.sub_status,
        'payment_status': desi.sub_paystatus, 'sub_date':desi.sub_date,
        'sub_start_date':desi.sub_startdate, 'sub_end_date': desi.sub_enddate
    } for desi in wordsearch.items]

    if wordsearch.total==0:
        return jsonify({
            'message': 'No Subcription Found',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200
    else:
        return jsonify({
            'message': 'Search completed successfully',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200


"""Search booking appointment section"""
@csrf.exempt
@admin_api_bp.route('/api/admin/search_booking_appointment/', methods=['POST'])
@jwt_required()
def api_adminsearch_bookappointment():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    word=request.json.get('search')
    # print("This is word under search post", word)
    page = request.args.get('page', 1, type=int)  # Get page number from query params

    # Perform search in Designer and Lga tables, only fetching active designers
    wordsearch = (Bookappointment.query
             .filter(
                 or_(
                     Bookappointment.ba_bookingDate.ilike(f"%{word}%"),
                     Bookappointment.ba_date.ilike(f"%{word}%"),
                     Bookappointment.ba_bookingTime.ilike(f"%{word}%"),
                     Bookappointment.ba_collectionDate.ilike(f"%{word}%"),
                     Bookappointment.ba_collectionTime.ilike(f"%{word}%"),
                     Bookappointment.ba_status.ilike(f"%{word}%"),
                     Bookappointment.ba_custstatus.ilike(f"%{word}%"),
                     Bookappointment.ba_paystatus.ilike(f"%{word}%"),
                     Bookappointment.ba_reason.ilike(f"%{word}%")
                 )
             )
             .order_by(desc(Bookappointment.ba_id))
             .paginate(page=page, per_page=rows_page, error_out=False))
    # print(wordsearch)

    # Format search results
    search_results = [{
        'creator_id': desi.desibaobj.desi_id if desi.desibaobj else None,
        'business_name': desi.desibaobj.desi_businessName if desi.desibaobj else None,
        'creator_firstname': desi.desibaobj.desi_fname if desi.desibaobj else None,
        'creator_lastname': desi.desibaobj.desi_lname if desi.desibaobj else None,
        'client_id': desi.custbaobj.cust_id if desi.custbaobj else None,
        'username': desi.custbaobj.cust_username if desi.custbaobj else None,
        'client_firstname': desi.custbaobj.cust_fname if desi.custbaobj else None,
        'client_lastname': desi.custbaobj.cust_lname if desi.custbaobj else None,
        'booking_id': desi.ba_id, 'date': desi.ba_date, "booking_date": desi.ba_bookingDate,
        'booking_time': desi.ba_bookingTime, 'collection_date':desi.ba_collectionDate,
        'collection_time':desi.ba_collectionTime, 'booking_status': desi.ba_status,
        'client_collection_status':desi.ba_custstatus, 'booking_paystatus': desi.ba_paystatus, 'reason': desi.ba_reason
    } for desi in wordsearch.items]

    if wordsearch.total==0:
        return jsonify({
            'message': 'No Subcription Found',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200
    else:
        return jsonify({
            'message': 'Search completed successfully',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results,
            'page': page,
            "has_next": wordsearch.has_next,
            "has_prev": wordsearch.has_prev,
            'admin':adm.admin_id if adm else None,
            'superadmin':spa.spadmin_id if spa else None
        }), 200


"""deactivate section"""
@csrf.exempt
@admin_api_bp.route('/api/deactivat/', methods=['POST'])
@jwt_required()
def deactivat_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    if request.method == "POST":
        # Get data from JSON body
        data = request.get_json()
        desi = data.get('desi_id')
        cust = data.get('cust_id')

        # Check for admin or superadmin and process the request accordingly
        if adm:
            if desi:
                if desi != "":
                    dess = Designer.query.filter_by(desi_id=desi).first()
                    if dess:
                        dess.desi_access = 'deactived'
                        dess.desi_adminid = adm.admin_id
                        db.session.commit()

                        # Log the activity
                        actlog = Activitylog(adminid=adm.admin_id, link=request.url)
                        db.session.add(actlog)
                        db.session.commit()

                        return jsonify({"message": "Designer deactivated", "status": "success",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None}), 200
                    else:
                        return jsonify({"message": "Designer not found", "status": "error",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                            }), 400
            elif cust:
                if cust != "":
                    cust = Customer.query.filter_by(cust_id=cust).first()
                    if cust:
                        cust.cust_access = 'deactived'
                        cust.cust_adminid = adm.admin_id
                        db.session.commit()

                        # Log the activity
                        actlog = Activitylog(adminid=adm.admin_id, link=request.url)
                        db.session.add(actlog)
                        db.session.commit()

                        return jsonify({"message": "Customer deactivated", "status": "success",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                        }), 200
                    else:
                        return jsonify({"message": "Customer not found", "status": "error",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                        }), 400
        elif spa:
            if desi:
                if desi != "":
                    dess = Designer.query.filter_by(desi_id=desi).first()
                    if dess:
                        dess.desi_access = 'deactived'
                        dess.desi_spadminid = spa.spadmin_id
                        db.session.commit()

                        # Log the activity
                        actlog = Activitylog(spadminid=spa.spadmin_id, link=request.url)
                        db.session.add(actlog)
                        db.session.commit()

                        return jsonify({"message": "Designer deactivated", "status": "success",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                        }), 200
                    else:
                        return jsonify({"message": "Designer not found", "status": "error",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                        }), 400
            elif cust:
                if cust != "":
                    cust = Customer.query.filter_by(cust_id=cust).first()
                    if cust:
                        cust.cust_access = 'deactived'
                        cust.cust_spadminid = spa.spadmin_id
                        db.session.commit()

                        # Log the activity
                        actlog = Activitylog(spadminid=spa.spadmin_id, link=request.url)
                        db.session.add(actlog)
                        db.session.commit()

                        return jsonify({"message": "Customer deactivated", "status": "success",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                        }), 200
                    else:
                        return jsonify({"message": "Customer not found", "status": "error",
                            "admin":adm.admin_id if adm else None,
                            "spadmin":spa.spadmin_id if spa else None
                        }), 400

    return jsonify({"message": "Invalid request", "status": "error",
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None
    }), 400


"""activate section"""
@csrf.exempt
@admin_api_bp.route('/api/activat/', methods=['POST'])
@jwt_required()
def activat_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    if request.method == "POST":
        url = request.url
        desi = request.json.get('desi_id')
        cust = request.json.get('cust_id')

        response = {
            "success": False,
            "message": "",
            "data": {}
        }

        if adm:
            if desi:
                if desi != "":
                    dess = Designer.query.filter_by(desi_id=desi).first()
                    dess.desi_access = 'actived'
                    dess.desi_adminid = adm.admin_id
                    db.session.commit()
                    actlog = Activitylog(adminid=adm.admin_id, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    response["success"] = True
                    response["message"] = 'Designer Activated'
                    response["data"] = {"desi_id": desi}
                    return jsonify(response)
            elif cust:
                if cust != "":
                    cust = Customer.query.filter_by(cust_id=cust).first()
                    cust.cust_access = 'actived'
                    cust.cust_adminid = adm.admin_id
                    db.session.commit()
                    actlog = Activitylog(adminid=adm.admin_id, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    response["success"] = True
                    response["message"] = 'Customer Activated'
                    response["data"] = {"cust_id": cust.cust_id}
                    return jsonify(response)

        elif spa:
            if desi:
                if desi != "":
                    dess = Designer.query.filter_by(desi_id=desi).first()
                    dess.desi_access = 'actived'
                    dess.desi_spadminid = spa.spadmin_id
                    db.session.commit()
                    actlog = Activitylog(spadminid=spa.spadmin_id, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    response["success"] = True
                    response["message"] = 'Designer Activated'
                    response["data"] = {"desi_id": desi}
                    return jsonify(response)
            elif cust:
                if cust != "":
                    cust = Customer.query.filter_by(cust_id=cust).first()
                    cust.cust_access = 'actived'
                    cust.cust_spadminid = spa.spadmin_id
                    db.session.commit()
                    actlog = Activitylog(spadminid=spa.spadmin_id, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    response["success"] = True
                    response["message"] = 'Customer Activated'
                    response["data"] = {"cust_id": cust.cust_id}
                    return jsonify(response)

        # If no conditions are met
        response["message"] = 'No valid user or designer found'
        return jsonify(response), 400


"""admin signup"""
@csrf.exempt
@admin_api_bp.route('/api/admin/signup/', methods=['POST'])
@jwt_required()
def admin_signup_api():
    identity = get_jwt_identity()
    user_type, spadmin = identity.split(':') if identity else (None, None)
    if user_type not in ['superadmin'] or not spadmin:
        return jsonify({'error': 'Unauthorized'}), 401
    last_admin_active(spadmin, user_type)
    # Getting form data
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    secretword = request.form.get('secretword')
    email = request.form.get('email')
    phone = request.form.get('phone')
    pwd = request.form.get('pwd')
    cpwd = request.form.get('cpwd')
    address = request.form.get('address')
    gender = request.form.get('gender')
    pic = request.files.get('pic')

    if not pic:
        return jsonify({"error": "No picture uploaded"}), 400

    original_name = pic.filename

    # print(fname, lname, secretword, email, phone, pwd, cpwd, address, gender)
    # Check if all required fields are provided
    if not all([fname, lname, secretword, email, phone, pwd, cpwd, address, gender]):
        return jsonify({"error": "One or more fields are empty"}), 400

    # Check password length
    if len(pwd) < 8:
        return jsonify({"error": "Password should be at least 8 characters long"}), 400

    # Check if passwords match
    if pwd != cpwd:
        return jsonify({"error": "Passwords do not match"}), 400

    # Check if the email is valid
    mail = email.split('@')
    if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
        return jsonify({"error": "Invalid email domain"}), 400

    # Hash the password
    hashed_password = generate_password_hash(pwd)

    # Check the image file type
    extension = os.path.splitext(original_name)
    if extension[1].lower() not in ['.jpg', '.gif', '.png']:
        return jsonify({"error": "Invalid image format"}), 400

    # Generate a random filename for the image and save it
    fn = math.ceil(random.random() * 10000000000)
    saveas = str(fn) + extension[1]
    save_path = os.path.join(current_app.config['admin'], saveas)
    pic.save(save_path)
    #pic.save(f'styleitapp/static/images/profile/admin/{saveas}')

    # Commit to the database
    admin = Admin(
        admin_fname=fname,
        admin_secretword=secretword,
        admin_lname=lname,
        admin_gender=gender,
        admin_phone=phone,
        admin_email=email,
        admin_pass=hashed_password,
        admin_address=address,
        admin_pic=saveas
    )
    db.session.add(admin)
    db.session.commit()

    # Return success response
    return jsonify({"message": "Admin signed up successfully"}), 201


"""searching for refno to approve payment"""
@csrf.exempt
@admin_api_bp.route('/api/searchref/', methods=['POST'])
@jwt_required()
def searchref_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    url=request.url
    if admin:
        nomba=request.json.get('searchref')
        if nomba != "":
            pymt=Payment.query.filter_by(payment_transNo=nomba).first()
            typmt=Transaction_payment.query.filter_by(tpay_transNo=nomba).first()
            if pymt == None and typmt==None:
                message ={"message":f"This refno {nomba} is not available"}
                return jsonify({"message":message}), 404
            else:
                if pymt:
                    msg={"payment_id":pymt.payment_id, "payment_transNo":pymt.payment_transNo,
                         "payment_transdate":str(pymt.payment_transdate), "payment_amount":pymt.payment_amount,
                         "payment_status":pymt.payment_status, "payment_desiid":pymt.payment_desiid,
                         "payment_subid":pymt.payment_subid,
                         "desipaymentobj":pymt.desipaymentobj.desi_businessName}
                    message=json.dumps(msg)
                    actlog = Activitylog(adminid=admin, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    return jsonify({"payment":msg}), 200
                elif typmt:
                    msg={"tpay_id":typmt.tpay_id, "tpay_transNo":typmt.tpay_transNo,
                         "tpay_transdate":str(typmt.tpay_transdate), "tpay_amount":typmt.tpay_amount,
                         "tpay_status":typmt.tpay_status, "tpay_creatorId":typmt.tpay_desiid,
                         "tpay_clientId":typmt.tpay_custid, "tpay_book_appointmentId":typmt.tpay_baid,
                         "creator_businessName":typmt.desitpayobj.desi_businessName,
                         "client_firstname":typmt.custtpayobj.cust_fname if typmt.custtpayobj else None, "client_lastname":typmt.custtpayobj.cust_lname if typmt.custtpayobj else None,
                         "tpay_booking_status":typmt.tpaybaobj.ba_paystatus if typmt.tpaybaobj else None, "client_booking_status":typmt.tpaybaobj.ba_custstatus if typmt.tpaybaobj else None,
                         "tpay_currencyicon":typmt.tpay_currencyicon}
                    message=json.dumps(msg)
                    actlog = Activitylog(adminid=admin, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    return jsonify({"payment":msg}), 200
        else:
            message={"message":"your refno is incorrect"}
            return jsonify({"message":message}), 400

    elif spadmin:
        nomba=request.json.get('searchref')
        if nomba != "":
            pymt=Payment.query.filter_by(payment_transNo=nomba).first()
            typmt=Transaction_payment.query.filter_by(tpay_transNo=nomba).first()
            if pymt == None and typmt==None:
                message ={"message":f"This refno {nomba} is not available"}
                return jsonify({"message":message}), 404
            else:
                if pymt:
                    msg={"payment_id":pymt.payment_id, "payment_transNo":pymt.payment_transNo,
                         "payment_transdate":str(pymt.payment_transdate), "payment_amount":pymt.payment_amount,
                         "payment_status":pymt.payment_status, "payment_desiid":pymt.payment_desiid,
                         "payment_subid":pymt.payment_subid,
                         "desipaymentobj":pymt.desipaymentobj.desi_businessName}
                    message=json.dumps(msg)
                    actlog = Activitylog(spadminid=spadmin, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    return jsonify({"payment":msg}), 200
                elif typmt:
                    msg={"tpay_id":typmt.tpay_id, "tpay_transNo":typmt.tpay_transNo,
                         "tpay_transdate":str(typmt.tpay_transdate), "tpay_amount":typmt.tpay_amount,
                         "tpay_status":typmt.tpay_status, "tpay_creatorId":typmt.tpay_desiid,
                         "tpay_clientId":typmt.tpay_custid, "tpay_book_appointmentId":typmt.tpay_baid,
                         "creator_businessName":typmt.desitpayobj.desi_businessName,
                         "client_firstname":typmt.custtpayobj.cust_fname if typmt.custtpayobj else None, "client_lastname":typmt.custtpayobj.cust_lname if typmt.custtpayobj else None,
                         "tpay_booking_status":typmt.tpaybaobj.ba_paystatus, "client_booking_status":typmt.tpaybaobj.ba_custstatus,
                         "tpay_currencyicon":typmt.tpay_currencyicon}
                    message=json.dumps(msg)
                    # print(message)
                    actlog = Activitylog(spadminid=spadmin, link=url)
                    db.session.add(actlog)
                    db.session.commit()
                    return jsonify({"payment":msg}), 200
        else:
            message={"message":"your refno is incorrect"}
            return jsonify({"message":message}), 404
    else:
        return redirect('/api/adminhome'), 401


"""approve payment"""
@admin_api_bp.route('/api/approve/<id>/', methods=['GET'])
@jwt_required()
def approve_payment_api(id):
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    linkurl = request.url

    typm = Transaction_payment.query.filter_by(tpay_transNo=id).first()
    if not typm:
        return jsonify({"error": "Transaction not found"}), 404

    desi = typm.desitpayobj.desi_id
    sendname = f"{typm.custtpayobj.cust_fname} {typm.custtpayobj.cust_lname}"
    bnk = Bank.query.filter_by(bnk_desiid=desi).first()
    bnkcode = Bankcodes.query.filter_by(name=bnk.bnk_bankname).first()
    ac = bnk.bnk_acno
    accd = bnkcode.code

    # Confirm account details
    url = f"https://api.paystack.co/bank/resolve?account_number={ac}&bank_code={accd}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {spamming}"
    }
    response = requests.get(url, headers=headers)
    res = response.json()

    if 'data' not in res:
        return jsonify({"error": "Account verification failed", "details": res}), 400

    # Create transfer recipient
    data = {
        "type": "nuban",
        "name": res['data']['account_name'],
        "account_number": res['data']['account_number'],
        "bank_code": accd,
        "currency": "NGN",
        "email": typm.desitpayobj.desi_email,
        "description": "payment for the just concluded service"
    }
    response = requests.post("https://api.paystack.co/transferrecipient", headers=headers, data=json.dumps(data))
    res2 = response.json()

    if 'data' not in res2:
        return jsonify({"error": "Transfer recipient creation failed", "details": res2}), 400

    # Create or update transfer record
    Tns = Transfer.query.filter_by(tf_tpayreference=typm.tpay_transNo).first()
    if not Tns or Tns.tf_reference is None:
        refno = int(random.random() * 10000000)
        session['refno'] = refno

        tf = Transfer(
            tf_createdAt=res2['data']['createdAt'],
            tf_updatedAt=res2['data']['updatedAt'],
            tf_reference=refno,
            tf_RecipientCode=res2['data']['recipient_code'],
            tf_receiverAcName=res2['data']['details']['account_name'],
            tf_receiverAcNo=res2['data']['details']['account_number'],
            tf_receiverbankName=res2['data']['details']['bank_name'],
            tf_receiverEmail=res2['data']['email'],
            tf_amountRemited=typm.tpay_amount - (typm.tpay_amount * 0.2),
            tf_integrationCode=res2['data']['integration'],
            tf_receiptId=res2['data']['id'],
            tf_message=res2['message'],
            tf_depositor=sendname,
            tf_tpayid=typm.tpay_id,
            tf_status='pending',
            tf_tpayreference=typm.tpay_transNo
        )
        db.session.add(tf)

        if admin:
            actlog = Activitylog(adminid=adm.admin_id, link=linkurl)
        else:
            actlog = Activitylog(spadminid=spa.spadmin_id, link=linkurl)

        db.session.add(actlog)
        db.session.commit()

    return jsonify({
        "success": True,
        "transfer_data": res2['data'],
        "message": res2.get('message', 'Transfer initiated'),
        "transaction": {
            "trans_id": typm.tpay_id,
            "trans_ref": typm.tpay_transNo,
            "amount": typm.tpay_amount
        },
        "recipient": {
            "account_name": res2['data']['details']['account_name'],
            "account_number": res2['data']['details']['account_number'],
            "bank_name": res2['data']['details']['bank_name']
        }
    }), 200


"""initiating transfer of payment"""
@csrf.exempt
@admin_api_bp.route('/api/sendfund/', methods=['POST'])
@jwt_required()
def send_fund_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    linkurl = request.url
    last_admin_active(userid, user_type)
    if not request.json or not request.json.get('refno'):
        return jsonify({"status": False, "message": "Missing reference number"}), 400

    refno = request.json.get('refno')
    tf = Transfer.query.filter_by(tf_reference=refno).first()

    if not tf:
        return jsonify({"status": False, "message": "Transfer reference not found"}), 404

    data = {
        "amount": int(float(tf.tf_amountRemited)) * 100,
        "reference": tf.tf_reference,
        "recipient": tf.tf_RecipientCode,
        "reason": tf.tf_message
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {spamming}"  # make sure `spamming` is defined somewhere
    }

    try:
        response = requests.post("https://api.paystack.co/transfer", headers=headers, data=json.dumps(data))
        rspjson = response.json()
    except Exception as e:
        return jsonify({"status": False, "message": f"Error connecting to Paystack: {str(e)}"}), 500

    # Log activity
    if admin:
        adm = db.session.get(Admin, admin)
        actlog = Activitylog(adminid=adm.admin_id, link=linkurl)
    elif spadmin:
        spa = db.session.get(Superadmin, spadmin)
        actlog = Activitylog(spadminid=spa.spadmin_id, link=linkurl)
    else:
        return jsonify({"status": False, "message": "Unauthorized"}), 401

    db.session.add(actlog)
    db.session.commit()

    if rspjson.get('status') is True:
        transfer_code = rspjson['data']["transfer_code"]
        session['transfer_code'] = transfer_code
        return jsonify({
            "status": True,
            "message": "Transfer initiated",
            "transfer_code": transfer_code
        }), 200
    else:
        return jsonify({
            "status": False,
            "message": rspjson.get("message", "Transfer failed")
        }), 400

@csrf.exempt
@admin_api_bp.route('/api/finalize_transfer', methods=['GET', 'POST'])
@jwt_required()
def finalizetransfer_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None
    last_admin_active(userid, user_type)
    if request.method == 'GET':
        transfercode = session.get('transfer_code')
        return jsonify({
            "admin":adm.admin_id if adm else None,
            "spadmin":spa.spadmin_id if spa else None,
            # "adm": adm.serialize() if adm else None,  # You must define `serialize` on your model
            # "spa": spa.serialize() if spa else None,
            "transfer_code": transfercode
        })

    if request.method == 'POST':
        data = request.json
        code = data.get('otp')
        transfercode = session.get('transfer_code')

        if not transfercode or not code:
            return jsonify({"error": "Missing OTP or transfer code"}), 400

        url = "https://api.paystack.co/transfer/finalize_transfer"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {spamming}"  # Make sure `spamming` is defined and secure
        }
        payload = {"transfer_code": transfercode, "otp": code}

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            return jsonify({
                "message": "Transfer completed. Verify in 30 minutes.",
                "status": "success",
                "paystack_response": response.json()
            }), 200
        else:
            return jsonify({
                "message": "Failed to finalize transfer",
                "status": "error",
                "paystack_response": response.json()
            }), 404


@csrf.exempt
@admin_api_bp.route('/api/verify_transfer', methods=['POST'])
@jwt_required()
def verify_transfer_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None

    data = request.get_json()
    code = data.get('otp')

    if not code:
        return jsonify({'error': 'OTP is required'}), 400

    url = f"https://api.paystack.co/transfer/verify/{code}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {spamming}"  # Make sure `spamming` is defined securely
    }

    try:
        response = requests.get(url, headers=headers)
        resoutput = response.json()
    except Exception as e:
        return jsonify({'error': 'Failed to connect to Paystack', 'details': str(e)}), 500

    if resoutput.get('status') == True:
        return jsonify({
            'message': 'Transfer Successful',
            'result': resoutput,
            # 'admin': adm.to_dict() if adm else None,
            # 'superadmin': spa.to_dict() if spa else None
        }), 200
    else:
        return jsonify({
            'message': 'Transfer Unsuccessful',
            'result': resoutput,
            "admin":adm.admin_id if adm else None,
            "spadmin":spa.spadmin_id if spa else None
            # 'admin': adm.to_dict() if adm else None,
            # 'superadmin': spa.to_dict() if spa else None
        }), 404


@csrf.exempt
@admin_api_bp.route('/api/webhookupdate/', methods=['POST'])
def webhook_api():
    if request.method == 'POST':
        ipslist = ['52.31.139.75', '52.49.173.169', '52.214.14.220']
        data = request.json
        # dat = request.json['data']
        iph = request.headers.get('X-Real-Ip')
        iph2 = request.headers.get('X-Forwarded-For')
        if iph==iph2:
            if iph in ipslist:
                payment_verification(data)
            else:
                print('wrong ips')
        else:
            print("signature/iphs is not equal")
        return jsonify({'message':'Data Received successfully'}), 200


@csrf.exempt
@admin_api_bp.route('/api/mail-notification', methods=['POST'])
@jwt_required()
def api_admin_general_mail():
    identity = get_jwt_identity()
    usertype, spadmin = identity.split(':') if identity else (None, None)
    if not spadmin or not usertype:
        return jsonify({'error': 'Unauthorized'}), 401
    last_admin_active(spadmin, usertype)
    data = request.get_json()
    subj = data.get('subject')
    bodi = data.get('body')

    if not subj or not bodi:
        return jsonify({'status': 'error', 'message': 'Subject and body are required.'}), 400

    # Collect all designer and customer emails
    recipients = [d.desi_email for d in Designer.query.all()]
    recipients += [c.cust_email for c in Customer.query.all()]
    recipients += [n.cust_email for n in Newsletter.query.all()]

    try:
        for recipient in recipients:
            msg = Message(subject=subj, recipients=[recipient])
            # Attach logo
            with current_app.open_resource('static/images/logo11.PNG') as attachment:
                msg.attach('logo11.PNG', 'application/PNG', attachment.read())
            # Render HTML content
            msg.html = render_template('admin/email_template.html', subject=subj, body=bodi)
            mail.send(msg)
        return jsonify({'status': 'success', 'message': 'Broadcast email sent successfully.'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


"""All trending post admin"""
@admin_api_bp.route('/api/admin/alltrend', methods=['GET'])
@jwt_required()
def api_admin_alltrend():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    subq_likes = (db.session.query(Like.like_postid, func.count(Like.like_id).label('like_count'))
                  .group_by(Like.like_postid).subquery())
    subq_comments = (db.session.query(Comment.com_postid, func.count(Comment.com_id).label('com_count'))
                     .group_by(Comment.com_postid).subquery())
    subq_shares = (db.session.query(Share.share_postid, func.count(Share.share_id).label('share_count'))
                   .group_by(Share.share_postid).subquery())

    page = request.args.get('page', 1, type=int)

    pstn = (db.session.query(Posting).outerjoin(subq_likes, Posting.post_id==subq_likes.c.like_postid)
            .outerjoin(subq_comments, Posting.post_id==subq_comments.c.com_postid)
            .outerjoin(subq_shares, Posting.post_id==subq_shares.c.share_postid)
            .filter(Posting.post_id==Image.image_postid)
            .order_by(desc(subq_likes.c.like_count), desc(subq_comments.c.com_count),
                      desc(subq_shares.c.share_count), desc(Posting.post_date))
            .paginate(page=page, per_page=rows_page))

    posts =[{
        "id":po.post_id,
        "title":po.post_title,
        "content":po.post_body,
        "created_at":po.post_date.isoformat(),
        "status": po.post_suspend,
        "businessname":po.designerobj.desi_businessName,
        'creator_id':po.designerobj.desi_id,
        'firstName':po.designerobj.desi_fname,
        'lastName':po.designerobj.desi_lname,
        "email": po.designerobj.desi_email,
        "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{po.designerobj.desi_pic}" if po.designerobj.desi_pic else None,
        "likes_Count": len(po.likes if po.likes else 0),
        "Comment_Count":len(po.postcomobj if po.postcomobj else 0),
        "shares_Count":len(po.sharepostobj if po.sharepostobj else 0),
        "image":[{"postImage":img.image_name,
                    "postImageUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"} for img in po.imagepostobj],
        # "comments": [{'comment_id':com.com_id, 'comment_parentId': com.parent_id, 'body':com.com_body,
        #         'client_username': com.comcustobj.cust_username if com.comcustobj and com.comcustobj.cust_username else '',
        #         'client_id': com.comcustobj.cust_id if com.comcustobj and com.comcustobj.cust_id else '',
        #         'creator_businessname': com.comdesiobj.desi_businessName if com.comdesiobj and com.comdesiobj.desi_businessName else '',
        #         'creator_id': com.comdesiobj.desi_id if com.comdesiobj and com.comdesiobj.desi_id else ''}
        #         for com in po.postcomobj],
    } for po in pstn.items]

    return jsonify({
        'posts': posts,
        'page': pstn.page,
        'pages': pstn.pages,
        'total': pstn.total,
        "has_next": pstn.has_next,
        "has_prev": pstn.has_prev,
        "admin":admin if admin else None,
        "spadmin":spadmin if spadmin else None
    })


"""All appointment admin"""
@admin_api_bp.route('/api/admin/appointments', methods=['GET'])
@jwt_required()
def get_admin_appointments():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    page = request.args.get('page', 1, type=int)
    appt_paginated = Bookappointment.query.order_by(
        Bookappointment.ba_id.desc()
    ).paginate(page=page, per_page=rows_page)

    appointments = [{
            "id": a.ba_id,
            "client_firstname": a.custbaobj.cust_fname, "client_lastname": a.custbaobj.cust_lname,
            "creator_businessName":a.desibaobj.desi_businessName,
            "booking_date": a.ba_bookingDate,
            "booking_Time":a.ba_bookingTime,
            "client_pic":f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{a.custbaobj.cust_pic}",
            "collection_date":a.ba_collectionDate,
            "collectionTime":a.ba_collectionTime,
            "status":a.ba_status
            # Add any other fields you need here
        }for a in appt_paginated.items]

    return jsonify({
        "appointments": appointments,
        "pagination": {
            "page": appt_paginated.page,
            "pages": appt_paginated.pages,
            "total": appt_paginated.total,
            "has_next": appt_paginated.has_next,
            "has_prev": appt_paginated.has_prev,
        },
        "admin": admin,
        "superadmin": spadmin,
    })


"""All payment admin"""
@admin_api_bp.route('/api/admin/payment', methods=['GET'])
@jwt_required()
def api_admin_allpment():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None

    page = request.args.get('page', 1, type=int)
    pymt_paginated = Payment.query.order_by(desc(Payment.payment_id)).paginate(page=page, per_page=rows_page)
    pymt_paginated2 = Payment.query.order_by(desc(Payment.payment_id)).limit(3).all()
    # Serialize the data for JSON response
    payments = [
        {
            'payment_id': payment.payment_id,
            "creators_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{payment.desipaymentobj.desi_pic}",
            "creators_firstname": payment.desipaymentobj.desi_fname,
            "business_businessName": payment.desipaymentobj.desi_businessName,
            'amount': payment.payment_amount,
            'date': payment.payment_transdate.strftime('%Y-%m-%d'),
            "status":payment.payment_status,
            'ref_no': payment.payment_transNo,
            # Add other fields as necessary
        }
        for payment in pymt_paginated.items
    ]

    payment = [{
            'payment_id': py.payment_id,
            "creators_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{py.desipaymentobj.desi_pic}",
            "creators_firstname": py.desipaymentobj.desi_fname,
            "business_businessName": py.desipaymentobj.desi_businessName,
            'amount': py.payment_amount,
            'date': py.payment_transdate.strftime('%Y-%m-%d'),
            "status":py.payment_status,
            'ref_no': py.payment_transNo,
        } for py in pymt_paginated2]

    return jsonify({
        'payments': payments,
        'last3payment': payment,
        'pagination': {
            'page': pymt_paginated.page,
            'pages': pymt_paginated.pages,
            'total': pymt_paginated.total,
            'has_next': pymt_paginated.has_next,
            'has_prev': pymt_paginated.has_prev,
            "admin":adm.admin_id if adm else None,
            "spadmin":spa.spadmin_id if spa else None
        }
    }), 200


"""All subscription admin"""
@admin_api_bp.route('/api/admin/subscription', methods=['GET'])
@jwt_required()
def api_admin_subscription():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin) if admin else None
    spa = db.session.get(Superadmin, spadmin) if spadmin else None

    page = request.args.get('page', 1, type=int)
    sublist = Subscription.query.order_by(desc(Subscription.sub_date)).paginate(page=page, per_page=rows_per_page)
    sublist2 = Subscription.query.order_by(desc(Subscription.sub_date)).limit(3).all()
    subscriptions_data = [{
            'id': sub.sub_id,
            'sub_refno': sub.sub_ref,
            'plan': sub.sub_plan,
            'sub_date': sub.sub_date.isoformat(),
            'sub_pay_status': sub.sub_paystatus,
            "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{sub.subdesiobj.desi_pic}",
            "creator_firstname":sub.subdesiobj.desi_fname, "creator_lastname":sub.subdesiobj.desi_lname,
            "business_name":sub.subdesiobj.desi_businessName,
            "start_date":sub.sub_startdate,
            "end_date":sub.sub_enddate,
            "sub_status":sub.sub_status
        } for sub in sublist.items]

    last3_data = [{
            'id': bub.sub_id,
            'sub_refno': bub.sub_ref,
            'plan': bub.sub_plan,
            'sub_date': bub.sub_date.isoformat(),
            'sub_pay_status': bub.sub_paystatus,
            "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{bub.subdesiobj.desi_pic}",
            "creator_firstname":bub.subdesiobj.desi_fname, "creator_lastname":bub.subdesiobj.desi_lname,
            "business_name":bub.subdesiobj.desi_businessName,
            "start_date":bub.sub_startdate,
            "end_date":bub.sub_enddate,
            "sub_status":bub.sub_status
        } for bub in sublist2]

    return jsonify({
        'subscriptions': subscriptions_data,
        'last3subscriptions': last3_data,
        'total': sublist.total,
        'pages': sublist.pages,
        'current_page': sublist.page,
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None,
        "page":sublist.page,
        "has_next":sublist.has_next,
        "has_prev":sublist.has_prev
    })


"""All report admin"""
@admin_api_bp.route('/api/admin/report', methods=['GET'])
@jwt_required()
def api_admin_report():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid
    last_admin_active(userid, user_type)
    adm = db.session.get(Admin, admin)
    spa = db.session.get(Superadmin, spadmin)

    page = request.args.get('page', 1, type=int)
    srepo_paginated = Report.query.order_by(desc(Report.report_id)).paginate(page=page, per_page=rows_per_page)

    # Serialize reports
    reports = [{
            'client_report_id': report.report_custid,
            'creator_report_id': report.report_desiid,
            'report_Date': report.report_date,
            'reason': report.report_reason,
            "client_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{report.custreportobj.cust_pic}" if report.custreportobj else "",
            "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{report.desireportobj.desi_pic}" if report.desireportobj else "",
            "creator_firstname": report.desireportobj.desi_fname if report.desireportobj else "",
            "creator_lastname": report.desireportobj.desi_lname if report.desireportobj else "",
            "creator_businessName":report.desireportobj.desi_businessName if report.desireportobj else "",
            "creator_email":report.desireportobj.desi_email if report.desireportobj else "",
            "client_lastname":report.custreportobj.cust_lname if report.custreportobj else "",
            "client_firstname":report.custreportobj.cust_fname if report.custreportobj else "",
            "client_email":report.custreportobj.cust_email if report.custreportobj else "",
            "main_reporter": report.reporter,
        }for report in srepo_paginated.items]

    response = {
        "admin":adm.admin_id if adm else None,
        "spadmin":spa.spadmin_id if spa else None,
        'reports': reports,
        'pagination': {
            'page': srepo_paginated.page,
            'pages': srepo_paginated.pages,
            'total': srepo_paginated.total,
            'has_next': srepo_paginated.has_next,
            'has_prev': srepo_paginated.has_prev
        }
    }

    return jsonify(response)


"""Activate and Deactivate admin"""
@csrf.exempt
@admin_api_bp.route('/api/admin_deactivate', methods=['POST'])
@jwt_required()
def admin_deactivate_api():
    identity = get_jwt_identity()
    usertype, spadmin = identity.split(':') if identity else (None, None)
    if not spadmin or not usertype:
        return jsonify({'error': 'Unauthorized'}), 401
    last_admin_active(spadmin, usertype)
    spa = db.session.get(Superadmin, spadmin)
    data = request.get_json()
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({'status': 'error', 'message': 'Missing admin_id'}), 400

    adm = Admin.query.filter_by(admin_id=admin_id).first()
    if not adm:
        return jsonify({'status': 'error', 'message': 'Admin not found'}), 404

    if adm.admin_status == 'active':
        adm.admin_status = 'deactive'
        status_changed_to = 'deactive'
    else:
        adm.admin_status = 'active'
        status_changed_to = 'active'

    db.session.commit()

    actlog = Activitylog(spadminid=spa.spadmin_id, link=request.url)
    db.session.add(actlog)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': f'Admin status changed to {status_changed_to}',
        'admin_id': admin_id,
        'new_status': status_changed_to
    }), 200



"""Staff activities"""
@admin_api_bp.route('/api/staffactivity', methods=['GET'])
@jwt_required()
def api_staff_activity():
    identity = get_jwt_identity()
    usertype, spadmin = identity.split(':') if identity else (None, None)

    if usertype not in ['superadmin'] or not spadmin:
        return jsonify({'error': 'Unauthorized'}), 401
    last_admin_active(spadmin, usertype)
    spa = db.session.get(Superadmin, spadmin)

    current_date = datetime.now()
    target_month = current_date.month
    target_year = current_date.year

    # result = (
    #     db.session.query(Admin, func.sum(Activitylog.adminid).label('total_activities'))
    #     .join(Activitylog)
    #     .filter(func.extract('month', Activitylog.date) == target_month,
    #             func.extract('year', Activitylog.date) == target_year)
    #     .group_by(Admin.admin_id)
    #     .order_by(func.sum(Activitylog.adminid).desc())
    #     .all()
    # )
    customer_stats = (
        db.session.query(
            Customer.cust_adminid.label("admin_id"),

            func.sum(case((Customer.cust_status == "suspended", 1), else_=0)).label("customer_suspended"),
            func.sum(case((Customer.cust_status == "banned", 1), else_=0)).label("customer_banned"),
            func.sum(case((Customer.cust_status == "deactived", 1), else_=0)).label("customer_deactivated"),
            func.sum(case((Customer.cust_status == "dormant", 1), else_=0)).label("customer_dormant"),
        )
        .group_by(Customer.cust_adminid)
        .subquery()
    )
    designer_stats = (
        db.session.query(
            Designer.desi_adminid.label("admin_id"),

            func.sum(case((Designer.desi_status == "suspended", 1), else_=0)).label("designer_suspended"),
            func.sum(case((Designer.desi_status == "banned", 1), else_=0)).label("designer_banned"),
            func.sum(case((Designer.desi_status == "deactived", 1), else_=0)).label("designer_deactivated"),
            func.sum(case((Designer.desi_status == "dormant", 1), else_=0)).label("designer_dormant"),
        )
        .group_by(Designer.desi_adminid)
        .subquery()
    )

    newdata = (
        select(
            Admin.admin_id.label("admin_id"),
            Admin.admin_fname.label("fname"),
            Admin.admin_lname.label("lname"),

            func.count(Activitylog.id).label("total_activities"),

            func.coalesce(customer_stats.c.customer_suspended, 0).label("customer_suspended"),
            func.coalesce(customer_stats.c.customer_banned, 0).label("customer_banned"),
            func.coalesce(customer_stats.c.customer_deactivated, 0).label("customer_deactivated"),
            func.coalesce(customer_stats.c.customer_dormant, 0).label("customer_dormant"),

            func.coalesce(designer_stats.c.designer_suspended, 0).label("designer_suspended"),
            func.coalesce(designer_stats.c.designer_banned, 0).label("designer_banned"),
            func.coalesce(designer_stats.c.designer_deactivated, 0).label("designer_deactivated"),
            func.coalesce(designer_stats.c.designer_dormant, 0).label("designer_dormant"),
        )
        .join(Activitylog, Activitylog.adminid == Admin.admin_id)
        .outerjoin(customer_stats, customer_stats.c.admin_id == Admin.admin_id)
        .outerjoin(designer_stats, designer_stats.c.admin_id == Admin.admin_id)
        .where(
            func.extract('month', Activitylog.date) == target_month,
            func.extract('year', Activitylog.date) == target_year
        )
        .group_by(
            Admin.admin_id,
            Admin.admin_fname,
            Admin.admin_lname,
            customer_stats.c.customer_suspended,
            customer_stats.c.customer_banned,
            customer_stats.c.customer_deactivated,
            customer_stats.c.customer_dormant,
            designer_stats.c.designer_suspended,
            designer_stats.c.designer_banned,
            designer_stats.c.designer_deactivated,
            designer_stats.c.designer_dormant,
        )
        .order_by(func.count(Activitylog.id).desc())
    )

    results = db.session.execute(newdata).mappings().all()

    data = [{
            "admin":{'admin_id': admin.admin_id,
            'admin_firstname': admin.fname,  # adjust fields as needed
            'admin_lastname': admin.lname,
            },
            'total_activities': admin.total_activities,
            "customers": {
            "suspended": admin.customer_suspended,
            "banned": admin.customer_banned,
            "deactivated": admin.customer_deactivated,
            "dormant": admin.customer_dormant,
            },
            "designers": {
                "suspended": admin.designer_suspended,
                "banned": admin.designer_banned,
                "deactivated": admin.designer_deactivated,
                "dormant": admin.designer_dormant,
            },
        } for admin in results]

    return jsonify({
        'month': target_month,
        'year': target_year,
        'result': data,
        "spadmin":spa.spadmin_id if spa else None
    })



"""Handling webhook event"""
def payment_verification(data):
    # Implement your logic to handle different webhook events
    # event_type = event_data.get('event')
    # print("payment verification data is ==", data)
    # print("this is data under data", data['data'])
    # print("this is reference number under data", data['data']['reference'])
    ref = data['data']['reference']
    # print('verification ref', ref)
    tff = Transfer.query.filter_by(tf_reference = ref).first()
    if not tff:
        return jsonify({"error": "Invalid transaction reference"}), 400
    tpa = Transaction_payment.query.filter_by(tpay_transNo = tff.tf_tpayreference).first()
    if data['event'] == 'transfer.success':
        tff.tf_status = "success"
        db.session.commit()
        tpa.tpay_status = "paid"
        db.session.commit()
        return "",200
    elif data['event'] == 'transfer.failed':
        tff.tf_status = "failed"
        db.session.commit()
        tpa.tpay_status = "failed"
        db.session.commit()
        return "",200
    elif data['event'] == 'transfer.reversed':
        tff.tf_status = "reversed"
        db.session.commit()
        tpa.tpay_status = "pending"
        db.session.commit()
        return "",200


"""refresh token"""

@csrf.exempt
@admin_api_bp.route("/api/admin/refresh", methods=["POST"])
@jwt_required(refresh=True)
def adminrefresh():
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['admin', 'superadmin'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        admin = None
        spadmin = userid

    old_jti = get_jwt()["jti"]
    if admin:
        # Blacklist old refresh token
        db.session.add(TokenBlocklist(jti=old_jti, jti_adminid=int(admin)))
        db.session.commit()

        # Issue new tokens
        new_access = create_access_token(identity=f"admin:{admin}")
        new_refresh = create_refresh_token(identity=f"admin:{admin}")

        # Update last_active_at
        last_admin_active(userid, user_type)
        access_token=new_access,
        refresh_token=new_refresh
        # Return to frontend
        return jsonify({
            "access_token":access_token,
            "refresh_token":refresh_token
        })
    if spadmin:
        # Blacklist old refresh token
        db.session.add(TokenBlocklist(jti=old_jti, jti_spadminid=int(spadmin)))
        db.session.commit()

        # Issue new tokens
        new_access = create_access_token(identity=f"superadmin:{spadmin}")
        new_refresh = create_refresh_token(identity=f"superadmin:{spadmin}")

        # Update last_active_at
        last_admin_active(userid, user_type)
        access_token=new_access,
        refresh_token=new_refresh
        # Return to frontend
        return jsonify({
            "access_token":access_token,
            "refresh_token":refresh_token
        })
    

"""Touch last active"""
def last_admin_active(id, usertype):
    userid=int(id)
    user_type=str(usertype)

    if user_type == 'admin':
        admin = userid
        spadmin = None
    else:
        spadmin = userid
        admin = None

    if admin:
        login = (
            Login.query
            .filter(Login.login_adminid == admin, Login.logout_date == None)
            .order_by(Login.login_date.desc())
            .first()
        )
        
    else:
        login = (
            Login.query.filter(Login.login_spadminid == spadmin, Login.logout_date == None)
            .order_by(Login.login_date.desc())
            .first()
        )
    
    if login:
        login.last_active_at = datetime.now()
        db.session.commit()