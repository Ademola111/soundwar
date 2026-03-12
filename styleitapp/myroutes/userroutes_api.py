import os, math, random, json, requests
from datetime import datetime, date, timedelta, timezone
from urllib.parse import quote_plus, unquote_plus
from sqlalchemy import desc, func, or_
from flask import Blueprint, current_app, request, redirect, session, jsonify, url_for
from flask_jwt_extended import create_refresh_token, decode_token, jwt_required, get_jwt_identity, create_access_token, verify_jwt_in_request, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from flask_mail import Message
# from flask_share import Share
from styleitapp import db, csrf, limiter
from styleitapp.models import (Designer, State, Customer, Posting, Image, Comment, Like,
                               Share, Bookappointment, Subscription, TokenBlocklist, Payment, Notification,
                               Report, Rating, Newsletter, Job, Transaction_payment, Bank, Bankcodes,
                               Follow, Login, Lga, Countries, States, Cities)
from styleitapp.junk import styleit, spamming
from styleitapp.mytoken import generate_activation_token, confirm_activation_code, confirm_password_reset_token
from styleitapp.mail_utils import send_customer_password_reset_email, send_email, send_email_alert, send_password_reset_email
from styleitapp.signals import (comment_signal, reply_signal, like_signal, unlike_signal,
                               subactivate_signal, free_subactivate_signal, subdeactivate_signal, payment_signal,
                               transpay_signal, share_signal, bookappointment_signal,
                               declineappointment_signal, acceptappointment_signal,
                               completetask_signal, confirmdelivery_signal, follow_signal,
                               unfollow_signal)

user_api_bp = Blueprint("user_api", __name__)
laps = "3 per second"

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


"""homepage"""
@limiter.limit(laps)
@user_api_bp.route('/api/home', methods=['GET'])
def apihome():
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        pass

    desi_loggedin = get_jwt_identity()
    logged_in = get_jwt_identity()

    # User is already logged in as designer
    if desi_loggedin:
        return jsonify({'redirect': 'api/designer/profile/'})
    # User is already logged in as customer
    elif logged_in:
        return jsonify({'redirect': 'api/customer/profile/'})
    else:
        today = date.today()
        today_str = str(today)  # Convert date to string for consistent comparison

        # Subscription logic (potential database interaction)
        subt = db.session.query(Subscription).filter(
            Subscription.sub_status == 'active',
            Subscription.sub_enddate == today_str  # Use the string representation
        ).all()

        if subt:  # Check if subt is not empty
            for su in subt:
                su.sub_status = 'deactive'
                db.session.commit()

                # Assuming subdeactivate_signal and other email-related components are properly set up
                commenter_email = su.subdesiobj.desi_email
                custom = su.subdesiobj.desi_businessName
                recipients = {"custom": custom}
                subdeactivate_signal.send(current_app, comment=su, post_author_email=commenter_email, recipients=recipients)

        # Prepare data for the response
        des=db.session.get(Designer, desi_loggedin) if desi_loggedin else None
        cus=db.session.get(Customer, logged_in) if logged_in else None

        # Return JSON data instead of rendering a template
        return jsonify({
            'user_type': 'guest',  # Or 'customer', 'designer' based on login status
            'customer': cus.serialize() if cus else None, # Assuming you have a serialize method
            'designer': des.serialize() if des else None, # Assuming you have a serialize method
            'subscription_updates': len(subt) if subt else 0 # Number of subscriptions updated
        })


"""login"""
@limiter.limit(laps)
@user_api_bp.route('/api/login/')
def login_api():
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        pass

    desi_loggedin = get_jwt_identity()
    logged_in = get_jwt_identity()

    customer = None
    designer = None

    if logged_in:
        customer = db.session.get(Customer, logged_in)
        if customer:
            customer_data = {
                'id': customer.cust_id,
                'username': customer.cust_username,
                'email': customer.cust_email  # Add other relevant fields
            }
        else:
            customer_data = None  # Or handle the case where customer is not found
    else:
        customer_data = None

    if desi_loggedin:
        designer = db.session.get(Designer, desi_loggedin)
        if designer:
            designer_data = {
                'id': designer.desi_id,
                'username': designer.desi_businessName,
                'email': designer.desi_email  # Add other relevant fields
            }
        else:
             designer_data = None # Or handle the case where designer is not found
    else:
        designer_data = None

    return jsonify({
        'customer': customer_data,
        'designer': designer_data
    })


""" loading local govt area using ajax"""
@limiter.limit(laps)
@user_api_bp.route('/api/lga/<int:state_id>', methods=['GET'])
def get_lgas_by_state(state_id):
    try:
        # querying lga table.  Using parameterized query to prevent SQL injection
        lg = db.session.execute(db.text("SELECT lga_id, lga_name FROM lga WHERE lga_stateid = :state_id"), {'state_id': state_id})
        results = lg.fetchmany(20)  # Consider pagination for large datasets

        lgas = []
        for lga_id, lga_name in results:
            lgas.append({'id': lga_id, 'name': lga_name})
        return jsonify(lgas)

    except Exception as e:
        # Log the error for debugging purposes
        # print(f"Error fetching LGAs: {e}")
        return jsonify({'error': 'Failed to retrieve LGAs'}), 500  # Return error status code


"""Country Check"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/countrycheck', methods=['POST'])
def apicountrycheck():
    countryid = request.form.get('countryid')
    countryid = request.json.get('countryid')
    cn = Countries.query.filter_by(country_id=countryid).first()
    if cn:
        msg = cn.country_name
        return jsonify({"country_name": msg})
    else:
        return jsonify({"error": "Country not found"}), 404


"""Post section"""
def get_posts():
    today = datetime.now().date()

    # Count likes, comments, shares for each post
    query = (
        db.session.query(Posting)
    .outerjoin(Like, Like.like_postid == Posting.post_id)
    .outerjoin(Comment, Comment.com_postid == Posting.post_id)
    .outerjoin(Share, Share.share_postid == Posting.post_id)
    .options(
        db.joinedload(Posting.likes),
        db.joinedload(Posting.imagepostobj),
        db.joinedload(Posting.designerobj),
        db.joinedload(Posting.postcomobj).joinedload(Comment.comcustobj)
    )
    .filter(Posting.post_delete == 'not deleted')
    .group_by(Posting.post_id)
    .order_by(
        (func.date(Posting.post_date) == today).desc(),
        Posting.post_date.desc()
    )
    )

    return query

"""Trending Section"""
@limiter.limit(laps)
@user_api_bp.route('/api/trending', methods=['GET'])
@jwt_required()
def trending_api():
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    cus = None
    des = None
    if logged_in:
        cus = db.session.get(Customer, logged_in)
    if desi_loggedin:
        des = db.session.get(Designer, desi_loggedin)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = get_posts()
    paginated_posts = query.paginate(page=page, per_page=per_page, error_out=False)
    last_active(userid, user_type)
    if cus:
        follow = Follow.query.filter_by(follow_custid=cus.cust_id).all()
    else:
        follow = []

    # Fetch notifications
    if desi_loggedin:
        noti = Notification.query.filter(Notification.notify_read == 'unread',
                                         Notification.notify_desiid == desi_loggedin).all()
    elif logged_in:
        #  Refactor this long query for better readability and maintainability.  Consider using separate queries.
        noti = Notification.query.filter(
            (Notification.notify_postid.isnot(None)) |  # Check if not None before using .isnot()
            (Notification.notify_likeid.isnot(None)) |
            (Notification.notify_baid.isnot(None)) |
            (Notification.notify_comid.isnot(None)) |
            (Notification.notify_paymentid.isnot(None)) |
            (Notification.notify_shareid.isnot(None)) |
            (Notification.notify_subid.isnot(None)),
            Notification.notify_read == 'unread',
            Notification.notify_custid == cus.cust_id if cus else None  #Handle case where cus is None
        ).all()
    else:
        noti = [] # Handle the case where neither designer nor customer is logged in

    posts = [
        {
            'notification':[{'noteid':nt.notify_id if nt.notify_id else None,
                             'noti_postid':nt.notify_postid if nt.notify_postid else None,
                             'noti_message':nt.notify_read if nt.notify_read else None,
                             'noti_date': nt.notify_date if nt.notify_date else None,
                             'noti_clientid':nt.notify_custid if nt.notify_custid else None, 
                             'noti_likeid':nt.notify_likeid if nt.notify_likeid else None, 
                             'noti_commentid':nt.notify_comid if nt.notify_comid else None, 
                             'noti_shareid':nt.notify_shareid if nt.notify_shareid else None, 
                             'noti_bookappointmentid':nt.notify_baid if nt.notify_baid else None, 
                             'noti_transaction_paymentid':nt.notify_tpayid if nt.notify_tpayid else None, 
                             'noti_transaction_payment_status':nt.notifytpayobj.tpay_status if nt.notifytpayobj else None, 
                             'noti_creatorid':nt.notify_desiid if nt.notify_desiid else None, 
                             'noti_creator_firstname':nt.notifydesiobj.desi_fname if nt.notifydesiobj else None, 
                             'noti_client_firstname':nt.notifycustobj.cust_fname if nt.notifycustobj else None, 
                             'noti_subscriptionid':nt.notify_subid if nt.notify_subid else None, 
                             'noti_subplan':nt.notifysubobj.sub_plan if nt.notifysubobj else None, 
                             'noti_sub_status':nt.notifysubobj.sub_status if nt.notifysubobj else None, 
                             'noti_paymentid':nt.notify_paymentid if nt.notify_paymentid else None, 
                             'noti_payment_status':nt.notifypayobj.payment_status if nt.notifypayobj else None } for nt in noti],
            'follows': [{'follow_id':f.follow_id if f.follow_id else None, 'followed_desiid':f.follow_desiid if f.follow_desiid else None,
                    'follower_custid':f.follow_custid if f.follow_custid else None} for f in (follow or [])],
            "id": posti.post_id,
            "title": posti.post_title,
            "content": posti.post_body,
            "created_at": posti.post_date.isoformat(),
            "status": posti.post_suspend,
            "delete": posti.post_delete,
            "likes_Count": len(posti.likes),
            "client_id_likes": [lke.like_custid if lke.like_custid else None for lke in posti.likes],
            "creator_id_likes": [lke.like_desiid if lke.like_desiid else None for lke in posti.likes],
            "shares_Count": len(posti.sharepostobj),
            "img": [{'img_id':img.image_id, 'img_name':img.image_name,
                     'url':f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}" } for img in posti.imagepostobj],
            "creator": {'creator_id':posti.designerobj.desi_id,
                        'firstName':posti.designerobj.desi_fname,
                        'lastName':posti.designerobj.desi_lname,
                        "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{posti.designerobj.desi_pic}" if posti.designerobj.desi_pic else None,
                        'businessname':posti.designerobj.desi_businessName},
            "comments": [{'comment_id':com.com_id, 'comment_parentId': com.parent_id, 'body':com.com_body,
                          'client_username': com.comcustobj.cust_username if com.comcustobj and com.comcustobj.cust_username else '',
                          'client_id': com.comcustobj.cust_id if com.comcustobj and com.comcustobj.cust_id else '',
                          'creator_businessname': com.comdesiobj.desi_businessName if com.comdesiobj and com.comdesiobj.desi_businessName else '',
                          'creator_id': com.comdesiobj.desi_id if com.comdesiobj and com.comdesiobj.desi_id else ''}
                          for com in posti.postcomobj],
            "Comment_Count": len(posti.postcomobj)
        } for posti in paginated_posts.items

    ]

    return jsonify({
        "posts": posts,
        "page": page,
        "per_page": per_page,
        "total_pages": paginated_posts.pages,
        "has_next": paginated_posts.has_next,
        "client":cus.cust_id if cus else None,
        "creator": des.desi_id if des else None
    })


""" comment tree building"""
def build_comment_tree(comments):
    comment_map = {}
    tree = []

    # First pass: serialize
    for com in comments:
        comment_map[com.com_id] = {
            "com_id": com.com_id,
            "body": com.com_body,
            "replies_id": com.com_id,
            "parent": com.parent_id,
            'path': com.path,
            "post_id": com.com_postid,
            "reply_date": com.com_date.isoformat(),
            "level": com.path.count(".") if com.path else None,  # nesting level
            # "client_com": com.comcustobj.cust_username if com.comcustobj else "",
            # "creator_com": com.comdesiobj.desi_businessName if com.comdesiobj else "",
            'client_username': com.comcustobj.cust_username if com.comcustobj and com.comcustobj.cust_username else '',
            'client_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{com.comcustobj.cust_pic}" if com.comcustobj and com.comcustobj.cust_pic else None,
            'client_id': com.comcustobj.cust_id if com.comcustobj and com.comcustobj.cust_id else '',
            'creator_businessname': com.comdesiobj.desi_businessName if com.comdesiobj and com.comdesiobj.desi_businessName else '',
            'creator_id': com.comdesiobj.desi_id if com.comdesiobj and com.comdesiobj.desi_id else '',
            'creator_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{com.comdesiobj.desi_pic}" if com.comdesiobj and com.comdesiobj.desi_pic else None,
            "children": []
        }

    # Second pass: build hierarchy
    for com in comment_map.values():
        if com["parent"]:
            parent = comment_map.get(com["parent"])
            if parent:
                parent["children"].append(com)
        else:
            tree.append(com)
        print("this is tree output",tree)
    return tree


def sort_tree_desc(nodes):
    """
    Sorts comments and their children by date DESC
    WITHOUT breaking parent-child relationships
    """
    nodes.sort(key=lambda x: x["reply_date"], reverse=True)
    for node in nodes:
        if node["children"]:
            sort_tree_desc(node["children"])
            

""" post detail session """
@limiter.limit(laps)
@user_api_bp.route('/api/post/<int:id>/', methods=['GET'])
@jwt_required()
def get_post_data(id):
    """
    API endpoint to retrieve post data by ID.
    Returns JSON data.
    """
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    try:
        page = request.args.get('page', 1, type=int)
        per_page =10
        # Fetch post
        pstn = Posting.query.filter_by(post_id=id).first_or_404()
        root_comments = Comment.query\
            .filter(Comment.com_postid == pstn.post_id, 
                    Comment.parent_id.is_(None))\
                        .order_by(Comment.com_date.desc())\
                            .paginate(page=page, 
                                      per_page=per_page,
                                      error_out=False)
        
        root_ids = [c.com_id for c in root_comments.items]

        """newly added code to fetch all comments with paths starting with root paths"""
        # root_ids = [c.path for c in root_comments.items]
       
        # conditions = [print("this is root path", root_path) for root_path in root_ids]

        # conditions = [Comment.path.startswith(root_path) for root_path in root_ids]
        # print("this is conditions", conditions)
        # comnt = Comment.query.filter(
        #     Comment.com_postid == pstn.post_id, or_(*conditions)
        #     ).order_by(Comment.path.asc()).all()
        comnt = Comment.query.filter(
            Comment.com_postid == pstn.post_id
            ).order_by(Comment.path.asc()).all()

        # comnti = Comment.query.filter(Comment.com_postid == pstn.post_id)
        # if conditions:
        #     comnt = comnti.filter(or_(*conditions))
        # comnt = comnti.order_by(Comment.path.asc()).all()
        
        # # Fetch comments (ordered by materialized path)
        # comnt = Comment.query\
        #     .filter(Comment.com_postid == pstn.post_id)\
        #     .order_by(Comment.path.asc())\
        #     .all()

        # Build nested comments
        paginate_tree = build_comment_tree(comnt)
        comments_tree = [node for node in paginate_tree if node["com_id"] in root_ids]
        print("this is build nested comment", comments_tree)

        sort_tree_desc(comments_tree)

        # Shares & Likes
        share = Share.query.filter_by(share_postid=pstn.post_id).all()
        likes = Like.query.filter_by(like_postid=pstn.post_id).all()

        # Logged-in users
        des = db.session.get(Designer, desi_loggedin) if desi_loggedin else None
        cus = db.session.get(Customer, logged_in) if logged_in else None
        if cus:
            follow = Follow.query.filter_by(follow_custid=cus.cust_id).all()
        else:
            follow = []
        # Notifications
        if desi_loggedin:
            noti = Notification.query.filter(
                Notification.notify_read == 'unread',
                Notification.notify_desiid == desi_loggedin
            ).all()

        elif logged_in:
            noti = Notification.query.filter(
                Notification.notify_read == 'unread',
                Notification.notify_custid == cus.cust_id,
                (
                    (Notification.notify_postid != None) |
                    (Notification.notify_likeid != None) |
                    (Notification.notify_baid != None) |
                    (Notification.notify_comid != None) |
                    (Notification.notify_paymentid != None) |
                    (Notification.notify_shareid != None) |
                    (Notification.notify_subid != None)
                )
            ).all()
        else:
            noti = []

        # Final response (SAME KEYS)
        post_data = {
            'post': {
                'post': {
                    "title": pstn.post_title,
                    "body": pstn.post_body,
                    "suspend": pstn.post_suspend,
                    "delete": pstn.post_delete,
                    "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{pstn.designerobj.desi_pic}" if pstn.designerobj.desi_pic else None,
                    "image": [
                        {
                            "imageName": img.image_name,
                            "imageUrl": f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}"
                        }
                        for img in pstn.imagepostobj
                    ],
                    'id':pstn.post_id,
                    'follows': [{'follow_id':f.follow_id if f.follow_id else None, 'followed_desiid':f.follow_desiid if f.follow_desiid else None,
                    'follower_custid':f.follow_custid if f.follow_custid else None} for f in (follow or [])],
                    "client_id_likes": [lke.like_custid if lke.like_custid else None for lke in pstn.likes],
                    "creator_id_likes": [lke.like_desiid if lke.like_desiid else None for lke in pstn.likes],
                    "creator": pstn.designerobj.desi_businessName,
                    "creator_id": pstn.designerobj.desi_id,
                    "date": pstn.post_date.isoformat(),
                    # "post_comment": [
                    #     {
                    #         "com_body": com.com_body,
                    #         "com_date": com.com_date.isoformat(),
                    #         "com_suspend": com.com_suspend,
                    #         "com_delete": com.com_delete,
                    #         "client_com": com.comcustobj.cust_username if com.comcustobj else "",
                    #         "creator_com": com.comdesiobj.desi_businessName if com.comdesiobj else ""
                    #     }
                    #     for com in pstn.postcomobj
                    # ]
                },

                #SAME KEY, NOW NESTED
                'comments_reply': comments_tree,

                "Comment_Count": len(comnt),
                "likes_Count": len(likes),
                "shares_Count": len(share)
            },

            'user': {
                'designer': des.desi_id if des else None,
                'customer': cus.cust_id if cus else None
            },

            'notification':[{'noteid':nt.notify_id if nt.notify_id else None,
                             'noti_postid':nt.notify_postid if nt.notify_postid else None,
                             'noti_message':nt.notify_read if nt.notify_read else None,
                             'noti_date': nt.notify_date if nt.notify_date else None,
                             'noti_clientid':nt.notify_custid if nt.notify_custid else None, 
                             'noti_likeid':nt.notify_likeid if nt.notify_likeid else None, 
                             'noti_commentid':nt.notify_comid if nt.notify_comid else None, 
                             'noti_shareid':nt.notify_shareid if nt.notify_shareid else None, 
                             'noti_bookappointmentid':nt.notify_baid if nt.notify_baid else None, 
                             'noti_transaction_paymentid':nt.notify_tpayid if nt.notify_tpayid else None, 
                             'noti_transaction_payment_status':nt.notifytpayobj.tpay_status if nt.notifytpayobj else None, 
                             'noti_creatorid':nt.notify_desiid if nt.notify_desiid else None, 
                             'noti_creator_firstname':nt.notifydesiobj.desi_fname if nt.notifydesiobj else None, 
                             'noti_client_firstname':nt.notifycustobj.cust_fname if nt.notifycustobj else None, 
                             'noti_subscriptionid':nt.notify_subid if nt.notify_subid else None, 
                             'noti_subplan':nt.notifysubobj.sub_plan if nt.notifysubobj else None, 
                             'noti_sub_status':nt.notifysubobj.sub_status if nt.notifysubobj else None, 
                             'noti_paymentid':nt.notify_paymentid if nt.notify_paymentid else None, 
                             'noti_payment_status':nt.notifypayobj.payment_status if nt.notifypayobj else None } for nt in noti],
        }

        return jsonify({"post":post_data,
                        "page": root_comments.page,
                        "per_page": root_comments.per_page,
                        "total_pages": root_comments.pages,
                        "total_items": root_comments.total,
                        "has_next": root_comments.has_next,
                        "has_prev": root_comments.has_prev
                        }), 200

    except NotFound:
        return jsonify({"error": "Post not found"}), 404

    except Exception as e:
        # print(e)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


"""post notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/posti/<id>/', methods=['PUT'])
@jwt_required()
def notepost_api(id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    des = db.session.get(Designer, desi_loggedin)
    cus = db.session.get(Customer, logged_in)
    last_active(userid, user_type)
    if desi_loggedin:
        notif = db.session.query(Notification).filter(Notification.notify_postid==id,
                                                      Notification.notify_desiid==des.desi_id,
                                                      Notification.notify_read=='unread').first()
        if notif:
            notif.notify_read='read'
            db.session.commit()
            return jsonify({'message': 'Notification updated successfully',
                            'redirect_url': f'/api/post/{id}/'}), 200
        else:
            return jsonify({'message': 'Notification not found'}), 404
    elif logged_in:
        notif = db.session.query(Notification).filter(Notification.notify_postid==id,
                                                      Notification.notify_custid==cus.cust_id,
                                                      Notification.notify_read=='unread').first()
        if notif:
            notif.notify_read='read'
            db.session.commit()
            return jsonify({'message': 'Notification updated successfully',
                            'redirect_url': f'/api/post/{id}/'}), 200
        else:
            return jsonify({'message': 'Notification not found'}), 404
    else:
        return jsonify({'message': 'Unauthorized'}), 401


"""Like notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/postlike/<id>/', methods=['PUT'])
@jwt_required()
def notelike_api(id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    if desi_loggedin:
        des = db.session.get(Designer, desi_loggedin)
        if not des:
            return jsonify({'error': 'Designer not found'}), 404

        lk = Like.query.filter(Like.like_id == id, Like.like_desiid == des.desi_id).first()
        if not lk:
            return jsonify({'error': 'Like not found'}), 404

        notif = db.session.query(Notification).filter(
            Notification.notify_likeid == id,
            Notification.notify_desiid == des.desi_id,
            Notification.notify_read == 'unread'
        ).first()

    elif logged_in:
        cus = db.session.get(Customer, logged_in)
        if not cus:
            return jsonify({'error': 'Customer not found'}), 404

        lk = Like.query.filter(Like.like_id == id, Like.like_custid == cus.cust_id).first()
        if not lk:
            return jsonify({'error': 'Like not found'}), 404

        notif = db.session.query(Notification).filter(
            Notification.notify_likeid == id,
            Notification.notify_custid == cus.cust_id,
            Notification.notify_read == 'unread'
        ).first()

    if not notif:
        return jsonify({'error': 'Notification not found'}), 404

    notif.notify_read = 'read'
    db.session.commit()
    posid = lk.like_postid
    return jsonify({'message': "notification updted successfully", "postid":posid}), 200


"""Reply notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/postreply/<id>/', methods=['PUT'])
@jwt_required()
def apinotereply(id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    if desi_loggedin:
        des=db.session.get(Designer, desi_loggedin)
        if not des:
             return jsonify({'message': 'Designer not found'}), 404
        lk=Comment.query.filter(Comment.com_id==id, Comment.com_desiid==des.desi_id).first()
        if not lk:
            return jsonify({'message': 'Comment not found'}), 404

        posid=lk.com_postid
        notif = db.session.query(Notification).filter(Notification.notify_comid==id,
                                                      Notification.notify_desiid==des.desi_id,
                                                      Notification.notify_read=='unread').first()
        if not notif:
            return jsonify({'message': 'Notification not found'}), 404

        notif.notify_read='read'
        db.session.commit()
        return jsonify({'message': 'Notification updated', 'post_id': posid}), 200

    elif logged_in:
        cus = db.session.get(Customer, logged_in)
        if not cus:
            return jsonify({'message': 'Customer not found'}), 404

        lk=Comment.query.filter(Comment.com_id==id, Comment.com_custid==cus.cust_id).first()
        if not lk:
            return jsonify({'message': 'Comment not found'}), 404

        posid=lk.com_postid
        notif = db.session.query(Notification).filter(Notification.notify_comid==id,
                                                      Notification.notify_custid==cus.cust_id,
                                                      Notification.notify_read=='unread').first()
        if not notif:
            return jsonify({'message': 'Notification not found'}), 404

        notif.notify_read='read'
        db.session.commit()
        return jsonify({'message': 'Notification updated'}), 200


"""share notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/postshare/<id>/', methods=['PUT'])
@jwt_required()
def noteshare_api(id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    if desi_loggedin:
        des = db.session.get(Designer, desi_loggedin)
        if not des:
            return jsonify({'error': 'Designer not found'}), 404

        lk = Share.query.filter(Share.share_id == id, Share.share_desiid == des.desi_id).first()
        if not lk:
            return jsonify({'error': 'Share not found for this designer'}), 404

        posid = lk.share_postid
        notif = Notification.query.filter(Notification.notify_shareid == id,
                                           Notification.notify_desiid == des.desi_id,
                                           Notification.notify_read == 'unread').first()
        if notif:
            notif.notify_read = 'read'
            db.session.commit()
        return jsonify({'redirect_url': f'/api/post/{posid}/'}), 200

    elif logged_in:
        cus = db.session.get(Customer, logged_in)
        if not cus:
            return jsonify({'error': 'Customer not found'}), 404

        lk = Share.query.filter(Share.share_id == id, Share.share_custid == cus.cust_id).first()
        if not lk:
            return jsonify({'error': 'Share not found for this customer'}), 404

        posid = lk.share_postid
        notif = Notification.query.filter(Notification.notify_shareid == id,
                                           Notification.notify_custid == cus.cust_id,
                                           Notification.notify_read == 'unread').first()
        if not notif:
            notif.notify_read = 'read'
            db.session.commit()
        return jsonify({'redirect_url': f'/api/post/{posid}/'}), 200
    else:
        return jsonify({'error': 'User not logged in'}), 401


"""bookappointment notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/bookapp/<id>/', methods=['PUT'])
@jwt_required()
def notebookapp_api(id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    if logged_in:
        cus = db.session.get(Customer, logged_in) # Use session value directly
        if not cus:
            return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

        notif = Notification.query.filter_by(notify_baid=id,
                                              notify_custid=cus.cust_id,
                                              notify_read='unread').first()

        if not notif:
            return jsonify({'status': 'error', 'message': 'Notification not found'}), 404

        notif.notify_read = 'read'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Notification read'})

    elif desi_loggedin:
        des = db.session.get(Designer, desi_loggedin) # Use session value directly
        if not des:
             return jsonify({'status': 'error', 'message': 'Designer not found'}), 404

        notif = Notification.query.filter_by(notify_baid=id,
                                              notify_desiid=des.desi_id,
                                              notify_read='unread').first()

        if not notif:
            return jsonify({'status': 'error', 'message': 'Notification not found'}), 404

        notif.notify_read = 'read'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Notification read'})
    else:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401


"""subscription notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/notesub/<id>/', methods=['PUT'])  # Specify the method
@jwt_required()
def notesub_api(id):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not desi_loggedin:
        return jsonify({'message': 'Unauthorized'}), 401  # Unauthorized
    if user_type != 'designer':
        return jsonify({'message': 'Notification not found'}), 404
    des = db.session.get(Designer, desi_loggedin)
    if not des:
        return jsonify({'message': 'Designer not found'}), 404
    last_active(desi_loggedin, user_type)
    notif = db.session.query(Notification).filter(
        Notification.notify_subid == id,
        Notification.notify_desiid == des.desi_id,
        Notification.notify_read == 'unread'
    ).first()

    if not notif:
        return jsonify({'message': 'Notification not found'}), 404

    notif.notify_read = 'read'
    db.session.commit()

    return jsonify({'message': 'Notification updated successfully'}), 200  # OK


"""payment notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/notepay/<id>/', methods=['PUT'])  # Specify the method
@jwt_required()
def notepay_api(id):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not desi_loggedin:
        return jsonify({'message': 'Unauthorized'}), 401  # Unauthorized
    if user_type != 'designer':
        return jsonify({'message': 'Notification not found'}), 404
    des = db.session.get(Designer, desi_loggedin)
    if not des:
        return jsonify({'message': 'Designer not found'}), 404
    last_active(desi_loggedin, user_type)
    notif = db.session.query(Notification).filter(
        Notification.notify_paymentid == id,
        Notification.notify_desiid == desi_loggedin,
        Notification.notify_read == 'unread'
    ).first()

    if not notif:
        return jsonify({'message': 'Notification not found'}), 404  # Not Found

    notif.notify_read = 'read'
    db.session.commit()

    return jsonify({'message': 'Notification updated successfully'}), 200  # OK


"""transaction payment notification"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/notetpay/<id>/', methods=['PUT'])
@jwt_required()
def notetpay_api(id):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not logged_in:
        return jsonify({'message': 'Unauthorized'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Notification not found'}), 404
    cus = db.session.get(Customer, logged_in)
    if not cus:
        return jsonify({'message': 'Customer not found'}), 404
    last_active(logged_in, user_type)
    notif = db.session.query(Notification).filter(
        Notification.notify_tpayid == id,
        Notification.notify_custid == logged_in,
        Notification.notify_read == 'unread'
    ).first()
    if not notif:
        return jsonify({'message': 'Notification not found'}), 404
    notif.notify_read = 'read'
    db.session.commit()
    return jsonify({'message': 'Notification updated successfully'}), 200



"""All Designers """
@limiter.limit(laps)
@user_api_bp.route('/api/designers', methods=['GET'])
@jwt_required()
def get_designers():
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int) # Allow per_page to be configurable

    design_pagination = Subscription.query.filter(Subscription.sub_status == 'active')\
        .paginate(page=page, per_page=per_page)
    designers_data = []
    for sub in design_pagination.items:
        # Fetch all ratings for this designer
        ratings = Rating.query.filter_by(rat_desiid=sub.subdesiobj.desi_id).all()
        total_ratings = len(ratings)
        avg_rating = round(sum(r.rat_rating for r in ratings) / total_ratings, 2) if total_ratings > 0 else None

        # Build designer data
        designers_data.append({
            "creator_id": sub.subdesiobj.desi_id,
            "fname": sub.subdesiobj.desi_fname,
            "lname": sub.subdesiobj.desi_lname,
            "bio": sub.subdesiobj.desi_bio,
            "desi_about":sub.subdesiobj.desi_about,
            "creator": sub.subdesiobj.desi_businessName,
            "state": sub.subdesiobj.stateobj2.state_name
                    if sub.subdesiobj.stateobj2.state_name else sub.subdesiobj.desi_state,
            "lga": sub.subdesiobj.lgaobj2.lga_name
                if sub.subdesiobj.lgaobj2.lga_name else sub.subdesiobj.desi_city,
            "Country": sub.subdesiobj.desicountry.country_name,
            "profil_pic": (
                f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{sub.subdesiobj.desi_pic}"
                if sub.subdesiobj.desi_pic else None
            ),
            "rating": avg_rating,        # ✅ Average rating
            "total_ratings": total_ratings  # ✅ Number of ratings
        })

    # Construct the response
    response_data = {
        'designers': designers_data,
        'total_pages': design_pagination.pages,
        'current_page': design_pagination.page,
        'total_items': design_pagination.total,
        'creator': desi_loggedin,
        'client': logged_in
    }

    return jsonify(response_data), 200


"""Designers Details """
@limiter.limit(laps)
@user_api_bp.route('/api/designer/<id>/', methods=['GET'])
@jwt_required()
def designer_detail_api(id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    design = Designer.query.filter(Designer.desi_id==id).first()

    if not design:
        return jsonify({"message": "Designer not found"}), 404

    # rating1 = Rating.query.filter(Rating.rat_rating==1, Rating.rat_desiid==id).count() #changed to .count()
    # rating2 = Rating.query.filter(Rating.rat_rating==2, Rating.rat_desiid==id).count()
    # rating3 = Rating.query.filter(Rating.rat_rating==3, Rating.rat_desiid==id).count()
    # rating4 = Rating.query.filter(Rating.rat_rating==4, Rating.rat_desiid==id).count()
    # rating5 = Rating.query.filter(Rating.rat_rating==5, Rating.rat_desiid==id).count()
    rating = Rating.query.filter(Rating.rat_desiid==id).all()
    if rating:
        avg_rating = round(sum(r.rat_rating for r in rating) / len(rating), 2)
    else:
        avg_rating = 0
    follow_count = Follow.query.filter_by(follow_desiid=id).count() #more efficient to count in the database

    is_following = False
    if logged_in: # Consider how you will identify the user with an API (e.g., API key, JWT)
        follower = Follow.query.filter_by(follow_custid=logged_in, follow_desiid=id).first()
        if follower:
            is_following = True

    # Serialize the data into a dictionary
    designer_data = {
        'desi_id': design.desi_id,
        'desi_fname': design.desi_fname,
        'desi_lname': design.desi_lname,
        'desi_bio': design.desi_businessName,
        'desi_about': design.desi_about,
        "status": design.desi_access,
        'rating_counts': {"average_rating":avg_rating, "total_rating":len(rating)},
        'follow_count': follow_count,
        'is_following': is_following,  # Requires user authentication context
        'creator': desi_loggedin,
        'client': logged_in
    }
    return jsonify(designer_data), 200


"""Comment session"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/comment/<int:postid>/', methods=['POST'])
@jwt_required()
def api_comment(postid):
    identity = get_jwt_identity()  # Get the current logged-in user
    # print("comment identity", identity)
    user_type, userid = identity.split(':') if identity else (None, None)
    # print(f"this is comment user type {user_type} and user id {userid}")

    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    data = request.json
    # idd = data.get('id')
    pstd = Posting.query.get(postid)
    # idd = request.form.get('id')

    if not pstd:
        return jsonify({"message":"this post is not available"}),404

    # try:
    if request.json:  # Check if the request is JSON
        # print("the is the comment request data", request.json)
        data = request.json
        # print("this is still the data from data variable ", data)
        comment_text = data.get('comment')  # Get comment from JSON
        # id = data.get('id')
        # print("this is the post id", id)
    else:
        comment_text = request.form.get('comment')  # Get comment from form
        # idd = request.form.get('id')
        # print("this is a form request data", request.form)

    if not comment_text:
        return jsonify({'message': 'Comment text is required'}), 400


    if desi_loggedin:
        designer = db.session.get(Designer, desi_loggedin)
        if not designer:
            return jsonify({'message': 'Designer not found'}), 404

        existing_comment = Comment.query.filter_by(
            com_body=comment_text, com_postid=postid, com_desiid=designer.desi_id).first()

        if existing_comment:
            return jsonify({'message': "You've commented this before. Write another"}), 400

        new_comment = Comment(com_body=comment_text, com_postid=postid, com_desiid=designer.desi_id)
        new_notification = Notification(notify_desiid=designer.desi_id,
                                        notify_postid=postid, notify_read='unread')

        db.session.add(new_comment)
        db.session.add(new_notification)
        db.session.commit()

        return jsonify({'message': 'Comment created successfully',
                        'comment_id': new_comment.com_id, "redirect_url": f'/api/post/{postid}/'}), 201

    elif logged_in:
        customer = db.session.get(Customer, logged_in)
        if not customer:
            return jsonify({'message': 'Customer not found'}), 404

        existing_comment = Comment.query.filter_by(
            com_body=comment_text, com_postid=postid, com_custid=customer.cust_id).first()

        if existing_comment:
            return jsonify({'message': "You've commented this before. Write another"}), 400

        new_comment = Comment(com_body=comment_text, com_postid=postid, com_custid=customer.cust_id)
        new_notification = Notification(notify_custid=customer.cust_id,
                                        notify_postid=postid, notify_read='unread')

        db.session.add(new_comment)
        db.session.add(new_notification)
        db.session.commit()

        # Attempt to fetch the comment author's email address. Handle potential issues gracefully.
        try:
            commenter = Comment.query.filter_by(com_postid=postid).first()
            if commenter and commenter.compostobj and commenter.compostobj.designerobj:
                commenter_email = commenter.compostobj.designerobj.desi_email
                comment_signal.send(current_app, comment=new_comment, post_author_email=commenter_email)
            else:
                print("Could not retrieve commenter's email. " \
                "Possible data integrity issue.") # Log for debugging
        except Exception as e:
            print(f"Error sending comment signal: {e}") # Log the error

        return jsonify({'message': 'Comment created successfully', 'comment_id': new_comment.com_id, "redirect_url": f'/api/post/{postid}/'}), 201

    else:
        return jsonify({'message': 'Unexpected error: User neither designer nor customer'}), 500



"""Reply Session """
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/reply/<int:postid>/<int:commentid>/', methods=['POST'])
@jwt_required()
def reply_api(postid, commentid):
    """
    Handles creating a reply to a comment on a post.  This endpoint expects a POST request
    with the 'comrep' field in the request body containing the reply text.  It checks if a
    designer or customer is logged in, creates the reply, saves it to the database,
    creates a notification, and sends a signal.

    Returns:
        JSON response with:
            - "status": "success" if the reply was created successfully
            - "status": "error" if there was an error (e.g., user not logged in, duplicate comment)
            - "message": A descriptive message about the outcome
            - "redirect_url": The URL to redirect to on success (can be used by the frontend)
    """
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)

    repl = request.json.get('comrep')
    # print(repl)
    if not repl:
        return jsonify({"status": "error", "message": "this field is required"}), 400  # Bad Request

    if desi_loggedin:
        des = db.session.get(Designer, desi_loggedin)
        comt = Comment.query.filter_by(com_body=repl, com_postid=postid,
                                         com_desiid=des.desi_id, parent_id=commentid).first()
        if comt is None:
            m = Comment(com_body=repl, com_postid=postid, com_desiid=des.desi_id, parent_id=commentid)
            m.save()
            d = Notification(notify_desiid=des.desi_id, notify_comid=commentid, notify_read='unread')
            d.save()
            commenter = Comment.query.filter_by(com_postid=postid, parent_id=m.parent_id).first() #This line is not used, so I commented it out
            dso = Comment.query.filter_by(com_postid=postid, com_id=commentid).first()
            custom = dso.comcustobj.cust_fname  # Assuming this relationship exists
            recipients = {'custom': custom}
            commenter_email = dso.comcustobj.cust_email  # Assuming this relationship exists
            reply_signal.send(current_app, comment=m,
                              post_author_email=commenter_email,
                              recipients=recipients) #I commented this because the signal import was missing and I couldn't test.
            return jsonify({
                "status": "success",
                "message": "Reply created successfully",
                "redirect_url": f'/api/post/{postid}/'
            }), 201  # Created

        else:
            return jsonify({
                "status": "error",
                "message": "You've commented this before. Write another",
                "redirect_url": f'/api/post/{postid}/'
            }), 409  # Conflict

    elif logged_in:
        cus = db.session.get(Customer, logged_in)
        comt = Comment.query.filter_by(com_body=repl, com_custid=cus.cust_id,
                                         com_postid=postid, parent_id=commentid).first()
        if comt is None:
            k = Comment(com_body=repl, com_postid=postid,
                        com_custid=cus.cust_id, com_id=commentid)
            k.save()
            d = Notification(notify_custid=cus.cust_id,
                             notify_comid=commentid, notify_read='unread')
            d.save()
            # commenter = Comment.query.filter_by(com_postid=postid,
            # parent_id=k.parent_id).first() #This line is not used, so I commented it out
            dso = Comment.query.filter_by(com_postid=postid, parent_id=commentid).first()
            custom = dso.compostobj.designerobj.desi_businessName  # Assuming this relationship exists
            recipients = {'custom': custom}
            commenter_email = dso.compostobj.designerobj.desi_email  # Assuming this relationship exists
            reply_signal.send(current_app, comment=k,
                              post_author_email=commenter_email,
                              recipients=recipients) #I commented this because the signal import was missing and I couldn't test.
            return jsonify({
                "status": "success",
                "message": "Reply created successfully",
                "redirect_url": f'/post/{postid}/'
            }), 201  # Created
        else:
            return jsonify({
                "status": "error",
                "message": "You've commented this before. Write another",
                "redirect_url": f'/post/{postid}/'
            }), 409  # Conflict


"""like session"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/like/<int:post_id>/', methods=['POST'])
@jwt_required()  # Assuming JWT authentication for users
def apilike(post_id):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    logged_in = int(userid) if user_type == 'customer' else None
    desi_loggedin = int(userid) if user_type == 'designer' else None
    last_active(userid, user_type)
    # print(f"this is post id under like {post_id}")
    posti = Posting.query.filter_by(post_id=post_id).first()
    if not posti:
        return jsonify({"message": "Post does not exist"}), 404

    # If designer is logged in
    if desi_loggedin:
        liking = Like.query.filter_by(like_desiid=desi_loggedin, like_postid=post_id).first()
        # print(f"this is like data {liking}")
        # print(f"this is designer id {desi_loggedin}")
        if liking:
            # Send an unlike signal
            commenter_email = posti.designerobj.desi_email
            custom = posti.designerobj.desi_businessName
            recipients = {"custom": custom}
            unlike_signal.send(current_app, comment=liking,
                               post_author_email=commenter_email,
                               recipients=recipients)
            # If the designer already liked the post, unlike it
            db.session.delete(liking)
            db.session.commit()

            return jsonify({"message": "Post unliked successfully"}), 200
        else:
            # If not liked yet, add a like
            liking = Like(like_desiid=desi_loggedin, like_postid=post_id)
            db.session.add(liking)
            db.session.commit()
            # print(f"this is successful like data {liking}")
            # print(f"this is successful designer id is present {desi_loggedin}")

            # Create notification for the designer
            lk = Like.query.filter_by(like_postid=post_id, like_desiid=desi_loggedin).first()
            notification = Notification(notify_desiid=desi_loggedin,
                                        notify_likeid=lk.like_id, notify_read='unread')
            db.session.add(notification)
            db.session.commit()

            # Send a like signal
            commenter_email = posti.designerobj.desi_email
            custom = posti.designerobj.desi_businessName
            recipients = {"custom": custom}
            like_signal.send(current_app, comment=liking,
                             post_author_email=commenter_email,
                             recipients=recipients)

            return jsonify({"message": "Post liked successfully"}), 200

    # If customer is logged in
    if logged_in:
        liking = Like.query.filter_by(like_custid=logged_in, like_postid=post_id).first()
        if liking:
            # Send an unlike signal
            commenter_email = posti.designerobj.desi_email
            custom = posti.designerobj.desi_businessName
            recipients = {"custom": custom}
            unlike_signal.send(current_app, comment=liking,
                               post_author_email=commenter_email,
                               recipients=recipients)
            # If the customer already liked the post, unlike it
            db.session.delete(liking)
            db.session.commit()

            return jsonify({"message": "Post unliked successfully"}), 200
        else:
            # If not liked yet, add a like
            liking = Like(like_custid=logged_in, like_postid=post_id)
            db.session.add(liking)
            db.session.commit()

            # Create notification for the customer
            lk = Like.query.filter_by(like_postid=post_id, like_custid=logged_in).first()
            notification = Notification(notify_custid=logged_in,
                                        notify_likeid=lk.like_id, notify_read='unread')
            db.session.add(notification)
            db.session.commit()

            # Send a like signal
            commenter_email = posti.designerobj.desi_email
            custom = posti.designerobj.desi_businessName
            recipients = {"custom": custom}
            like_signal.send(current_app, comment=liking,
                             post_author_email=commenter_email,
                             recipients=recipients)

            return jsonify({"message": "Post liked successfully"}), 200
    # else:
    #     return jsonify({"message": "User not authenticated"}), 401


"""Share buttons"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/share/', methods=['POST'])
@jwt_required()  # Ensure the user is authenticated (either designer or customer)
def apishare():
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    # Get the data from the incoming JSON request body
    data = request.json

    name = data.get('name')
    postid = data.get('sharepost')
    user = data.get('user')

    if not name or not postid or not user:
        return jsonify({"message": "Missing required fields: name, sharepost, and user."}), 400

    if desi_loggedin:
        # Designer is logged in
        sh = Share(share_webname=name, share_postid=postid, share_desiid=user)
        db.session.add(sh)
        db.session.commit()

        # Create a notification for the designer
        notification = Notification(notify_desiid=user,
                                    notify_shareid=sh.share_id, notify_read='unread')
        db.session.add(notification)
        db.session.commit()

        # Send a share signal
        commenter = Share.query.filter_by(share_postid=postid,
                                          share_desiid=desi_loggedin).first()
        commenter_email = commenter.postshareobj.designerobj.desi_email
        custom = commenter.postshareobj.designerobj.desi_businessName
        recipients = {"custom": custom}
        share_signal.send(current_app, comment=commenter,
                          post_author_email=commenter_email,
                          recipients=recipients)

        return jsonify({"message": "Post shared successfully by designer."}), 200

    elif logged_in:
        # Customer is logged in
        sh = Share(share_webname=name, share_postid=postid, share_custid=user)
        db.session.add(sh)
        db.session.commit()

        # Create a notification for the customer
        notification = Notification(notify_custid=user, notify_shareid=sh.share_id,
                                    notify_read='unread')
        db.session.add(notification)
        db.session.commit()

        # Send a share signal
        commenter = Share.query.filter_by(share_postid=postid, share_custid=logged_in).first()
        commenter_email = commenter.postshareobj.designerobj.desi_email
        custom = commenter.postshareobj.designerobj.desi_businessName
        recipients = {"custom": custom}
        share_signal.send(current_app, comment=commenter,
                          post_author_email=commenter_email,
                          recipients=recipients)

        return jsonify({"message": "Post shared successfully by customer."}), 200

    else:
        return jsonify({"message": "User not authenticated."}), 401


"""token confirmation"""
@limiter.limit(laps)
@user_api_bp.route('/api/confirm_token', methods=['GET'])
def apiconfirm_email():
    try:
        token_q = request.args.get("token")
        if not token_q:
            return jsonify({"error": "Token is required"}), 400

        token = unquote_plus(token_q)

        result = confirm_activation_code(token)
        if "error" in result:
            return jsonify({"error": result["error"]}), 401

        if result.get("valid"):
            email = result.get("email")
            if not email:
                return jsonify({"error": "Email not found in token"}), 400

            cus = Customer.query.filter_by(cust_email=email).first()
            des = Designer.query.filter_by(desi_email=email).first()

            if cus and cus.cust_status == 'actived':
                return jsonify({"message": "Account already activated. Please login."}), 200

            if des and des.desi_status == 'actived':
                return jsonify({"message": "Account already activated. Please login."}), 200

            if cus:
                cus.cust_status = 'actived'
                cus.cust_activationdate = datetime.now()
                db.session.commit()
                return jsonify({
                    "message": f"Activation successful. Please login with your {email}"
                    }), 200

            if des:
                des.desi_status = 'actived'
                des.desi_activationdate = datetime.now()
                db.session.commit()
                return jsonify({
                    "message": f"Activation successful. Please login with your {email}"
                    }), 200

        return jsonify({"error": "Invalid session or token"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500

"""unconfirmed activation section"""
@limiter.limit(laps)
@user_api_bp.route('/api/unconfirmed', methods=['GET'])
@jwt_required()
def apiunconfirmed():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    if logged_in:
        cusi = Customer.query.filter_by(cust_id=logged_in).first_or_404()
        if cusi.cust_status == 'actived':
            return jsonify({'redirect': '/customer/profile/'})

    if desi_loggedin:
        desi = Designer.query.filter_by(desi_id=desi_loggedin).first_or_404()
        if desi.desi_status == 'actived':
            return jsonify({'redirect': '/designer/profile/'})

    return jsonify({'message': 'Confirm your account!', 'status': 'warning'})


"""Resend activation"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/resend-activation', methods=['POST'])
@jwt_required()
def resend_confirmation():
    identity = get_jwt_identity()
    # print("this is my identity ",identity)
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401

    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    email = request.json.get('email')
    # print(email)
    if logged_in:
        cus = Customer.query.filter_by(cust_id=logged_in).first_or_404()
        if email == cus.cust_email:
            token = generate_activation_token(cus.cust_email)
            token_quoted = quote_plus(token)
            activation_link = f"https://styleitafrica.pythonanywhere.com/api/confirm_token?token={token_quoted}"
            subject = "Please confirm your email"
            send_email(cus.cust_email, subject, activation_link)
            return jsonify({'message': 'A new activation link has been sent to your mail.',
                            'status': 'success', "activation_link":activation_link})
        else:
            return jsonify({'message': 'provide a valid email', 'status': 'error'})

    if desi_loggedin:
        des = Designer.query.filter_by(desi_id=desi_loggedin).first_or_404()
        if email == des.desi_email:   
            token = generate_activation_token(des.desi_email)
            token_quoted = quote_plus(token)
            activation_link = f"https://styleitafrica.pythonanywhere.com/api/confirm_token?token={token_quoted}"
            subject = "Please confirm your email"
            send_email(des.desi_email, subject, activation_link)
            return jsonify({'message': 'A new activation link has been sent to your mail.',
                            'status': 'success', "activation_link":activation_link})
        else:
            return jsonify({'message': 'provide a valid email', 'status': 'error'})

"""verification of user"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/user_verification', methods=['PUT'])
@jwt_required()
def user_verification_api():
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid
    last_active(userid, user_type)
    cus = None
    des = None
    vpic = request.files.get('pic')
    if not vpic:
        return jsonify({"status": "error", "message": "upload an image"}), 400
    original_pic = vpic.filename
    if logged_in:
        cus = db.session.get(Customer, logged_in)
        if original_pic:
            extension = os.path.splitext(original_pic)[1].lower()
            if extension in ['.jpg', '.gif', '.png']:
                fn = math.ceil(random.random() * 10000000000)
                saveas = str(fn) + extension
                save_path = os.path.join(current_app.config['cusveri_pic'], saveas)
                vpic.save(save_path)
                cus.cust_vinpic=saveas
                db.session.commit()

    if desi_loggedin:
        des = db.session.get(Designer, desi_loggedin)
        if original_pic:
            extension = os.path.splitext(original_pic)[1].lower()
            if extension in ['.jpg', '.gif', '.png']:
                fn = math.ceil(random.random() * 10000000000)
                saveas = str(fn) + extension
                save_path = os.path.join(current_app.config['desveri_pic'], saveas)
                vpic.save(save_path)
                des.desi_vinpic=saveas
                db.session.commit()

    return jsonify({"message":"verification complete"})


# Customers sections
"""Custormer Signup"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/customer/signup', methods=['POST'])
def customer_signup():
    pic = request.files.get('pic')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    pwd = request.form.get('pwd')
    cpwd = request.form.get('cpwd')
    address = request.form.get('address')
    country = request.form.get('country')
    state = request.form.get('state')
    lga = request.form.get('lga')
    gender = request.form.get('gender')
    cities = request.form.get('cities')
    nin = request.form.get('nin')
    passport = request.form.get('passport')
    profile_pic = None

    sup = Customer.query.filter_by(cust_email=email).first()
    if sup:
        if sup.cust_email == email:
            return jsonify({"message":"This email is already registered"}), 409
        if sup.cust_nin == nin:
            return jsonify({"message":"This NIN is already linked to another account."
            "Please log in or contact support"}), 409
        if sup.cust_passport == passport:
            return jsonify({"message":"provide a valid passport ID"}), 409
    else:
        pass

    if country == '161':
        if not all([fname, lname, username, email, phone, pwd,
                    cpwd, address, state, lga, gender, country]):
            return jsonify({'message': 'One or more fields are empty', 'status': 'error'}), 400
    else:
        if not all([fname, lname, username, email, phone, pwd,
                    cpwd, address, state, cities, gender, country]):
            return jsonify({'message': 'One or more fields are empty', 'status': 'error'}), 400

    if not nin and not passport:
        return jsonify({'message':'one of the identification filed must be provided'}), 400
    
    if nin:
        if len(nin) != 11:
            return jsonify({"message":"Provide a valid NIN"}), 400

    if passport:
        if len(passport) != 9:
            return jsonify({"message":"Provide a valid Passport number or ID"}), 400

    if len(pwd) < 8:
        return jsonify({'message': 'Password should be at least 8 characters long',
                        'status': 'error'}), 400

    if pwd != cpwd:
        return jsonify({'message': 'Password match error', 'status': 'error'}), 400

    mail = email.split('@')
    if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
        return jsonify({'message': 'Kindly provide a valid email', 'status': 'error'}), 400

    hashed_pwd = generate_password_hash(pwd)

    # Handle profile picture upload
    if pic and allowed_file(pic.filename):
        filename = secure_filename(pic.filename)
        unique_name = f"{math.ceil(random.random() * 10000000000)}_{filename}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        pic.save(save_path)
        profile_pic = unique_name

    new_customer = Customer(
        cust_fname=fname,
        cust_username=username,
        cust_lname=lname,
        cust_gender=gender,
        cust_phone=phone,
        cust_email=email,
        cust_pass=hashed_pwd,
        cust_address=address,
        cust_nin = nin,
        cust_passport = passport,
        cust_pic=profile_pic,
        cust_stateid=state if country == '161' else None,
        cust_lgaid=lga if country == '161' else None,
        cust_city=cities if country != '161' else None,
        cust_countryid=country
    )

    db.session.add(new_customer)
    db.session.commit()

    if country != '161':
        db.session.add(Cities(name=cities))
        db.session.add(States(name=state))
        db.session.commit()

    token = generate_activation_token(email)
    token_quoted = quote_plus(token)
    activation_link = f"https://styleitafrica.pythonanywhere.com/api/confirm_token?token={token_quoted}"
    send_email(email, "Please confirm your email", activation_link)
    newcus = Customer.query.filter_by(cust_email=email).first()
    access_token = create_access_token(identity=f"customer:{newcus.cust_id}")
    return jsonify({"activation_link":activation_link, "access_token":access_token, "customerId":newcus.cust_id,
                    'message': 'Profile setup completed. A confirmation mail has been sent via email',
                    'status': 'success','customer': {'id': newcus.cust_id, 'first_name': newcus.cust_fname,
                    'last_name': newcus.cust_lname, 'email': newcus.cust_email, 'phone': newcus.cust_phone,
                    'address': newcus.cust_address, 'username':newcus.cust_username, 'gender': newcus.cust_gender,
                    'registerDate': newcus.cust_regdate, 'status': newcus.cust_status, "state":newcus.cust_state,
                    'profilePic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{newcus.cust_pic}" if newcus.cust_pic else None,
                    'access': newcus.cust_access, 'nin': newcus.cust_nin, 'passport': newcus.cust_passport,'cities': newcus.cust_city,
                    'vinpic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/vpic/{newcus.cust_vinpic}" if newcus.cust_vinpic else None,
                    "state_name": newcus.stateobj.state_name if newcus.stateobj else None, "lga_name": newcus.lgaobj.lga_name if newcus.lgaobj else None,
                    "state_id": newcus.cust_stateid if newcus else None, "lga_id": newcus.cust_lgaid if newcus else None,
                    },
                    }), 200


"""Custormer Login"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/user/customer/login', methods=['POST'])
def customer_login():
    email = request.json.get('email')
    pwd = request.json.get('pwd')
    # print(email, pwd)
    if not email or not pwd:
        return jsonify({'message': 'Invalid Credentials', 'status': 'danger'}), 400

    user = Customer.query.filter_by(cust_email=email).first()
    if not user:
        return jsonify({'message': 'Kindly supply valid credentials', 'status': 'warning'}), 401

    if check_password_hash(user.cust_pass, pwd):
        session['customer'] = user.cust_id
        access_token = create_access_token(identity=f"customer:{user.cust_id}")
        refresh_token = create_refresh_token(identity=f"customer:{user.cust_id}")
        # set_access_cookies(access_token)
        lo = Login(login_email=user.cust_email, login_custid=user.cust_id, last_active_at=datetime.now(timezone.utc))
        db.session.add(lo)
        db.session.commit()
        # print(access_token, session['customer'])
        return jsonify({'message': 'Login successful', 'userid':session['customer'],
                        'access_token':access_token, 
                        'refresh_token':refresh_token,
                        'status': 'success',
                        'customer': {'id': user.cust_id, 'first_name': user.cust_fname,
                        'last_name': user.cust_lname, 'email': user.cust_email, 'phone': user.cust_phone,
                        'address': user.cust_address, 'username':user.cust_username, 'gender': user.cust_gender,
                        'registerDate': user.cust_regdate, 'status': user.cust_status,
                        'profilePic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{user.cust_pic}" if user.cust_pic else None,
                        'nin': user.cust_nin, 'passport':user.cust_passport, 'cities':user.cust_city,
                        'vinpic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/vpic/{user.cust_vinpic}" if user.cust_vinpic else None,
                        'states':user.cust_state, 'access': user.cust_access, 'state_id': user.stateobj.state_id if user.stateobj else None, 'state':user.stateobj.state_name if user.stateobj else None,
                        'lga_id':user.lgaobj.lga_id if user.lgaobj else None, 'lga_name':user.lgaobj.lga_name if user.lgaobj else None
                        },
                        'redirect': '/api/customer/profile'})

    return jsonify({'message': 'Kindly supply a valid email address and password',
                    'status': 'warning'}), 401

"""Customer Profile"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/customer/profile', methods=['GET', 'PUT'])
@jwt_required()
def customer_profile():
    identity = get_jwt_identity()

    user_type, logged_in = identity.split(':') if identity else (None, None)
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access', 'status': 'error'}), 401
    last_active(logged_in, user_type)
    cus = db.session.get(Customer, logged_in)
    if cus.cust_status == 'deactived':
        return jsonify({'message': 'Please confirm your account', 'status': 'warning',
                        'redirect': '/api/unconfirmed'})

    if cus.cust_access == 'deactived':
        session.pop('customer', None)
        return jsonify({'message': 'Your account has been deactivated. Contact Styleit for help',
                        'status': 'danger', 'redirect': '/api/user/customer/login'})

    if request.method == 'GET':
        # print(logged_in)
        state = State.query.filter(State.state_id==cus.cust_stateid).first()
        lg = Lga.query.filter(Lga.lga_id==cus.cust_lgaid).first()
        page = request.args.get('page', 1, type=int)
        mylike = Like.query.filter(Like.like_custid == cus.cust_id).paginate(page=page, per_page=30)
        getbk = Bookappointment.query.filter(Bookappointment.ba_custid == logged_in)\
            .order_by(desc(Bookappointment.ba_date)).paginate(page=page, per_page=20)
        noti = Notification.query.filter(Notification.notify_read == 'unread',
                                          Notification.notify_custid == cus.cust_id)\
                                            .order_by(desc(Notification.notify_date)).all()
        follow = Follow.query.filter_by(follow_custid=logged_in).all()

        return jsonify({
            'userid': logged_in,
            'user_type':user_type,
            'customer': {
                'id': cus.cust_id,
                'fname': cus.cust_fname,
                'lname': cus.cust_lname,
                'email': cus.cust_email,
                'phone': cus.cust_phone,
                'address': cus.cust_address,
                'username':cus.cust_username,
                'gender': cus.cust_gender,
                'registerDate': cus.cust_regdate,
                'profilePic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{cus.cust_pic}"if cus.cust_pic else None,
                'status': cus.cust_status,
                'access': cus.cust_access,
                'nin': cus.cust_nin,
                'passport':cus.cust_passport,
                'vinpic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/vpic/{cus.cust_vinpic}" if cus.cust_vinpic else None,
                'cities':cus.cust_city,
                'states':cus.cust_state,
                'state': [{'id': state.state_id, 'name': state.state_name}],
                'lga': [{'id': lg.lga_id, 'name': lg.lga_name}]
            },

            'likes': [{"likeDate":lk.like_date, "postLiked":lk.posts.post_title if lk.posts else None,
                       "imagelikedUrl":f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{lk.posts.imagepostobj[0].image_url}" if lk.posts.imagepostobj and lk.posts.imagepostobj[0].image_url else None,
                       "imagelikedName":lk.posts.imagepostobj[0].image_name if lk.posts and lk.posts.imagepostobj else None,
                       "creatorPostLiked":lk.desilikesobj.desi_businessName if lk.desilikesobj else None}
                       for lk in mylike.items],

            'appointments': [{
                'bookingId':bk.ba_id, 'requestDate':bk.ba_date, 'bookingDate':bk.ba_bookingDate,
                'bookingTime':bk.ba_bookingTime,
                "collectionTime":bk.ba_collectionTime,
                "collectionDate": bk.ba_collectionDate,
                "status":bk.ba_status,
                "collectionStatus": bk.ba_custstatus,
                "paymentStatus": bk.ba_paystatus,
                "reason": bk.ba_reason,
                "clientName":bk.custbaobj.cust_username if bk.custbaobj and bk.custbaobj.cust_username else None,
                "creatorId": bk.desibaobj.desi_id if bk.desibaobj and bk.desibaobj.desi_id else None,
                "creatorName": bk.desibaobj.desi_businessName if bk.desibaobj and bk.desibaobj.desi_businessName else None,
                "creatorPhone": bk.desibaobj.desi_phone if bk.desibaobj and bk.desibaobj.desi_phone else None,
                "creatorFname":bk.desibaobj.desi_fname if bk.desibaobj and bk.desibaobj.desi_fname else None,
                "creatorLname":bk.desibaobj.desi_lname if bk.desibaobj and bk.desibaobj.desi_lname else None
            } for bk in getbk.items],

            'notification':[{'noteid':nt.notify_id if nt.notify_id else None,
                             'noti_postid':nt.notify_postid if nt.notify_postid else None,
                             'noti_message':nt.notify_read if nt.notify_read else None,
                             'noti_date': nt.notify_date if nt.notify_date else None,
                             'noti_clientid':nt.notify_custid if nt.notify_custid else None, 
                             'noti_likeid':nt.notify_likeid if nt.notify_likeid else None, 
                             'noti_commentid':nt.notify_comid if nt.notify_comid else None, 
                             'noti_shareid':nt.notify_shareid if nt.notify_shareid else None, 
                             'noti_bookappointmentid':nt.notify_baid if nt.notify_baid else None, 
                             'noti_transaction_paymentid':nt.notify_tpayid if nt.notify_tpayid else None,
                             'noti_transaction_payment_status':nt.notifytpayobj.tpay_status if nt.notifytpayobj else None, 
                             'noti_creatorid':nt.notify_desiid if nt.notify_desiid else None, 
                             'noti_creator_firstname':nt.notifydesiobj.desi_fname if nt.notifydesiobj else None, 
                             'noti_client_firstname':nt.notifycustobj.cust_fname if nt.notifycustobj else None, 
                             'noti_subscriptionid':nt.notify_subid if nt.notify_subid else None, 
                             'noti_subplan':nt.notifysubobj.sub_plan if nt.notifysubobj else None, 
                             'noti_sub_status':nt.notifysubobj.sub_status if nt.notifysubobj else None, 
                             'noti_paymentid':nt.notify_paymentid if nt.notify_paymentid else None, 
                             'noti_payment_status':nt.notifypayobj.payment_status if nt.notifypayobj else None } for nt in noti],

            'follows': [{'id':f.follow_id, 'follow_desiid':f.follow_desiid,
                         'follow_custid':f.follow_custid} for f in follow],
            'total_following': len(follow),
            'total_notification':len(noti)
        })

    if request.method == 'PUT':
        data = request.json
        fname = data.get('fname')
        lname = data.get('lname')
        email = data.get('email')
        phone = data.get('phone')
        address = data.get('address')

        if not fname or not lname or not email or not phone or not address:
            return jsonify({'message': 'One or more fields are empty',
                            'status': 'warning'}), 400

        upd = db.session.get(Customer, logged_in)
        upd.cust_fname = fname
        upd.cust_lname = lname
        upd.cust_phone = phone
        upd.cust_email = email
        upd.cust_address = address
        db.session.commit()

        return jsonify({'message': 'Profile updated successfully', 'status': 'success'})


""" update customer profile picture"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/customer/update/profilepic', methods=['PUT'])
@jwt_required()
def update_customer_profilepic():
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if not logged_in:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(logged_in, user_type)
    if request.method == 'PUT':
        pic = request.files.get('pic')
        if not pic:
            return jsonify({'message': 'No file provided'}), 400

        original_name = pic.filename
        if original_name:
            extension = os.path.splitext(original_name)[1].lower()
            if extension in ['.jpg', '.gif', '.png']:
                fn = math.ceil(random.random() * 10000000000)
                saveas = f"{fn}{extension}"
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], saveas)
                pic.save(save_path)

                cust = db.session.get(Customer, logged_in)
                cust.cust_pic = saveas
                db.session.commit()

                return jsonify({'message': 'Profile picture updated successfully',
                                'status': 'success',
                                'profilePic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/customer/{cust.cust_pic}"})

        return jsonify({'message': 'Invalid file type'}), 400


"""customer logout session"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/customer/logout', methods=['POST'])
@jwt_required()
def customer_logout():
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if not logged_in:
        return jsonify({'message': 'Unauthorized access', 'status': 'error', 'redirect': '/'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access', 'status': 'error', 'redirect': '/'}), 401
    last_active(logged_in, user_type)
    jti = get_jwt()["jti"]
    db.session.add(TokenBlocklist(jti=jti, jti_custid=int(logged_in)))
    db.session.commit()
    session.pop('customer', None)
    lo = Login.query.filter_by(login_custid=int(logged_in), logout_date=None).first()
    if lo:
        lo.logout_date = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify({'message': 'Logout successful', 'status': 'success', 'redirect': '/'}), 200


"""Customers Details """
@limiter.limit(laps)
@user_api_bp.route('/api/customer/<id>', methods=['GET'])
@jwt_required()
def customer_detail(id):
    identity = get_jwt_identity()
    user_type, userid = identity.split(':') if identity else (None, None)
    if not userid or not user_type:
        return jsonify({'message': 'Unauthorized access'}), 401

    if user_type == 'designer':
        desi_loggedin = userid if userid is not None else userid
        logged_in = None
    else:
        logged_in = userid if userid is not None else userid
        desi_loggedin = None
    last_active(userid, user_type)
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'message': 'Customer not found', 'status': 'error'}), 404

    return jsonify({
        'customer': {
            "user_type": user_type,
            'userid': logged_in if logged_in else desi_loggedin,
            'id': customer.cust_id,
            'fname': customer.cust_fname,
            'lname': customer.cust_lname,
            'email': customer.cust_email,
            'phone': customer.cust_phone,
            'address': customer.cust_address
        }
    })


"""book appointment"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/bookappointment', methods=['POST'])
@jwt_required()
def apibook_appointment():
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if not logged_in:
        return jsonify({'message': 'Please Login/Signup to book appointment'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access', 'redirect': '/'}), 401
    last_active(logged_in, user_type)
    data = request.json
    dsignername = data.get('dsignername')
    bdate = data.get('bookingdate')
    btime = data.get('bookingtime')
    cdate = data.get('collectiondate')
    ctime = data.get('collectiontime')

    if not all([dsignername, bdate, btime, cdate, ctime]):
        return jsonify({'message': 'Kindly fill each field', 'status': 'warning'}), 400

    bookapp = Bookappointment(
        ba_desiid=dsignername, ba_custid=logged_in,
        ba_bookingDate=bdate, ba_bookingTime=btime,
        ba_collectionDate=cdate, ba_collectionTime=ctime
    )
    db.session.add(bookapp)
    db.session.commit()

    db.session.add(Notification(notify_custid=logged_in,
                                notify_baid=bookapp.ba_id, notify_read='unread'))
    db.session.add(Notification(notify_desiid=dsignername,
                                notify_baid=bookapp.ba_id, notify_read='unread'))
    db.session.commit()

    return jsonify({'message': 'Booking successful', 'status': 'success'})

# customer section ends

# designer section begins
"""Designer Signup"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/signup', methods=['POST'])
def designer_signup():

    pic = request.files.get('pic')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    busname = request.form.get('busname')
    email = request.form.get('email')
    phone = request.form.get('phone')
    pwd = request.form.get('pwd')
    cpwd = request.form.get('cpwd')
    address = request.form.get('address')
    country = request.form.get('country')
    state = request.form.get('state')
    lga = request.form.get('lga')
    gender = request.form.get('gender')
    cities = request.form.get('cities')
    nin = request.form.get('nin')
    passport = request.form.get('passport')
    original_name = pic.filename if pic else ""
    # print(f"this is cpwd:{cpwd}, address:{address}, fname:{fname}, lname:{lname}, state:{state}, lga:{lga}, cities:{cities}, address:{address}, busname:{busname}, pic:{pic}, pwd:{pwd}, nin:{nin} this is a passport:{passport}")
    dsup = Designer.query.filter_by(desi_email=email).first()
    if dsup:
        if dsup.desi_email == email:
            return jsonify({"message":"This email is already registered"}), 409
        if dsup.desi_nin == nin:
            return jsonify({"message":"This NIN is already linked to another account."
            "Please log in or contact support"}), 409
        if dsup.desi_passport == passport:
            return jsonify({"message":"provide a valid passport ID"}), 409
    else:
        pass

    if country == '161' and fname=="" and lname=="" and busname=="" and email=="" and pwd=="" and cpwd=="" and address=="" and state=="" and lga=="" and gender=="":
        return jsonify({'message': 'One or more fields are empty', 'status': 'error'}), 400
    else:
        if fname=="" and lname=="" and busname=="" and email=="" and pwd=="" and cpwd=="" and address=="" and state=="" and cities=="" and gender=="" and country=="":
            return jsonify({'message': 'One or more fields are empty', 'status': 'error'}), 400

    if nin=="" and passport=="":
        return jsonify({'message':'one of the identification filed must be provided'}), 400
    if nin:
        if len(nin) != 11:
            return jsonify({"message":"Provide a valid NIN"}), 400

    if passport:
        if len(passport) != 9:
            return jsonify({"message":"Provide a valid Passport number or ID"}), 400

    if len(pwd) < 8:
        return jsonify({'message': 'Password should be at least 8 characters long',
                        'status': 'error'}), 400

    if pwd != cpwd:
        return jsonify({'message': 'Password match error', 'status': 'error'}), 400

    mail = email.split('@')
    if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
        return jsonify({'message': 'Kindly provide a valid email', 'status': 'error'}), 400


    hashed_password = generate_password_hash(pwd)

    saveas = ""
    if original_name:
        extension = os.path.splitext(original_name)[1].lower()
        if extension in ['.jpg', '.gif', '.png']:
            fn = math.ceil(random.random() * 10000000000)
            saveas = str(fn) + extension
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER2'], saveas)
            pic.save(save_path)

    new_designer = Designer(
        desi_fname=fname,
        desi_businessName=busname,
        desi_lname=lname,
        desi_gender=gender,
        desi_phone=phone,
        desi_email=email,
        desi_pass=hashed_password,
        desi_address=address,
        desi_nin = nin,
        desi_passport = passport,
        desi_pic=saveas,
        desi_stateid=state if country == '161' else None,
        desi_lgaid=lga if country == '161' else None,
        desi_city=cities if country != '161' else None,
        desi_countryid=country
    )
    db.session.add(new_designer)
    db.session.commit()

    if country != '161':
        db.session.add(Cities(name=cities))
        db.session.add(States(name=state))
        db.session.commit()

    token = generate_activation_token(email)
    # confirm_url = url_for('confirm_email', token=token, _external=True)
    token_quoted = quote_plus(token)
    activation_link = f"https://styleitafrica.pythonanywhere.com/api/confirm_token?token={token_quoted}"
    subject = "Please confirm your email"
    # html = render_template('user/activate.html', confirm_url=confirm_url)
    send_email(new_designer.desi_email, subject, activation_link)
    newdes = Designer.query.filter_by(desi_email=email).first()
    state = State.query.filter(State.state_id==newdes.desi_stateid).first()
    lg = Lga.query.filter(Lga.lga_id==newdes.desi_lgaid).first()
    access_token = create_access_token(identity=f"designer:{newdes.desi_id}")
    return jsonify({
        "activation_link":activation_link, "access_token":access_token,
        'message': 'Profile setup completed. Confirmation email sent.','status':'success',
        "creator":{
                'designer_id': newdes.desi_id,
                'first_name': newdes.desi_fname,
                'last_name': newdes.desi_lname,
                'email': newdes.desi_email,
                'phone': newdes.desi_phone,
                'address': newdes.desi_address,
                'profile_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{newdes.desi_pic}" if newdes.desi_pic else None,
                'gender': newdes.desi_gender,
                "businessName": newdes.desi_businessName,
                'registerDate': newdes.desi_regdate,
                'status': newdes.desi_status,
                'access': newdes.desi_access,
                'nin': newdes.desi_nin,
                'passport':newdes.desi_passport,
                'vinpic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/vpic/{newdes.desi_vinpic}" if newdes.desi_vinpic else None,
                'cities':newdes.desi_city,
                'states':newdes.desi_state,
                'state': [{'id': state.state_id, 'name': state.state_name}],
                'lga': [{'id': lg.lga_id, 'name': lg.lga_name}]
            }
        }), 201


"""checking sub status for automatic deactivation"""
# @app.before_request
# def before_request_func():
#     verify_jwt_in_request(optional=True)
#     desiloggedin = session.get('designer')
#     desi_loggedin = get_jwt_identity()
#     if desi_loggedin:
#         g.des = db.session.get(Designer, desi_loggedin)
#         if des:
#             subt = db.session.query(Subscription).filter(
#                 Subscription.sub_desiid == g.des.desi_id,
#                 Subscription.sub_status == 'active'
#             ).first()
#             apt = db.session.query(Bookappointment).filter_by(ba_desiid=g.des.desi_id).all()
#             today = date.today()
#             if subt and subt.sub_enddate < str(today):
#                 subt.sub_status = "deactive"
#                 db.session.commit()
#                 commenter_email = subt.subdesiobj.desi_email
#                 custom = subt.subdesiobj.desi_businessName
#                 recipients = {"custom": custom}
#                 subdeactivate_signal.send(app, comment=subt,
#                                           post_author_email=commenter_email,
#                                           recipients=recipients)
#             if subt and subt.sub_plan == 'free' and len(apt) == 3:
#                 subt.sub_status = "deactive"
#                 db.session.commit()
#                 commenter_email = subt.subdesiobj.desi_email
#                 custom = subt.subdesiobj.desi_businessName
#                 recipients = {"custom": custom}
#                 subdeactivate_signal.send(app, comment=subt,
#                                           post_author_email=commenter_email,
#                                           recipients=recipients)
#             else:
#                 if subt and subt.sub_plan == 'free' and len(apt) == None:
#                     Dstart = date.today()
#                     Dend = Dstart + timedelta(days=29)
#                     # Update subscription details
#                     subt.sub_startdate = Dstart
#                     subt.sub_enddate = Dend
#                     subt.sub_status = 'active'
#                     db.session.commit()
#                     commenter_email = subt.subdesiobj.desi_email
#                     custom = subt.subdesiobj.desi_businessName
#                     recipients = {"custom": custom}
#                     subdeactivate_signal.send(app, comment=subt,
#                                             post_author_email=commenter_email,
#                                             recipients=recipients)


"""Designer Login"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/login', methods=['POST'])
def designer_login():
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid request format'}), 400

    email = data.get('email')
    pwd = data.get('pwd')
    # print("here is your login details ", data)

    if not email or not pwd:
        return jsonify({'error': 'Invalid Credentials'}), 400

    designer = db.session.query(Designer).filter(Designer.desi_email == email).first()
    if not designer or not check_password_hash(designer.desi_pass, pwd):
        return jsonify({'error': 'Invalid email or password'}), 400

    if designer.desi_status != "actived":
        return jsonify({"message": "Your account is either suspended, banned, dormant or deactive. Kindly contact support to activate your account"}), 403

    state = State.query.filter(State.state_id==designer.desi_stateid).first()
    lg = Lga.query.filter(Lga.lga_id==designer.desi_lgaid).first()

    session['designer'] = designer.desi_id
    access_token = create_access_token(identity=f"designer:{designer.desi_id}")
    refresh_token = create_refresh_token(identity=f"designer:{designer.desi_id}")
    le = Login(login_email=designer.desi_email, login_desiid=designer.desi_id, last_active_at=datetime.now(timezone.utc))
    db.session.add(le)
    db.session.commit()

    return jsonify({'message': 'Login successful',
                    'designer_id': designer.desi_id,
                    "token":access_token,
                    "refresh_token":refresh_token,
                    "status":"success",
                    "creator":{
                        'designer_id': designer.desi_id,
                        'first_name': designer.desi_fname,
                        'last_name': designer.desi_lname,
                        'email': designer.desi_email,
                        'phone': designer.desi_phone,
                        'address': designer.desi_address,
                        'profile_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{designer.desi_pic}" if designer.desi_pic else None,
                        'gender': designer.desi_gender,
                        "businessName": designer.desi_businessName,
                        'registerDate': designer.desi_regdate,
                        'status': designer.desi_status,
                        'access': designer.desi_access,
                        'nin': designer.desi_nin,
                        'passport':designer.desi_passport,
                        'vinpic':f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/vpic/{designer.desi_vinpic}" if designer.desi_vinpic else None,
                        'cities':designer.desi_city,
                        'states':designer.desi_state,
                        'state': [{'id': state.state_id, 'name': state.state_name}] if state else [],
                        'lga': [{'id': lg.lga_id, 'name': lg.lga_name}] if lg else []
                        }
                    }), 200


"""Designer Profile"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/profile', methods=['GET', 'PUT'])
@jwt_required()
def designer_profile():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    # print(f"this is a user type {user_type} and this is id {desi_loggedin}")
    if user_type != 'designer':
        return jsonify({'error': 'Unauthorized access'}), 401
    last_active(desi_loggedin, user_type)
    if request.method == 'GET':
        # print(desi_loggedin)
        des = Designer.query.get(int(desi_loggedin))
        if not des:
            return jsonify({'error': 'Designer not found'}), 404

        if des.desi_status == 'deactived':
            return jsonify({'error': 'Please confirm your account'}), 403
        elif des.desi_access == 'deactived':
            session.pop('designer', None)
            return jsonify({'error': 'Your account has been deactivated. Contact support'}), 403

        #before reuqest test.
        if desi_loggedin:
            des = Designer.query.get(int(desi_loggedin))
            # print("b4 req", des)
            # if des==None:
            #     pass
            # else:
            if des:
                subt = db.session.query(Subscription).filter(
                    Subscription.sub_desiid == des.desi_id,
                    Subscription.sub_status == 'active'
                ).first()
                apt = db.session.query(Bookappointment).filter_by(ba_desiid=des.desi_id).all()
                # print(f"b4 req {subt} and {apt}")
                today = date.today()
                if subt and subt.sub_enddate < str(today):
                    subt.sub_status = "deactive"
                    db.session.commit()
                    commenter_email = subt.subdesiobj.desi_email
                    custom = subt.subdesiobj.desi_businessName
                    recipients = {"custom": custom}
                    subdeactivate_signal.send(current_app, comment=subt,
                                            post_author_email=commenter_email,
                                            recipients=recipients)

                if subt and subt.sub_plan == 'free' and len(apt) == 0:
                        Dstart = date.today()
                        Dend = Dstart + timedelta(days=29)
                        # Update subscription details
                        subt.sub_startdate = Dstart
                        subt.sub_enddate = Dend
                        subt.sub_status = 'active'
                        db.session.commit()
                        commenter_email = subt.subdesiobj.desi_email
                        custom = subt.subdesiobj.desi_businessName
                        recipients = {"custom": custom}
                        subdeactivate_signal.send(current_app, comment=subt,
                                                post_author_email=commenter_email,
                                                recipients=recipients)
                else:
                    if subt and subt.sub_plan == 'free' and len(apt) == 3:
                        subt.sub_status = "deactive"
                        db.session.commit()
                        commenter_email = subt.subdesiobj.desi_email
                        custom = subt.subdesiobj.desi_businessName
                        recipients = {"custom": custom}
                        subdeactivate_signal.send(current_app, comment=subt, post_author_email=commenter_email, recipients=recipients)

        state = State.query.filter(State.state_id==des.desi_stateid).first()
        lg = Lga.query.filter(Lga.lga_id==des.desi_lgaid).first()
        page = request.args.get('page', 1, type=int)
        pos=Posting.query.filter(Posting.post_desiid==desi_loggedin, Posting.post_delete=='not deleted').order_by(desc(Posting.post_date)).paginate(page=page, per_page=30)
        # comnt = db.session.query(Comment).filter(Comment.com_postid == pos.post_id).order_by(Comment.path.asc()).all()
        getbk=Bookappointment.query.filter(Bookappointment.ba_desiid==desi_loggedin).order_by(desc(Bookappointment.ba_date)).paginate(page=page, per_page=20)
        subt=Subscription.query.filter(Subscription.sub_desiid==desi_loggedin, Subscription.sub_status=='active').first()
        noti = Notification.query.filter(Notification.notify_read=='unread',
        Notification.notify_desiid==des.desi_id).all()
        jb=Job.query.filter((Job.jb_status=='completed') |
                            (Job.jb_status=='collected'))\
                                .order_by(desc(Job.jb_date)).paginate(page=page, per_page=20)
        bnk=Bank.query.filter_by(bnk_desiid=desi_loggedin).first()
        bnkcode=Bankcodes.query.all()
        follow = Follow.query.filter_by(follow_desiid=desi_loggedin).all()

        return jsonify({
            "userId":desi_loggedin,
            "userType":user_type,
            "creator":{
                'designer_id': des.desi_id,
                'firstName': des.desi_fname,
                'lastName': des.desi_lname,
                'email': des.desi_email,
                'phone': des.desi_phone,
                'address': des.desi_address,
                'bio': des.desi_bio,
                'profile_pic': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{des.desi_pic}" if des.desi_pic else None,
                'gender':des.desi_gender,
                "businessName":des.desi_businessName,
                'registerDate':des.desi_regdate,
                'status': des.desi_status,
                'access': des.desi_access,
                'state': [{'id': state.state_id, 'name': state.state_name}],
                'lga': [{'id': lg.lga_id, 'name': lg.lga_name}]
            },

            "posts": [{
                "postId": po.post_id,
                "postTitle": po.post_title,
                "content": po.post_body,
                "date": po.post_date,
                "postSuspend": po.post_suspend,
                "postDelete": po.post_delete,
                "postCreator": po.designerobj.desi_businessName,
                "postImage": po.imagepostobj[0].image_name if po.imagepostobj else None,
                "postImageUrl": f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{po.imagepostobj[0].image_url}"
                                if po.imagepostobj else None,
                "Comment_Count": db.session.query(Comment).filter(Comment.com_postid == po.post_id).count(),
                "likes_Count": len(po.likes),
                "client_id_likes": [lke.like_custid if lke.like_custid else None for lke in po.likes],
                "creator_id_likes": [lke.like_desiid if lke.like_desiid else None for lke in po.likes],
                "shares_Count": len(po.sharepostobj),
                "post_comment": (lambda comments: [
                    {
                        "com_body": c.com_body,
                        "com_date": c.com_date.isoformat(),
                        "com_suspend": c.com_suspend,
                        "com_delete": c.com_delete,
                        "client_com": c.comcustobj.cust_username if c.comcustobj else "",
                        "creator_com": c.comdesiobj.desi_businessName if c.comdesiobj else "",
                        "replies": [
                            {
                                "com_body": r.com_body,
                                "com_date": r.com_date.isoformat(),
                                "com_suspend": r.com_suspend,
                                "com_delete": r.com_delete,
                                "client_com": r.comcustobj.cust_username if r.comcustobj else "",
                                "creator_com": r.comdesiobj.desi_businessName if r.comdesiobj else ""
                            }
                            for r in comments if r.path and r.path.startswith(str(c.com_id))
                        ]
                    }
                    for c in comments if c.path is None
                ])(
                    db.session.query(Comment)
                    .filter(Comment.com_postid == po.post_id)
                    .order_by(Comment.path.is_(None).desc(), Comment.path.asc())
                    .all()
                )
            } for po in pos.items],

            "bookings":[{
                'bookingId':bk.ba_id, 'date':bk.ba_date, 'bookingDate':bk.ba_bookingDate, 'bookingTime':bk.ba_bookingTime,
                "collectionTime":bk.ba_collectionTime, "collectionDate": bk.ba_collectionDate,
                "status":bk.ba_status,
                "collectionStatus": bk.ba_custstatus, "paymentStatus": bk.ba_paystatus,
                "reason": bk.ba_reason,
                "clientId": bk.custbaobj.cust_id,
                "clientUsername": bk.custbaobj.cust_username,
                "clientCountry":bk.custbaobj.custcountry.country_name,
                "clientPhone":bk.custbaobj.cust_phone, "clientfname":bk.custbaobj.cust_fname,
                "clientlname":bk.custbaobj.cust_lname
            } for bk in getbk.items],

            "subscription": [{"plan":"{:,.2f}".format(float(subt.sub_plan)), "date":subt.sub_date,"startDate":subt.sub_startdate,
            "endDate":subt.sub_enddate, "ref":subt.sub_ref,"status":subt.sub_status,
            "subpaystatus":subt.sub_paystatus}if subt else None],
            'notification':[{'noteid':nt.notify_id if nt.notify_id else None,
                             'noti_postid':nt.notify_postid if nt.notify_postid else None,
                             'noti_message':nt.notify_read if nt.notify_read else None,
                             'noti_date': nt.notify_date if nt.notify_date else None,
                             'noti_clientid':nt.notify_custid if nt.notify_custid else None, 
                             'noti_likeid':nt.notify_likeid if nt.notify_likeid else None, 
                             'noti_commentid':nt.notify_comid if nt.notify_comid else None, 
                             'noti_shareid':nt.notify_shareid if nt.notify_shareid else None, 
                             'noti_bookappointmentid':nt.notify_baid if nt.notify_baid else None, 
                             'noti_transaction_paymentid':nt.notify_tpayid if nt.notify_tpayid else None, 
                             'noti_transaction_payment_status':nt.notifytpayobj.tpay_status if nt.notifytpayobj else None, 
                             'noti_creatorid':nt.notify_desiid if nt.notify_desiid else None, 
                             'noti_creator_firstname':nt.notifydesiobj.desi_fname if nt.notifydesiobj else None, 
                             'noti_client_firstname':nt.notifycustobj.cust_fname if nt.notifycustobj else None, 
                             'noti_subscriptionid':nt.notify_subid if nt.notify_subid else None, 
                             'noti_subplan':nt.notifysubobj.sub_plan if nt.notifysubobj else None, 
                             'noti_sub_status':nt.notifysubobj.sub_status if nt.notifysubobj else None, 
                             'noti_paymentid':nt.notify_paymentid if nt.notify_paymentid else None, 
                             'noti_payment_status':nt.notifypayobj.payment_status if nt.notifypayobj else None } for nt in noti],
            "jobs": [{"jobPic":f"https://styleitafrica.pythonanywhere.com/static/images/completed_task/{pt.jb_pic}" if pt.jb_pic else None, "clientFirstName":pt.jbcustobj.cust_fname if pt.jbcustobj else None,
            "clientLastName":pt.jbcustobj.cust_lname if pt.jbcustobj else None, "date":pt.jb_date if pt else None,"status":pt.jb_status.title() if pt else None, } for pt in jb.items],
            "bank": [{"accountName":bnk.bnk_acname, "accountNo":bnk.bnk_acno, "bankName":bnk.bnk_bankname}if bnk else None],
            "bank_codes": [{"bank_id":bc.id, "bank_name":bc.name, "bank_code":bc.code} for bc in bnkcode],
            "follow": [{"followid": ff.follow_id,
                        "follow_creator": ff.desifollowobj.desi_businessName if ff.desifollowobj else None,
                        "follow_client": ff.custfollowobj.cust_username if ff.custfollowobj else None
                        }
                        for ff in follow],
            "follow_count": len(follow),
            "total_notification": len(noti)
        }), 200

    if request.method == 'PUT':
        data = request.json
        required_fields = ['fname', 'lname', 'email', 'phone', 'address']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        des = db.session.get(Designer, desi_loggedin)
        if not des:
            return jsonify({'error': 'Designer not found'}), 404

        des.desi_fname = data['fname']
        des.desi_lname = data['lname']
        des.desi_email = data['email']
        des.desi_phone = data['phone']
        des.desi_address = data['address']
        db.session.commit()

        return jsonify({'message': 'Profile updated successfully'}), 200


"""Designer update bio/description"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/updatebio/', methods=['PUT'])
@jwt_required()
def update_description_bio():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    # print(f"this is a user type {user_type} and this is id {desi_loggedin}")
    if user_type != 'designer':
        return jsonify({'error': 'Unauthorized access'}), 401
    last_active(desi_loggedin, user_type)
    if request.method == 'PUT':
        data = request.json
        description = data.get('bio')
        if not description:
            return jsonify({'error': 'Bio is required'}), 400

        des = db.session.get(Designer, desi_loggedin)
        if not des:
            return jsonify({'error': 'Designer not found'}), 404

        des.desi_bio = description
        db.session.commit()

        return jsonify({'message': 'Bio updated successfully'}), 200


"""Designer update about"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/about/', methods=['PUT'])
@jwt_required()
def update_about():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    # print(f"this is a user type {user_type} and this is id {desi_loggedin}")
    if user_type != 'designer':
        return jsonify({'error': 'Unauthorized access'}), 401
    last_active(desi_loggedin, user_type)
    if request.method == 'PUT':
        data = request.json
        description = data.get('about')
        if not description:
            return jsonify({'error': 'The about field is required'}), 400

        des = db.session.get(Designer, desi_loggedin)
        if not des:
            return jsonify({'error': 'Designer not found'}), 404

        des.desi_about = description
        db.session.commit()

        return jsonify({'message': 'About updated successfully'}), 200


"""update designer profile picture"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/update/profilepic', methods=['PUT'])
@jwt_required()
def update_designer_profile_pic():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if not desi_loggedin:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    if request.method == 'PUT':
        pic = request.files.get('pic')
        if not pic:
            return jsonify({'message': 'No file provided'}), 400

        original_name = pic.filename
        if original_name:
            extension = os.path.splitext(original_name)[1].lower()
            if extension in ['.jpg', '.gif', '.png']:
                fn = math.ceil(random.random() * 10000000000)
                saveas = f"{fn}{extension}"
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER2'], saveas)
                pic.save(save_path)

                designer = db.session.get(Designer, desi_loggedin)
                designer.desi_pic = saveas
                db.session.commit()

                return jsonify({'message': 'Profile picture updated successfully',
                                'profile_pic_url': f"https://styleitafrica.pythonanywhere.com/static/images/profile/designer/{saveas}"}), 200

        return jsonify({'message': 'Invalid file type'}), 400


"""designer logout session"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/logout', methods=['POST'])
@jwt_required()
def designer_logout():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if not desi_loggedin:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    jti = get_jwt()["jti"]
    session.pop('designer', None)

    lo = Login.query.filter_by(login_desiid=desi_loggedin, logout_date=None).first()
    if lo:
        db.session.add(TokenBlocklist(jti=jti, jti_desiid=desi_loggedin))
        db.session.commit()
        lo.logout_date = datetime.now(timezone.utc)
        db.session.commit()

    return jsonify({'message': 'Logout successful'}), 200


"""Posting section"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/posting', methods=['POST'])
@jwt_required()
def apiposting():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    if request.method == 'POST':
        designer = db.session.get(Designer, desi_loggedin)
        title = request.form.get('title')
        body = request.form.get('body')
        imgs = request.files.getlist('img')
        # print("this are the images sent",imgs)

        if not title or not body or not imgs:
            return jsonify({'message': 'Complete all fields'}), 400

        # Save post
        post = Posting(post_title=title, post_body=body, post_desiid=designer.desi_id)
        db.session.add(post)
        db.session.commit()

        # Fetch the newly created post
        created_post = Posting.query.filter_by(post_title=title,
                                               post_desiid=designer.desi_id).first()

        for img in imgs:
            original_name = img.filename
            if original_name:
                extension = os.path.splitext(original_name)[1].lower()
                if extension in ['.jpg', '.gif', '.png']:
                    fn = math.ceil(random.random() * 10000000000)
                    saveas = f"{fn}{extension}"
                    post_image_folder = current_app.config['POST_IMAGE']
                    os.makedirs(post_image_folder, exist_ok=True)
                    save_path = os.path.join(post_image_folder, saveas)
                    #save_path = f'styleitapp/static/images/postpic/{saveas}'

                    img.save(save_path)  # Save image to the specified path

                    # Save image details in the database
                    image_entry = Image(image_name=created_post.post_title,
                                        image_url=saveas,
                                        image_postid=created_post.post_id,
                                        Image_desiid=desi_loggedin)
                    db.session.add(image_entry)
        db.session.commit()

        return jsonify({
            'message': 'Post saved successfully',
            'post': {
                'id': created_post.post_id,
                'title': created_post.post_title,
                'body': created_post.post_body,
                'designer_id': created_post.post_desiid
            }
        }), 201


"""Accept/decline appointment"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/appointment/status/<int:id>', methods=['POST'])
@jwt_required()
def apiappointment_status(id):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    aptaction = request.json.get('action')
    if not aptaction:
        return jsonify({'message': 'Action is required'}), 400

    apptm = db.session.get(Bookappointment, id)
    if not apptm:
        return jsonify({'message': 'Appointment not found'}), 404

    if aptaction == "accept":
        apptm.ba_status = "accept"
        db.session.commit()

        commenter_email = apptm.custbaobj.cust_email
        recipients = {'custom': commenter_email}

        acceptappointment_signal.send(current_app, comment=apptm,
                                      post_author_email=commenter_email,
                                      recipients=recipients)

        return jsonify({'message': 'Appointment accepted'}), 200

    elif aptaction == "decline":
        res = request.json.get('reason')
        if not res:
            return jsonify({'message': 'Decline reason is required'}), 400

        apptm.ba_status = "decline"
        apptm.ba_reason = res
        db.session.commit()

        commenter_email = apptm.custbaobj.cust_email
        recipients = {'custom': commenter_email}

        declineappointment_signal.send(current_app, comment=apptm,
                                       post_author_email=commenter_email,
                                       recipients=recipients)

        return jsonify({'message': 'Appointment declined'}), 200

    return jsonify({'message': 'Invalid action'}), 400


"""subscription plans"""
@limiter.limit(laps)
@user_api_bp.route('/api/designer/subplan', methods=['GET'])
@jwt_required()
def apisubplan():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    designer = db.session.get(Designer, desi_loggedin)
    if not designer:
        return jsonify({'message': 'Designer not found'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 2, type=int)

    subscriptions = Subscription.query.filter_by(sub_desiid=desi_loggedin) \
                                      .order_by(desc(Subscription.sub_date)) \
                                      .paginate(page=page, per_page=per_page, error_out=False)

    noti = Notification.query.filter_by(notify_read='unread',
                                                  notify_desiid=designer.desi_id).all()

    return jsonify({
        'designer': {'id': designer.desi_id, 'firstName': designer.desi_fname,
                     'lastName': designer.desi_lname, 'businessName': designer.desi_businessName},
        'subscriptions': [
            {'id': sub.sub_id, 'date': sub.sub_date, 'plan': f"{float(sub.sub_plan):,.2f}",
             "startDate":sub.sub_startdate, "endDate":sub.sub_enddate,
             "status":sub.sub_status, "paymentStatus":sub.sub_paystatus, "refrence":sub.sub_ref}
            for sub in subscriptions.items
        ],
        'pagination': {
            'pages': subscriptions.page,
            'total_pages': subscriptions.pages,
            'total_items': subscriptions.total,
            'has_next': subscriptions. has_next,
            'per_page': per_page,
            'page':page
        },
        'notification':[{'noteid':nt.notify_id if nt.notify_id else None,
                         'noti_postid':nt.notify_postid if nt.notify_postid else None,
                         'noti_message':nt.notify_read if nt.notify_read else None,
                         'noti_date': nt.notify_date if nt.notify_date else None,
                         'noti_clientid':nt.notify_custid if nt.notify_custid else None, 
                         'noti_likeid':nt.notify_likeid if nt.notify_likeid else None, 
                         'noti_commentid':nt.notify_comid if nt.notify_comid else None, 
                         'noti_shareid':nt.notify_shareid if nt.notify_shareid else None, 
                         'noti_bookappointmentid':nt.notify_baid if nt.notify_baid else None, 
                         'noti_transaction_paymentid':nt.notify_tpayid if nt.notify_tpayid else None, 
                         'noti_transaction_payment_status':nt.notifytpayobj.tpay_status if nt.notifytpayobj else None, 
                         'noti_creatorid':nt.notify_desiid if nt.notify_desiid else None, 
                         'noti_creator_firstname':nt.notifydesiobj.desi_fname if nt.notifydesiobj else None, 
                         'noti_client_firstname':nt.notifycustobj.cust_fname if nt.notifycustobj else None, 
                         'noti_subscriptionid':nt.notify_subid if nt.notify_subid else None, 
                         'noti_subplan':nt.notifysubobj.sub_plan if nt.notifysubobj else None, 
                         'noti_sub_status':nt.notifysubobj.sub_status if nt.notifysubobj else None, 
                         'noti_paymentid':nt.notify_paymentid if nt.notify_paymentid else None, 
                         'noti_payment_status':nt.notifypayobj.payment_status if nt.notifypayobj else None } for nt in noti]
    }), 200


"""subscription"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/sub', methods=['POST'])
@jwt_required()
def apisubscribe():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    data = request.json
    plan = data.get('plan')

    if not plan:
        return jsonify({'message': 'Subscription plan is required'}), 400
    if plan not in ["free", "1000", "3000", "5000", "10000"]:
        return jsonify({"message": "invalid subscription plan"})
    
    if plan == 'free':
        refno = int(random.random() * 10000000)
        session['refno'] = refno

        # Create subscription entry
        sub = Subscription(sub_plan=plan, sub_ref=refno, sub_desiid=desi_loggedin,
                        sub_startdate=0, sub_enddate=0)
        db.session.add(sub)
        db.session.commit()

        # Fetch the created subscription
        created_sub = Subscription.query.filter_by(sub_ref=refno, sub_desiid=desi_loggedin).first()

        # Add notification for subscription
        notification_sub = Notification(notify_desiid=desi_loggedin, notify_subid=created_sub.sub_id,
                                        notify_read='unread')
        db.session.add(notification_sub)
        db.session.commit()
        payment = Payment(payment_transNo=refno, payment_amount="0.00",
                        payment_desiid=desi_loggedin, payment_subid=created_sub.sub_id)
        db.session.add(payment)
        db.session.commit()
        return redirect('/api/free/activate')
    else:
        refno = int(random.random() * 10000000)
        session['refno'] = refno

        # Create subscription entry
        sub = Subscription(sub_plan=plan, sub_ref=refno, sub_desiid=desi_loggedin,
                        sub_startdate=0, sub_enddate=0)
        db.session.add(sub)
        db.session.commit()

        # Fetch the created subscription
        created_sub = Subscription.query.filter_by(sub_ref=refno, sub_desiid=desi_loggedin).first()

        # Add notification for subscription
        notification_sub = Notification(notify_desiid=desi_loggedin, notify_subid=created_sub.sub_id,
                                        notify_read='unread')
        db.session.add(notification_sub)
        db.session.commit()

        # Create payment entry
        payment = Payment(payment_transNo=refno, payment_amount=plan,
                        payment_desiid=desi_loggedin, payment_subid=created_sub.sub_id)
        db.session.add(payment)
        db.session.commit()

        # Add notification for payment
        created_payment = Payment.query.filter_by(payment_transNo=refno, payment_desiid=desi_loggedin).first()
        notification_payment = Notification(notify_desiid=desi_loggedin,
                                            notify_paymentid=created_payment.payment_id,
                                            notify_read='unread')
        db.session.add(notification_payment)
        db.session.commit()

        return jsonify({
            'message': 'Subscription initiated successfully',
            'subscription': {
                'id': created_sub.sub_id,
                'plan': created_sub.sub_plan,
                'reference': created_sub.sub_ref
            },
            'payment': {
                'id': created_payment.payment_id,
                'transaction_no': created_payment.payment_transNo,
                'amount': created_payment.payment_amount
            }
        }), 201


""" payment """
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/payment', methods=['POST'])
@jwt_required()
def apipayment():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    refno = request.json.get('refno')
    # print(refno)
    # refno = session.get('refno')
    if not refno:
        return jsonify({'message': 'No reference number found in session'}), 400

    pymt = Payment.query.filter_by(payment_transNo=refno).first()
    # print(pymt)
    if not pymt:
        return jsonify({'message': 'Payment record not found'}), 404

    designer = db.session.get(Designer, desi_loggedin)
    if not designer:
        return jsonify({'message': 'Designer not found'}), 404

    data = {
        "email": designer.desi_email,
        "amount": pymt.payment_amount * 100,  # Convert to kobo (for NGN)
        "reference": pymt.payment_transNo
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {spamming}"
    }

    response = requests.post('https://api.paystack.co/transaction/initialize',
                             headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        rspjson = response.json()
        if rspjson.get('status') is True:
            return jsonify({'authorization_url': rspjson['data']['authorization_url']}), 200
        else:
            return jsonify({'message': 'Failed to initialize payment',
                            'error': rspjson.get('message')}), 400
    else:
        return jsonify({'message': 'Payment gateway error'}), 500


@limiter.limit(laps)
@user_api_bp.route("/api/user/payverify/", methods=["GET"])
def apipaystack():
    reference = request.args.get('reference')
    # refno = session.get('refno')

    if not reference:
        return jsonify({'message': 'Reference number is missing'}), 400

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {spamming}"
    }

    response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)

    if response.status_code != 200:
        return jsonify({'message': 'Error verifying payment'}), 500

    rsp = response.json()

    if rsp.get('data', {}).get('status') == 'success':
        amt = rsp['data']['amount']
        ipaddress = rsp['data']['ip_address']

        p = Payment.query.filter_by(payment_transNo=reference).first()

        if p:
            p.payment_status = 'paid'
            db.session.commit()
            # session['refnoo']=reference
            token = create_access_token(
                identity=str(reference),
                expires_delta=timedelta(minutes=2)
            )
            token2 = create_access_token(
                identity=f"designer:{p.payment_desiid}",
                expires_delta=timedelta(minutes=2)
            )
            act_url = url_for('user_api.apiactivating', jwt=token, access_token=token2, _external=True)
            return redirect(act_url), 302
            #return jsonify({'message': 'Payment successful', 'status': 'paid',
                            #'amount': amt, 'ip': ipaddress}), 200

        tpay = Transaction_payment.query.filter_by(tpay_transNo=reference).first()
        if tpay:
            bk = Bookappointment.query.filter_by(ba_id=tpay.tpay_baid).first()
            tpay.tpay_status = 'paid'
            bk.ba_paystatus = 'paid'
            db.session.commit()
            # return jsonify({'message': 'Transaction payment successful', 'status': 'paid',
                            # 'amount': amt, 'ip': ipaddress}), 200
            return redirect(f'localhost:5173/client/payverify?trxref={tpay.tpay_transNo}& reference={tpay.tpay_transNo}'), 302
        
    else:
        p = Payment.query.filter_by(payment_transNo=reference).first()
        tpay = Transaction_payment.query.filter_by(tpay_transNo=reference).first()

        if p:
            p.payment_status = 'failed'
            db.session.commit()
            return jsonify({'message': 'Payment failed', 'status': 'failed'}), 400

        elif tpay:
            bk = Bookappointment.query.filter_by(ba_id=tpay.tpay_baid).first()
            tpay.tpay_status = 'failed'
            bk.bk_paystatus = 'failed'
            db.session.commit()
            return jsonify({'message': 'Transaction payment failed', 'status': 'failed'}), 400


@limiter.limit(laps)
@user_api_bp.route('/api/activate', methods=['GET'])
def apiactivating():
    """
    Accept two independent tokens:
      STRICT MODE:
    - Requires TWO tokens:
        1) Query-string JWT (?jwt=...) → contains payment reference
        2) Header JWT (Authorization: Bearer ...) → contains 'designer:ID'
    """

    # === REQUIRE BOTH TOKENS ===
    payment_jwt = request.args.get('jwt')
    auth_header = request.args.get('access_token')

    if not payment_jwt or not auth_header:
        return jsonify({
            'message': 'Both payment token (jwt) and authorization token are required'
        }), 400

    # === VERIFY PAYMENT JWT (query string) ===
    try:
        verify_jwt_in_request(locations=['query_string'])
        ref_identity = get_jwt_identity()
    except Exception:
        return jsonify({'message': 'Invalid or expired payment token'}), 400

    # === VERIFY USER JWT (header) ===
    try:
        # verify_jwt_in_request(locations=['headers'])
        decoded_access = decode_token(auth_header)
        user_identity= decoded_access["sub"]
        # user_identity = get_jwt_identity()
    except Exception:
        return jsonify({'message': 'Invalid or expired authorization token'}), 401

    # === EXTRACT REFERENCE NUMBER ===
    try:
        refno = int(ref_identity)
    except (TypeError, ValueError):
        return jsonify({'message': 'Invalid payment reference token'}), 400

    # === EXTRACT USER IDENTITY ===
    if not isinstance(user_identity, str) or ':' not in user_identity:
        return jsonify({'message': 'Invalid user token format'}), 400

    user_type, user_id = user_identity.split(':', 1)

    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 401
    last_active(user_id, user_type)
    try:
        desi_loggedin = int(user_id)
    except ValueError:
        return jsonify({'message': 'Invalid user id in token'}), 400

    # === LOOK UP SUBSCRIPTION ===
    substat = Subscription.query.filter_by(sub_ref=refno).first()
    if not substat:
        return jsonify({'message': 'Subscription not found'}), 404

    # === ENSURE SUB BELONGS TO THIS DESIGNER ===
    if int(substat.sub_desiid) != desi_loggedin:
        return jsonify({'message': 'This subscription does not belong to you'}), 403

    # === VALIDATE PLAN ===
    plan_durations = {
        'free': 29,
        '1000': 29,
        '3000': 89,
        '5000': 179,
        '10000': 364
    }

    if substat.sub_plan not in plan_durations:
        return jsonify({'message': 'Invalid subscription plan'}), 400

    # === ACTIVATE SUBSCRIPTION ===
    Dstart = date.today()
    Dend = Dstart + timedelta(days=plan_durations[substat.sub_plan])

    substat.sub_startdate = Dstart
    substat.sub_enddate = Dend
    substat.sub_status = 'active'
    substat.sub_paystatus = 'paid'
    db.session.commit()

    # === SEND NOTIFICATION (SAFE) ===
    commenter = Payment.query.filter_by(
        payment_desiid=desi_loggedin,
        payment_transNo=refno
    ).first()

    if commenter and commenter.desipaymentobj:
        commenter_email = commenter.desipaymentobj.desi_email
        custom = commenter.desipaymentobj.desi_businessName
        recipients = {"custom": custom}

        subactivate_signal.send(
            current_app,
            comment=commenter,
            post_author_email=commenter_email,
            recipients=recipients
        )
    refresh_token = create_refresh_token(identity=f"designer:{desi_loggedin}")
    # === RESPONSE ===
    return jsonify({
        'message': 'Activation successful',
        'creatorid': desi_loggedin,
        'status': 'active',
        'plan': substat.sub_plan,
        'start_date': str(Dstart),
        'end_date': str(Dend),
        'access_token':auth_header,
        'refresh_token': refresh_token
    }), 200



@limiter.limit(laps)
@user_api_bp.route('/api/free/activate', methods=['GET'])
# @jwt_required(locations=["query_string", "headers"])
@jwt_required()
def apifreeactivating():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    refno = session.get('refno')
    if not refno:
        return jsonify({'message': 'Reference number not found in session'}), 400

    substat = Subscription.query.filter_by(sub_ref=refno).first()
    if not substat:
        return jsonify({'message': 'Subscription not found'}), 404

    # Define subscription durations
    plan_durations = {
        'free':29,
        '1000': 29,
        '3000': 89,
        '5000': 179,
        '10000': 364
    }

    if substat.sub_plan not in plan_durations:
        return jsonify({'message': 'Invalid subscription plan'}), 400
    
    # Activate subscription
    Dstart = date.today()
    Dend = Dstart + timedelta(days=plan_durations[substat.sub_plan])

    # Update subscription details
    substat.sub_startdate = Dstart
    substat.sub_enddate = Dend
    substat.sub_status = 'active'
    substat.sub_paystatus = 'paid'
    db.session.commit()

    # Notify the user
    commenter = Subscription.query.filter_by(sub_desiid=desi_loggedin, sub_plan='free').first()
    commenter_email = commenter.subdesiobj.desi_email
    custom = commenter.subdesiobj.desi_businessName
    recipients = {"custom": custom}
    free_subactivate_signal.send(current_app, comment=commenter, post_author_email=commenter_email,
                            recipients=recipients)

    return jsonify({
        'message': 'Activation successful',
        'status': 'active',
        'plan': substat.sub_plan,
        'start_date': str(Dstart),
        'end_date': str(Dend)
    }), 200


"""confim work done"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/complete_task/<int:id>/', methods=['POST'])
@jwt_required()
def apicomplete_task(id):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(desi_loggedin, user_type)
    # Get form data
    custid = request.form.get('custid')
    lev = request.form.get('status')
    pic = request.files.get('pic')

    if not custid or not lev or not pic:
        return jsonify({'message': 'One or more fields are empty'}), 400

    # Validate image extension

    original_name = pic.filename
    extension = os.path.splitext(original_name)[1].lower()
    if extension not in ['.jpg', '.gif', '.png']:
        return jsonify({'message': 'Invalid file format. Only JPG, GIF, PNG allowed'}), 400

    # Generate a random filename and save the image
    fn = math.ceil(random.random() * 10000000000)
    saveas = f"{fn}{extension}"
    image_path = os.path.join(current_app.config['COMPLETE_TASK'], saveas)
    pic.save(image_path)

    # Save task completion details
    new_job = Job(jb_status=lev, jb_pic=saveas, jb_custid=custid,jb_desiid=desi_loggedin, jb_baid=id)
    db.session.add(new_job)
    db.session.commit()

    # Update the appointment status
    appointment = db.session.get(Bookappointment, id)
    if appointment:
        appointment.ba_status = lev
        db.session.commit()

    # Send notification
    commenter_email = new_job.jbcustobj.cust_email
    completetask_signal.send(current_app, comment=new_job, post_author_email=commenter_email)

    return jsonify({
        'message': 'Task completed successfully',
        'task_id': new_job.jb_baid,
        'status': lev,
        'image_url': f"https://styleitafrica.pythonanywhere.com/static/images/completed_task/{saveas}"
    }), 200


"confirming task delevery"
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/confirm_delivery/<int:id>/', methods=['GET','POST'])
@jwt_required()
def apiconfirm_delivery(id):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(logged_in, user_type)

    if request.method == 'GET':
        cus=db.session.get(Customer, logged_in)
        jb=Job.query.filter(Job.jb_baid==id).first() if id else None
        return jsonify({
            'customer': cus.cust_name,
            'job_creator_id': jb.jb_desiid if jb else None,
            'task_image_url': f"https://styleitafrica.pythonanywhere.com/static/images/completed_task/{jb.jb_pic}" if jb else None
        }), 200

    if request.method == 'POST':
        # Get JSON data
        data = request.json
        desiid = data.get('desiid')
        status = data.get('custstatus')

        if not desiid or not status:
            return jsonify({'message': 'One or more fields are empty'}), 400

        # Update appointment status
        bk = db.session.get(Bookappointment, id)
        if bk is None:
            return jsonify({'message': 'Appointment not found'}), 404

        bk.ba_custstatus = status
        db.session.commit()

        # Update job status
        jb = Job.query.filter_by(jb_baid=id).first()
        if jb is None:
            return jsonify({'message': 'Job not found'}), 404

        jb.jb_status = status
        db.session.commit()

        # Send notification
        commenter_email = jb.jbdesiobj.desi_email
        confirmdelivery_signal.send(current_app, comment=jb, post_author_email=commenter_email)

        return jsonify({
            'message': "Thank you! You've confirmed a job well done for quality service.",
            'job_id': jb.jb_baid,
            'status': status
        }), 200


"""payment page for customer"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/custpayment/<int:id>/', methods=['POST'])
@jwt_required()
def apicustpayment(id):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(logged_in, user_type)
    cus = db.session.get(Customer, logged_in)
    if cus is None:
        return jsonify({'message': 'Customer not found'}), 404

    # Get JSON data
    data = request.json
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    if not id:
        return jsonify({'message': 'Appointment ID is required'}), 400

    sender = data.get('custid')
    receiver = data.get('desiid')
    amt = data.get('amount')
    charges = data.get('charges')

    if not sender or not receiver or not amt or not charges:
        return jsonify({'message': 'One or more fields are missing'}), 400

    try:
        # Generate a transaction reference number
        refno = int(random.random() * 10000000)
        session['refno'] = refno
        total_amount = int(amt) + int(charges)
        currency = "NGN" if cus.cust_countryid == 161 else "$"

        # Create transaction payment
        tpay = Transaction_payment(
            tpay_transNo=refno,
            tpay_custid=sender,
            tpay_desiid=receiver,
            tpay_amount=total_amount,
            tpay_baid=id,
            tpay_currencyicon=currency
        )
        db.session.add(tpay)
        db.session.commit()

        # Create notification
        pp = Transaction_payment.query.filter_by(tpay_transNo=refno, tpay_custid=int(logged_in)).first()
        notification = Notification(
            notify_custid=cus.cust_id,
            notify_tpayid=pp.tpay_id,
            notify_read='unread'
        )
        db.session.add(notification)
        db.session.commit()

        return jsonify({
            'message': 'Payment initiated successfully',
            'transaction_id': pp.tpay_id,
            'reference_no': refno,
            'total_amount': total_amount,
            'currency_icon': currency,
            'redirect to': f'/api/confirm_payment/{id}/'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error processing payment: {str(e)}'}), 500


""" customer payment """
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/confirm_payment/<int:id>/', methods=['GET','POST'])
@jwt_required()
def apiconfirm_custpayment(id):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Unauthorized access'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403
    last_active(logged_in, user_type)
    # Retrieve customer and appointment
    cus = db.session.get(Customer, logged_in)
    bk = db.session.get(Bookappointment, id)

    if not cus or not bk:
        return jsonify({'message': 'Invalid request or session expired'}), 400

    if request.method=='GET':
        refnot = session.get('refno')
        if not refnot:
            return jsonify({'message': 'Invalid request or session expired'}), 400

        # Fetch the payment record
        pymt = Transaction_payment.query.filter_by(tpay_transNo=refnot).first()
        if not pymt:
            return jsonify({'message': 'Transaction not found'}), 404

        return jsonify({
            'transaction_id': pymt.tpay_id,
            'reference_no': pymt.tpay_transNo,
            'total_amount': pymt.tpay_amount,
            'currency_icon': pymt.tpay_currencyicon,
            })

    if request.method=='POST':
        data = request.json
        refno = data.get('refno')
        if not refno:
            return jsonify({'message': 'Session expired, please retry'}), 400

        pymt = Transaction_payment.query.filter_by(tpay_transNo=refno).first()
        if not pymt:
            return jsonify({'message': 'Transaction not found'}), 404
        # Check if already paid
        if pymt.tpay_status == "paid":
            return jsonify({'message': 'Payment already confirmed'}), 200

        # Prepare data for Paystack API request
        payment_data = {
            "email": cus.cust_email,
            "amount": pymt.tpay_amount * 100,  # Paystack requires amount in kobo
            "reference": pymt.tpay_transNo
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {spamming}"
        }

        # Send request to Paystack API
        try:
            response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                headers=headers,
                data=json.dumps(payment_data)
            )
            rspjson = response.json()

            if rspjson.get('status') is True:
                return jsonify({
                    'message': 'Payment initialized successfully',
                    'authorization_url': rspjson['data']['authorization_url']
                }), 201
            else:
                return jsonify({'message': 'Payment initialization failed',
                                'error': rspjson.get('message')}), 400
        except requests.exceptions.RequestException as e:
            return jsonify({'message': 'Payment request failed', 'error': str(e)}), 500



"""Error 404 page"""
@user_api_bp.errorhandler(404)
def page_not_found(error):
    # verify_jwt_in_request(optional=True)

    # identity = get_jwt_identity()

    # if not identity:
    #     return jsonify({'message': 'Unauthorized access'}), 401

    # user_type, userid = identity.split(':') if identity else (None, None)

    # # Unauthorized access
    # if not (
    #     (user_type == 'designer' and userid is not None) or
    #     (user_type == 'customer' and userid is not None)
    # ):
    #     return jsonify({'message': 'Unauthorized access'}), 401

    # if user_type == 'designer':
    #     desi_loggedin = userid
    #     logged_in = None
    # else:
    #     logged_in = userid
    #     desi_loggedin = None

    # # Retrieve user details
    # des = db.session.get(Designer, desi_loggedin) if desi_loggedin else None
    # cus = db.session.get(Customer, logged_in) if logged_in else None

    # # Fetch notifications
    # noti = []
    # if desi_loggedin:
    #     noti = Notification.query.filter_by(notify_read='unread', notify_desiid=des.desi_id).all()
    # elif logged_in:
    #     noti = Notification.query.filter(
    #         (Notification.notify_postid != None) |
    #         (Notification.notify_likeid != None) |
    #         (Notification.notify_baid != None) |
    #         (Notification.notify_comid != None) |
    #         (Notification.notify_paymentid != None) |
    #         (Notification.notify_shareid != None) |
    #         (Notification.notify_subid != None),
    #         Notification.notify_read == 'unread',
    #         Notification.notify_custid == cus.cust_id
    #     ).all()

    # # Convert notifications to a list of dictionaries
    # notifications = [{'noti_postid':nt.notify_postid if nt.notify_postid else None,
    #                   'noti_date': nt.notify_date if nt.notify_date else None, 
    #                   'noti_message':nt.notify_read if nt.notify_read else None,
    #                   'noti_clientid':nt.notify_custid if nt.notify_custid else None, 
    #                   'noti_likeid':nt.notify_likeid if nt.notify_likeid else None, 
    #                   'noti_commentid':nt.notify_comid if nt.notify_comid else None, 
    #                   'noti_shareid':nt.notify_shareid if nt.notify_shareid else None, 
    #                   'noti_bookappointmentid':nt.notify_baid if nt.notify_baid else None, 
    #                   'noti_transaction_paymentid':nt.notify_tpayid if nt.notify_tpayid else None, 
    #                   'noti_transaction_payment_status':nt.notifytpayobj.tpay_status if nt.notifytpayobj else None, 
    #                   'noti_creatorid':nt.notify_desiid if nt.notify_desiid else None, 
    #                   'noti_creator_firstname':nt.notifydesiobj.desi_fname if nt.notifydesiobj else None, 
    #                   'noti_client_firstname':nt.notifycustobj.cust_fname if nt.notifycustobj else None, 
    #                   'noti_subscriptionid':nt.notify_subid if nt.notify_subid else None, 
    #                   'noti_subplan':nt.notifysubobj.sub_plan if nt.notifysubobj else None, 
    #                   'noti_sub_status':nt.notifysubobj.sub_status if nt.notifysubobj else None, 
    #                   'noti_paymentid':nt.notify_paymentid if nt.notify_paymentid else None, 
    #                   'noti_payment_status':nt.notifypayobj.payment_status if nt.notifypayobj else None } for nt in noti]

    return jsonify({
        'message': 'Page not found',
        'error': str(error) if error is not None else None,
        # 'notifications': notifications
    }), 404



"""the search section"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/postsearch/', methods=['POST'])
@jwt_required()
def search_results():
    identity = get_jwt_identity()
    if not identity:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_type, userid = identity.split(':') if identity else (None, None)

    # Unauthorized access
    if not (
        (user_type == 'designer' and userid is not None) or
        (user_type == 'customer' and userid is not None)
    ):
        return jsonify({'message': 'Unauthorized access'}), 401

    if user_type == 'designer':
        desi_loggedin = userid
        logged_in = None
    else:
        logged_in = userid
        desi_loggedin = None
    last_active(userid, user_type)
    word = request.json.get('search')

    if not word:
        return jsonify({'message': 'Search term is required'}), 400

    page = request.args.get('page', 1, type=int)  # Get page number from query params
    pattern = f'%{word}%'

    # Perform search in Posting and Designer tables
    wordsearch = (Posting.query
                .outerjoin(Designer, Posting.post_desiid == Designer.desi_id)
                .outerjoin(State, Designer.desi_stateid == State.state_id)
                .outerjoin(Lga, Designer.desi_lgaid == Lga.lga_id)
                .filter(or_(
                    Posting.post_title.ilike(pattern),
                    Posting.post_body.ilike(pattern),
                    Designer.desi_businessName.ilike(pattern),
                    Designer.desi_fname.ilike(pattern),
                    Designer.desi_lname.ilike(pattern),
                    Designer.desi_state.ilike(pattern),
                    Designer.desi_city.ilike(pattern),
                    Lga.lga_name.ilike(pattern),
                    State.state_name.ilike(pattern)
                ))
                .order_by(desc(Posting.post_id))
                .paginate(page=page, per_page=50, error_out=False))

    # Format search results
    search_results = [{
        'id': pot.post_id,
        'title': pot.post_title,
        'content': pot.post_body,
        "created_at": pot.post_date.isoformat(),
        "creator_pic": f"https://styleitafrica.pythonanywhere.com/static/images/designerpic/{pot.designerobj.desi_pic}" if pot.designerobj and pot.designerobj.desi_pic else None,
        "status": pot.post_suspend,
        "delete": pot.post_delete,
        "likes_Count": len(pot.likes),
        "shares_Count": len(pot.sharepostobj),
        "Comment_Count": len(pot.postcomobj),
        "image": [
            {
                "imageUrl": f"https://styleitafrica.pythonanywhere.com/static/images/postpic/{img.image_url}",
                "imageName": img.image_name
            } for img in pot.imagepostobj
        ] if pot.imagepostobj else [],
        "client_id_likes": [lke.like_custid if lke.like_custid else None for lke in pot.likes],
        "creator_id_likes": [lke.like_desiid if lke.like_desiid else None for lke in pot.likes],
        "businessname": pot.designerobj.desi_businessName if pot.designerobj else None,
        'first_name': pot.designerobj.desi_fname if pot.designerobj else None,
        'last_name': pot.designerobj.desi_lname if pot.designerobj else None,
        'international_state': pot.designerobj.desi_state if pot.designerobj else None,
        'international_city': pot.designerobj.desi_city if pot.designerobj else None,
        'lga': pot.designerobj.lgaobj2.lga_name if pot.designerobj and pot.designerobj.lgaobj2 else None,
        'state': pot.designerobj.stateobj2.state_name if pot.designerobj and pot.designerobj.stateobj2 else None
    } for pot in wordsearch.items]
    message = (
        'Search completed successfully'
        if wordsearch.total > 0
        else 'No posts matched your search'
    )
    return jsonify({
        'message': message,
        'query': word,
        'total_results': wordsearch.total,
        'total_pages': wordsearch.pages,
        'current_page': wordsearch.page,
        'results': search_results,
        'desi_loggedin': desi_loggedin if desi_loggedin else None,
        'logged_in': logged_in if logged_in else None
    }), 200


"""Search section"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/search_creator/', methods=['POST'])
def api_desisearch():
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
                 ),
                 Subscription.sub_status == 'active'
             )
             .order_by(desc(Designer.desi_id))
             .paginate(page=page, per_page=50, error_out=False))
    # print(wordsearch)

    # Format search results
    search_results = [{
        'id': desi.desi_id,
        'business_name': desi.desi_businessName,
        'first_name': desi.desi_fname,
        'last_name': desi.desi_lname,
        'bio': desi.desi_bio,
        'creator_pic': f"https://styleitafrica.pythonanywhere.com/static/images/designerpic/{desi.desi_pic}" if desi.desi_pic else None,
        'about': desi.desi_about,
        'state': desi.stateobj2.state_name if desi.stateobj2 else None,
        'city': desi.desi_city,
        'lga': desi.lgaobj2.lga_name if desi.lgaobj2 else None
    } for desi in wordsearch.items]

    if wordsearch.total==0:
        return jsonify({
            'message': 'No Creator Found',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results
        }), 200
    else:
        return jsonify({
            'message': 'Search completed successfully',
            'query': word,
            'total_results': wordsearch.total,
            'total_pages': wordsearch.pages,
            'current_page': wordsearch.page,
            'results': search_results
        }), 200


"""delete section"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/trashit/', methods=['POST', 'DELETE'])
@jwt_required()
def trash_post():
    if request.method in ['POST', 'DELETE']:
        identity = get_jwt_identity()
        user_type, desi_loggedin = identity.split(':') if identity else (None, None)

        if desi_loggedin is None:
            return jsonify({'error': 'Unauthorized. Please log in as a designer.'}), 401
        if user_type != 'designer':
            return jsonify({'error': 'Unauthorized. You can only delete posts as a designer.'}), 403
        last_active(desi_loggedin, user_type)
        postid = request.json.get('postid')  # Expecting JSON request
        if not postid:
            return jsonify({'error': 'Post ID is required'}), 400

        # Find the post
        post = Posting.query.filter_by(post_id=postid).first()
        # print(type(post.post_desiid))
        # print(type(desi_loggedin))
        # print(f"This is post id: {post.post_desiid} and current loggedin user id: {desi_loggedin} this is under post query")
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Ensure the designer owns the post
        if int(post.post_desiid) != int(desi_loggedin):
            # print(f"This is post id: {post.post_desiid} and current desiloggedin user id: {desi_loggedin} this is under checking equality")
            return jsonify({'error': 'Unauthorized. You can only delete your own posts.'}), 403

        # Mark as deleted
        post.post_delete = 'deleted'
        db.session.commit()

        return jsonify({'message': 'Post successfully deleted'}), 200


"""Report post """
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/report/', methods=['POST'])
@jwt_required()
def create_report():
    identity = get_jwt_identity()
    if not identity:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_type, userid = identity.split(':') if identity else (None, None)

    # Unauthorized access
    if not (
        (user_type == 'designer' and userid is not None) or
        (user_type == 'customer' and userid is not None)
    ):
        return jsonify({'message': 'Unauthorized access Please log in'}), 401

    if user_type == 'designer':
        desi_loggedin = int(userid)
        logged_in = None
    else:
        logged_in = int(userid)
        desi_loggedin = None
    last_active(userid, user_type)
    data = request.json
    custid = data.get('custid')
    desid = data.get('desid')
    custname = data.get('custname')
    desname = data.get('desname')
    reason = data.get('report')

    if not reason or (not desid and not custid):
        return jsonify({'error': 'Missing required fields'}), 400

    if logged_in:
        report = Report(report_reason=reason, report_desiid=desid, reporter=custname)
    elif desi_loggedin:
        if custid:
            report = Report(report_reason=reason, report_custid=custid, reporter=desname)
        else:
            report = Report(report_reason=reason, report_desiid=desid, reporter=desname)

    db.session.add(report)
    db.session.commit()

    return jsonify({'message': 'Report logged successfully'}), 201


"""Rating"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/rating/', methods=['POST'])
@jwt_required()
def apirate():
    identity = get_jwt_identity()
    if not identity:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_type, userid = identity.split(':') if identity else (None, None)

    # Unauthorized access
    if not (
        (user_type == 'designer' and userid is not None) or
        (user_type == 'customer' and userid is not None)
    ):
        return jsonify({'message': 'Unauthorized access Please log in'}), 401

    if user_type == 'designer':
        desi_loggedin = userid
        logged_in = None
    else:
        logged_in = userid
        desi_loggedin = None
    last_active(userid, user_type)
    data = request.json
    reason = data.get('rate')
    custid = data.get('custid')
    desid = data.get('desid')

    if not reason or not custid or not desid:
        return jsonify({"error": "One or more fields are empty"}), 400

    if desi_loggedin == int(desid):
        return jsonify({"error": "You can't rate yourself"})

    if str(custid) != str(logged_in):
        return jsonify({"error": "Customer ID mismatch"}), 403

    rating = Rating(rat_rating=reason, rat_custid=logged_in, rat_desiid=desid)

    db.session.add(rating)
    db.session.commit()
    return jsonify({"message": "Thank you for the review", "status": "success"}), 201


"""newsletter section"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/newsletter/', methods=['POST'])
# @jwt_required()
def apinewsletter():
    data = request.json
    name = data.get('name')
    email = data.get('email')

    if not name or not email:
        return jsonify({"error": "One or more fields are empty"}), 400

    existing_newsletter = Newsletter.query.filter_by(news_email=email).first()
    if existing_newsletter:
        return jsonify({"message": "You have already subscribed to our newsletter"}), 200

    new_subscription = Newsletter(news_name=name, news_email=email)
    db.session.add(new_subscription)
    db.session.commit()

    return jsonify({"message": "You have successfully subscribed to our newsletter"}), 201


"""Bank details"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/designer/bankdetail/', methods=['POST'])
@jwt_required()
def apibank_detail():
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)

    if desi_loggedin is None:
        return jsonify({"error": "Unauthorized access"}), 401
    if user_type != 'designer':
        return jsonify({"error": "Unauthorized access. You can only add bank details as a designer."}), 403
    last_active(desi_loggedin, user_type)
    data = request.json
    name = data.get('name')
    bkname = data.get('bank')
    acno = data.get('acno')

    if not name or not bkname or not acno:
        return jsonify({"error": "One or more fields are empty"}), 400

    bnk = Bank(bnk_acname=name, bnk_bankname=bkname, bnk_acno=acno, bnk_desiid=desi_loggedin)
    db.session.add(bnk)
    db.session.commit()

    return jsonify({"message": "Thank you! Your bank details have been saved."}), 201


"""Follow session"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/follow/<int:id>/', methods=['POST'])
@jwt_required()
def apifollow(id):
    # print(f"This is header request: {request.headers}")
    # print(f"This is cookies request: {request.cookies}")
    # print(f"This is json request: {request.json}")

    identity = get_jwt_identity()
    if not identity:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_type, userid = identity.split(':') if identity else (None, None)

    # Unauthorized access
    if not (
        (user_type == 'designer' and userid is not None) or
        (user_type == 'customer' and userid is not None)
    ):
        return jsonify({'message': 'Unauthorized access Please log in'}), 401

    if user_type == 'designer':
        desi_loggedin = userid
        logged_in = None
    else:
        logged_in = userid
        desi_loggedin = None
    last_active(userid, user_type)
    existing_follow = Follow.query.filter_by(follow_desiid=id,follow_custid=logged_in).first()

    if existing_follow:
        return jsonify({
            "status": "exists",
            "message": "You already follow this designer."
        }), 200

    new_follower = Follow(follow_desiid=id, follow_custid=logged_in)
    db.session.add(new_follower)
    db.session.commit()

    return jsonify({"message": "You are now following this designer.", "client_id":logged_in, "creator_id": desi_loggedin}), 201


"""Unfollow session"""
@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route('/api/unfollow/<int:id>/', methods=['POST'])
@jwt_required()
def apiunfollow(id):
    identity = get_jwt_identity()
    if not identity:
        return jsonify({'message': 'Unauthorized access'}), 401

    user_type, userid = identity.split(':') if identity else (None, None)

    # Unauthorized access
    if not (
        (user_type == 'designer' and userid is not None) or
        (user_type == 'customer' and userid is not None)
    ):
        return jsonify({'message': 'Unauthorized access Please log in'}), 401

    if user_type == 'designer':
        desi_loggedin = userid
        logged_in = None
    else:
        logged_in = userid
        desi_loggedin = None
    last_active(userid, user_type)
    follower = Follow.query.filter_by(follow_desiid=id, follow_custid=logged_in).first()
    if not follower:
        return jsonify({"error": "You are not following this designer."}), 400

    db.session.delete(follower)
    db.session.commit()

    return jsonify({"message": "You have unfollowed this designer.", "client_id":logged_in, "creator_id": desi_loggedin}), 200


@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route("/api/user/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    old_jti = get_jwt()["jti"]
    if logged_in:
        # Blacklist old refresh token
        db.session.add(TokenBlocklist(jti=old_jti, jti_custid=int(logged_in)))
        db.session.commit()

        # Issue new tokens
        new_access = create_access_token(identity=f"customer:{logged_in}")
        new_refresh = create_refresh_token(identity=f"customer:{logged_in}")

        # Update last_active_at
        last_active(userid, user_type)

        access_token=new_access,
        refresh_token=new_refresh
        # Return to frontend
        return jsonify({
            "access_token":access_token,
            "refresh_token":refresh_token
        })
    if desi_loggedin:
        # Blacklist old refresh token
        db.session.add(TokenBlocklist(jti=old_jti, jti_desiid=int(desi_loggedin)))
        db.session.commit()

        # Issue new tokens
        new_access = create_access_token(identity=f"designer:{desi_loggedin}")
        new_refresh = create_refresh_token(identity=f"designer:{desi_loggedin}")

        # Update last_active_at
        last_active(userid, user_type)

        access_token=new_access,
        refresh_token=new_refresh
        # Return to frontend
        return jsonify({
            "access_token":access_token,
            "refresh_token":refresh_token
        })
    

"""Touch last active"""
def last_active(id, usertype):
    userid=int(id)
    user_type=str(usertype)

    if user_type == 'designer':
        desi_loggedin = userid
        logged_in = None
    else:
        logged_in = userid
        desi_loggedin = None

    if desi_loggedin:
        login = (
            Login.query
            .filter(Login.login_desiid == desi_loggedin, Login.logout_date == None)
            .order_by(Login.login_date.desc())
            .first()
        )
        
    else:
        login = (
            Login.query.filter(Login.login_custid == logged_in, Login.logout_date == None)
            .order_by(Login.login_date.desc())
            .first()
        )
    
    if login:
        login.last_active_at = datetime.now()
        db.session.commit()
    return  True


@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route("/api/forgot-password", methods=["POST"])
def forgot_password():

    email = request.json.get("email")

    desi = Designer.query.filter_by(desi_email=email).first()
    cust = Customer.query.filter_by(cust_email=email).first()
    
    if desi:
        send_password_reset_email(desi)
        return jsonify({
            "message": "If the email exists, a reset link has been sent."
        }), 200
    elif cust:
        send_customer_password_reset_email(cust)
        return jsonify({
            "message": "If the email exists, a reset link has been sent."
        }), 200
    else:
        return jsonify({
        "message": "email does not exist"
        }), 200


@limiter.limit(laps)
@csrf.exempt
@user_api_bp.route("/api/reset-password/<token>", methods=["POST"])
def reset_password(token):

    email_dict = confirm_password_reset_token(token)
    email = email_dict.get("email")
    if not email:
        return jsonify({"message": "Invalid or expired token"}), 400

    designer = Designer.query.filter_by(desi_email=email).first()
    customer = Customer.query.filter_by(cust_email=email).first()
    user = designer or customer
    if not user:
        return jsonify({"message": "User not found"}), 404

    now = datetime.now()

    # Check if user is currently locked
    if user.reset_locked_until and now < user.reset_locked_until:
        return jsonify({
            "message": f"Too many attempts. Try again after {user.reset_locked_until}"
        }), 429


    # Check attempts within 1 minute
    if user.reset_attempt_time and now - user.reset_attempt_time < timedelta(minutes=1):

        user.reset_attempts += 1

        if user.reset_attempts >= 5:
            user.reset_locked_until = now + timedelta(minutes=15)
            db.session.commit()

            return jsonify({
                "message": "Too many reset attempts. Try again in 15 minutes."
            }), 429

    else:
        # reset attempt window
        user.reset_attempts = 1
        user.reset_attempt_time = now

    data = request.json
    new_password = data.get("pwd")
    confirm_pwd = data.get("cpwd")

    if len(new_password) < 8:
        return jsonify({'message': 'Password should be at least 8 characters long',
                        'status': 'error'}), 400

    if confirm_pwd != new_password:
        return jsonify({"message":"password does not match", 'status': 'error'}), 400
    
    hashed_password = generate_password_hash(new_password)

    if designer:
        designer.desi_pass = hashed_password
        designer.desi_password_changed_at = datetime.now()
        db.session.commit()
        return jsonify({"message": "Password reset successful"}), 200
    elif customer:
        customer.cust_pass = hashed_password
        customer.cust_password_changed_at = datetime.now()
        db.session.commit()
        return jsonify({"message": "Password reset successful"}), 200
    else:
        return jsonify({"message": "Password reset unsuccessful"}), 404


"""Rate limit exceeded handler"""
@user_api_bp.errorhandler(429)
def ratelimit_exceeded(e):
    return jsonify({"error": "Too many requests. Please try again later."}), 429


"""

signals connects signals connects signals connects
signals connects signals connects signals connects
signals connects signals connects signals connects
signals connects signals connects signals connects

"""
@comment_signal.connect
def send_comment_email_alert(sender, comment, post_author_email):
    subject = f"StyleitHQ: {(comment.comcustobj.cust_fname if comment.comcustobj else 'A Client')} commented on your post"
    body = (
        f"Hi {(comment.compostobj.designerobj.desi_businessName if comment.compostobj else 'Creator')}, \n\n"
        f"{(comment.comcustobj.cust_fname if comment.comcustobj else 'A client')} commented on your post: \n"
        f"{comment.com_body} \n\n"
        f"Visit: https://www.styleit.africa/api/post/{comment.com_postid}/ \n\n"
        f"StyleitHQ")
    send_email_alert(subject, body, [post_author_email])


@reply_signal.connect
@jwt_required()
def send_reply_email_alert(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    if desi_loggedin:
        subject = f"StyleitHQ: {(comment.comdesiobj.desi_businessName if comment.comdesiobj else 'A Creator')} replied to your comment"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n{(comment.comdesiobj.desi_businessName if comment.comdesiobj else'A Creator')}"
                f"replied to your comment: \n {comment.com_body} \n\n"
                f"Visit: https://www.styleit.africa/api/post/{comment.com_postid}/ \n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])
    elif logged_in:
        subject = f"StyleitHQ: {(comment.comcustobj.cust_fname if comment.comcustobj else 'A Client')} replied to your comment"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n {(comment.comcustobj.cust_fname if comment.comcustobj else 'A Client')}"
                f"replied to your comment: \n {comment.com_body}"
                f"\n\n Visit: https://www.styleit.africa/api/post/{comment.com_postid}/ \n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])


@like_signal.connect
@jwt_required()
def send_like_email_alert(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    if desi_loggedin:
        subject = f"StyleitHQ: {(comment.desilikesobj.desi_businessName if comment.desilikesobj else 'A Creator' )} like your post"
        body = (f"Hi {recipients['custom']},\n\n{(comment.desilikesobj.desi_businessName if comment.desilikesobj else 'A Creator')}"
                f"like your post: \n\n Visit: https://www.styleit.africa/api/post/{comment.like_postid}/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])
    elif logged_in:
        subject = f"StyleitHQ: {(comment.custlikesobj.cust_fname if comment.custlikesobj else 'A Client')} like your post"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Bubby' )},\n\n {(comment.custlikesobj.cust_fname if comment.custlikesobj else 'A Client')}"
                f"like your post:  \n\n Visit: https://www.styleit.africa/api/post/{comment.like_postid}/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])


@unlike_signal.connect
@jwt_required()
def send_unlike_email_alert(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    if desi_loggedin:
        subject = f"StyleitHQ: {(comment.desilikesobj.desi_businessName if comment.desilikesobj else 'A Creator')} unlike your post"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n{(comment.desilikesobj.desi_businessName if comment.desilikesobj else 'A Creator')} unlike your post:"
                f"\n\n Visit: https://www.styleit.africa/api/post/{comment.like_postid}/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])
    elif logged_in:
        subject = f"StyleitHQ: {(comment.custlikesobj.cust_fname if comment.custlikesobj else 'A Client')} unlike your post"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n {(comment.custlikesobj.cust_fname if comment.custlikesobj else 'A Client')} unlike your post:"
                f"\n\n Visit: https://www.styleit.africa/api/post/{comment.like_postid}/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])

@subactivate_signal.connect
def send_subactivate_email_alart(sender, comment, post_author_email, recipients):
    subject = f"Subcription Alert by StyleitHQ"
    body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n You have successfully subscribe to a new plan"
            f"\n\n Your subscription details is as shown below"
            f"\n plan: {comment.subpaymentobj.sub_plan}"
            f"\n Sub Start Date: {comment.subpaymentobj.sub_startdate}"
            f"\n Sub End Date: {comment.subpaymentobj.sub_enddate} \n Thank you for doing business with us."
            f"\n\n Visit: https://www.styleit.africa/api/designer/subplan/"
            f"\n\n StyleitHQ Team" )
    send_email_alert(subject, body, [post_author_email])

@free_subactivate_signal.connect
def send_free_subactivate_email_alart(sender, comment, post_author_email, recipients):
    subject = f"Subcription Alert by StyleitHQ"
    body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n You have successfully subscribe to a free plan"
            f"\n\n Your subscription details is as shown below"
            f"\n plan: {comment.sub_plan}"
            f"\n Sub Start Date: {comment.sub_startdate}"
            f"\n Sub End Date: {comment.sub_enddate} \n Thank you for doing business with us."
            f"\n\n Visit: https://www.styleit.africa/api/designer/subplan/"
            f"\n\n StyleitHQ Team" )
    send_email_alert(subject, body, [post_author_email])

@subdeactivate_signal.connect
def send_subdeactivate_email_alart(sender, comment, post_author_email, recipients):
    subject = f"Subcription Alert by StyleitHQ"
    body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n Your subscription have been deactivated."
            f"\n Kindly click the link below to subscribe. \n Thank you for doing business with us."
            f"\n\n Visit: https://www.styleit.africa/api/designer/subplan/ \n\n StyleitHQ Team")
    send_email_alert(subject, body, [post_author_email])

@share_signal.connect
@jwt_required()
def send_share_email_alart(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()  # Get the current logged-in user
    user_type, userid = identity.split(':') if identity else (None, None)
    if user_type not in ['customer', 'designer'] or not userid:
        return jsonify({'error': 'Unauthorized'}), 401
    if user_type == 'customer':
        logged_in = userid
        desi_loggedin = None
    else:
        logged_in = None
        desi_loggedin = userid

    if desi_loggedin:
        subject = f"StyleitHQ: {(comment.desishareobj.desi_businessName if comment.desishareobj else 'A Creator')} shared your post"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n{(comment.desishareobj.desi_businessName if comment.desishareobj else 'A Creator')} shared your post:"
                f"\n\n Visit: https://www.styleit.africa/api/post/{comment.share_postid}/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])
    elif logged_in:
        subject = f"StyleitHQ: {(comment.custshareobj.cust_fname if comment.custshareobj else 'A Client')} shared your post"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n {(comment.custshareobj.cust_fname if comment.custshareobj else 'A Client')} shared your post:"
                f"\n\n Visit: https://www.styleit.africa/api/post/{comment.share_postid}/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])


@bookappointment_signal.connect
@jwt_required()
def send_bookappointment_email_alart(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if logged_in:
        subject = f"StyleitHQ: {(comment.custbaobj.cust_fname if comment.custbaobj else 'A Client')} booking appointment"
        body = (f"Hi {(recipients['custom'] if recipients['custom'] else 'Buddy')},\n\n {(comment.custbaobj.cust_fname if comment.custbaobj else 'A Client')} needs your service."
                f"\n Kindly visit the link below to respond to the appointment"
                f"\n\n Visit: https://www.styleit.africa/api/designer/profile/"
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])

@acceptappointment_signal.connect
@jwt_required()
def send_acceptappointment_email_alart(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if desi_loggedin:
        subject = f"StyleitHQ: Booking Appointment Update!"
        body = (f"Hi {(comment.custbaobj.cust_fname if comment.custbaobj else 'Client')},"
                f"\n\n {(comment.desibaobj.desi_businessName if comment.desibaobj else 'The Creator')} has accepted your appointment."
                f"\n Kindly visit the link below to respond to the appointment status"
                f"\n\n Visit: https://www.styleit.africa/api/customer/profile/"
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@declineappointment_signal.connect
@jwt_required()
def send_declineappointment_email_alart(sender, comment, post_author_email, recipients):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if desi_loggedin:
        subject = f"StyleitHQ: Booking Appointment Update!"
        body = (f"Hi {(comment.custbaobj.cust_fname if comment.custbaobj else 'Client')},"
                f"\n\n {(comment.desibaobj.desi_businessName if comment.desibaobj else 'The Creator')} has decline your appointment with the"
                f"below response: \n {comment.ba_reason}. \n\n Kindly visit the link below to book"
                f"new appointment \n\n Visit: https://www.styleit.africa/api/bookappointment/"
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@completetask_signal.connect
@jwt_required()
def send_completetask_email_alart(sender, comment, post_author_email):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if desi_loggedin:
        subject = f"StyleitHQ: Job Update!"
        body = (f"Hi {(comment.jbcustobj.cust_fname if comment.jbcustobj else 'Client')},\n\n {(comment.jbdesiobj.desi_businessName if comment.jbdesiobj else 'The Creator')}"
                f"has completed your task. \n Kindly use the link below to approve delivery"
                f"and collection \n\n Visit: https://www.styleit.africa/api/customer/profile/"
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@confirmdelivery_signal.connect
@jwt_required()
def send_confirmdelivery_email_alart(sender, comment, post_author_email):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if logged_in:
        subject = f"StyleitHQ: Job Update!"
        body = (f"Hi {(comment.jbdesiobj.desi_businessName if comment.jbdesiobj else 'A Creator')},\n\n {(comment.jbcustobj.cust_fname if comment.jbcustobj else 'A Client')}"
                f"has confirm your task delivery. Kindly await your payment from Styleit HQ once"
                f"payment is confirmed.\n Kindly use the link below to view details."
                f"\n\n Visit: https://www.styleit.africa/api/customer/profile/"
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])

@follow_signal.connect
@jwt_required()
def send_follow_email_alart(sender, comment, post_author_email):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if logged_in:
        subject = f"StyleitHQ: {(comment.custfollowobj.cust_fname if comment.custfollowobj else 'A Client' )} follow you"
        body = (f"Hi {(comment.desifollowobj.desi_businessName if comment.desifollowobj else 'A Creator')},"
                f"\n\n {(comment.custfollowobj.cust_fname if comment.custfollowobj else 'A Client')} started following you for updates."
                f"\n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])

@unfollow_signal.connect
@jwt_required()
def send_unfollow_email_alart(sender, comment, post_author_email):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if logged_in:
        subject = f"StyleitHQ: {(comment.custfollowobj.cust_fname if comment.custfollowobj else 'A Client')} unfollow you"
        body = (f"Hi {(comment.desifollowobj.desi_businessName if comment.desifollowobj else 'A Creator')},"
                f"\n\n {(comment.custfollowobj.cust_fname if comment.custfollowobj else 'A Client')} just unfollowing you."
                f"Don't feel down everyone have there reasons, just keep up the"
                f"good work to gain more followers. \n Thanks."
                f"\n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@payment_signal.connect
@jwt_required()
def send_payment_email_alart(sender, comment, post_author_email):
    identity = get_jwt_identity()
    user_type, desi_loggedin = identity.split(':') if identity else (None, None)
    if desi_loggedin is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'designer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if desi_loggedin:
        subject = f"StyleitHQ: {(comment.desipaymentobj.desi_bussinessName if comment.desipaymentobj else 'Your')} payment update"
        body = (f"Hi {(comment.desipaymentobj.desi_businessName if comment.desipaymentobj else 'Creator')},"
                f"\n\n Your payment for the subscription is successful."
                f"\n\n Kindly check the subscription plan for update.. \n Thanks."
                f"\n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])

@transpay_signal.connect
@jwt_required()
def send_transpay_signal_email_alart(sender, comment, post_author_email):
    identity = get_jwt_identity()
    user_type, logged_in = identity.split(':') if identity else (None, None)
    if logged_in is None:
        return jsonify({'message': 'Not logged in'}), 401
    if user_type != 'customer':
        return jsonify({'message': 'Unauthorized access'}), 403

    if logged_in:
        subject = f"StyleitHQ: {(comment.custtpayobj.cust_fname if comment.custtpayobj else 'Your')} payment update"
        body = (f"Hi {(comment.custtpayobj.cust_fname if comment.custtpayobj else 'Client' )},"
                f"\n\n Your payment for the negotiated {(comment.desitpayobj.desi_businessName if comment.desitpayobj else 'Creator')}"
                f"payment was successful. Your total charges for payment is  {(comment.tpay_amount if comment else '.')}."
                f"\n Thanks. \n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


