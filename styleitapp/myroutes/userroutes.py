import re, os, math, random, json, requests
from datetime import datetime, date, timedelta
from sqlalchemy import desc, func, extract, text
from flask import Blueprint, current_app, render_template, request, redirect, flash, session, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
# from flask_share import Share
# from flask_socketio import emit, disconnect
from styleitapp import db
from styleitapp.models import (Designer, State, Customer, Posting, Image, Comment, Like, 
                               Share, Bookappointment, Subscription, Payment, Notification,
                               Report, Rating, Newsletter, Job, Transaction_payment, Bank,
                               Follow, Login, Bankcodes, State, Lga, Countries, States, Cities)
from styleitapp.junk import styleit, spamming
from styleitapp.forms import CustomerLoginForm, DesignerLoginForm
from styleitapp import mail
from styleitapp.mytoken import generate_confirmation_token, confirm_token
from styleitapp.mail_utils import send_email, send_email_alert
from styleitapp.signals import (comment_signal, reply_signal, like_signal, unlike_signal, 
                               subactivate_signal, subdeactivate_signal, payment_signal, 
                               transpay_signal, share_signal, bookappointment_signal, 
                               declineappointment_signal, acceptappointment_signal, 
                               completetask_signal, confirmdelivery_signal, follow_signal, 
                               unfollow_signal)

user_bp = Blueprint("user", __name__, url_prefix="")

"""homepage"""
@user_bp.route('/')
def home():
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus=Customer.query.get(loggedin)
    
    if desiloggedin:
        return redirect('/designer/profile/')
    elif loggedin:
        return redirect('/customer/profile/')
    else:  
        today = date.today()
        print(str(today))
        if today:
            subt=db.session.query(Subscription).filter(Subscription.sub_status=='active', 
                                                       Subscription.sub_enddate ==str(today)).all()
            
            if subt != None:
                for su in subt:
                    su.sub_status='deactive'
                    db.session.commit()
                    
                    commenter_email=su.subdesiobj.desi_email
                    custom=su.subdesiobj.desi_businessName
                    recipients={"custom":custom}
                    subdeactivate_signal.send(current_app, comment=su, 
                                              post_author_email=commenter_email, 
                                              recipients=recipients)
            else:
                pass   
        return render_template('user/index.html', cus=cus, des=des)


"""login"""
@user_bp.route('/login/')
def login():
    loggedin = session.get('customer')
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    cus=Customer.query.get(loggedin)
    return render_template('user/login.html', cus=cus, des=des)

""" loading local govt area using ajax"""
@user_bp.route('/load/lga/', methods=['POST'])
def lgacheck():
    state=request.form.get('stateid')
    # querying lga table
    lg=db.session.execute(text(f"SELECT * FROM lga WHERE lga_stateid={state}"))
    results = lg.fetchmany(20)
    # building html tags for lga
    select_html = "<select>"
    for x,y,z in results:
        select_html = select_html + f"<option value='{x}'>{y}</option>"
    select_html = select_html + "</select>"
    return select_html


"""Country Check"""
@user_bp.route('/countrycheck/', methods=['POST'])
def countrycheck():
    countryid=request.form.get('countryid')
    cn=Countries.query.filter_by(country_id=countryid).first()
    msg=cn.country_name
    return jsonify(msg)


"""Trending section"""
@user_bp.route('/trending/', methods=['GET', 'POST'])
def trending():
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')

    if request.method == "GET":
        cus=Customer.query.get(loggedin)
        des=Designer.query.get(desiloggedin)
        today = date.today()
        
        page = request.args.get('page', 1, type=int)
        offset = (page - 1) * 10
        # offset = request.args.get('offset', 0, type=int)
        pstn = fetch_posts(offset)
        has_more = len(pstn) == 10
        
        lk=Like.query.filter(Like.like_postid==Posting.post_id).all()
        if desiloggedin:
            noti = Notification.query.filter(Notification.notify_read=='unread', 
                                             Notification.notify_desiid==desiloggedin).all()
        elif loggedin:
            noti = Notification.query.filter(Notification.notify_postid | Notification.notify_likeid | 
                                             Notification.notify_baid | Notification.notify_comid | 
                                             Notification.notify_paymentid | Notification.notify_shareid | 
                                             Notification.notify_subid, Notification.notify_read=='unread', 
                                             Notification.notify_custid==cus.cust_id).all()
        return render_template('user/trending.html', pstn=pstn, loggedin=loggedin, 
                               desiloggedin=desiloggedin, des=des, cus=cus, lk=lk, 
                               noti=noti, has_more=has_more, page=page, exclude_footer=True)


@user_bp.route('/loadmore')
def fetch_posts(offset):
    # today = date.today()
    
    """the main query for the production"""
    subq_likes = db.session.query(Like.like_postid, 
                                  func.count(Like.like_id).label('like_count')
                                  ).group_by(Like.like_postid).subquery()
    subq_comments = db.session.query(Comment.com_postid, 
                                     func.count(Comment.com_id).label('com_count')
                                     ).group_by(Comment.com_postid).subquery()
    subq_shares = db.session.query(Share.share_postid, 
                                   func.count(Share.share_id).label('share_count')
                                   ).group_by(Share.share_postid).subquery()

    """query post with daily rank"""
    # pstn = (db.session.query(Posting)
    #         .outerjoin(subq_likes, Posting.post_id==subq_likes.c.like_postid)
    #         .outerjoin(subq_comments, Posting.post_id==subq_comments.c.com_postid)
    #         .outerjoin(subq_shares, Posting.post_id==subq_shares.c.share_postid)
    #         .filter(extract('day', Posting.post_date) == extract('day', today), 
    #                 extract('month', Posting.post_date) == extract('month', today), 
    #                 extract('year', Posting.post_date) == extract('year', today), 
    #                 Posting.post_suspend=='unsuspended')
    #         .order_by(desc(subq_likes.c.like_count), desc(subq_comments.c.com_count), 
    #                   desc(subq_shares.c.share_count), desc(Posting.post_date))
    #         .offset(offset).all())

    """query post without daily rank"""    
    pstn = (db.session.query(Posting)
            .outerjoin(subq_likes, Posting.post_id==subq_likes.c.like_postid)
            .outerjoin(subq_comments, Posting.post_id==subq_comments.c.com_postid)
            .outerjoin(subq_shares, Posting.post_id==subq_shares.c.share_postid)
            .filter(Posting.post_id==Image.image_postid)
            .order_by(desc(subq_likes.c.like_count), desc(subq_comments.c.com_count), 
                      desc(subq_shares.c.share_count), desc(Posting.post_date))
            .offset(offset).all())
    return pstn


""" post detail session """
@user_bp.route('/post/<id>/')
def post(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')

    if request.method == 'GET':
        des=Designer.query.get(desiloggedin)
        cus = Customer.query.get(loggedin)
        pstn=db.session.query(Posting).filter(Posting.post_id==Image.image_postid, Posting.post_id==id).first()
        compost = Posting.query.filter_by(post_id=id).first_or_404()
        comnt=db.session.query(Comment).filter(Comment.com_postid==
                                               compost.post_id).order_by(Comment.path.asc()).all()
        share = db.session.query(Share).filter(Share.share_postid==compost.post_id).all()
        lk=Like.query.filter(Like.like_postid==Posting.post_id).all()
        for i in lk:
            print(i)
        if desiloggedin:
            noti = Notification.query.filter(Notification.notify_read=='unread', 
                                             Notification.notify_desiid==desiloggedin).all()
        elif loggedin:
            noti = Notification.query.filter(Notification.notify_postid | Notification.notify_likeid | 
                                             Notification.notify_baid | Notification.notify_comid | 
                                             Notification.notify_paymentid | Notification.notify_shareid | 
                                             Notification.notify_subid, Notification.notify_read=='unread', 
                                             Notification.notify_custid==cus.cust_id).all()
        return render_template('user/post.html', loggedin=loggedin, desiloggedin=desiloggedin, 
                               des=des,cus=cus,comnt=comnt, pstn=pstn, share=share, 
                               i=i, noti=noti, exclude_footer=True)


"""post notification"""
@user_bp.route('/posti/<id>/')
def notepost(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus = Customer.query.get(loggedin)
    if desiloggedin:
        notif = db.session.query(Notification).filter(Notification.notify_postid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{id}/')
    elif loggedin:
        notif = db.session.query(Notification).filter(Notification.notify_postid==id, 
                                                      Notification.notify_custid==cus.cust_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{id}/')
        

"""Like notification"""      
@user_bp.route('/postlike/<id>/')
def notelike(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus = Customer.query.get(loggedin)
    if desiloggedin:
        lk=Like.query.filter(Like.like_id==id, Like.like_desiid==des.desi_id).first()
        posid=lk.like_postid
        notif = db.session.query(Notification).filter(Notification.notify_likeid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{posid}/')
    elif loggedin:
        lk=Like.query.filter(Like.like_id==id, Like.like_custid==cus.cust_id).first()
        posid=lk.like_postid
        notif = db.session.query(Notification).filter(Notification.notify_likeid==id, 
                                                      Notification.notify_custid==cus.cust_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{posid}/')


"""Reply notification"""
@user_bp.route('/postreply/<id>/')
def notereply(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus = Customer.query.get(loggedin)
    if desiloggedin:
        lk=Comment.query.filter(Comment.com_id==id, Comment.com_desiid==des.desi_id).first()
        posid=lk.com_postid
        notif = db.session.query(Notification).filter(Notification.notify_comid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{posid}/')
    elif loggedin:
        lk=Comment.query.filter(Comment.com_id==id, Comment.com_custid==cus.cust_id).first()
        posid=lk.com_postid
        notif = db.session.query(Notification).filter(Notification.notify_comid==id, 
                                                      Notification.notify_custid==cus.cust_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{posid}/')

"""share notification"""
@user_bp.route('/postshare/<id>/')
def noteshare(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus = Customer.query.get(loggedin)
    if desiloggedin:
        lk=Share.query.filter(Share.share_id==id, Share.share_desiid==des.desi_id).first()
        posid=lk.share_postid
        notif = db.session.query(Notification).filter(Notification.notify_shareid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{posid}/')
    elif loggedin:
        lk=Share.query.filter(Share.share_id==id, Share.share_custid==cus.cust_id).first()
        posid=lk.share_postid
        notif = db.session.query(Notification).filter(Notification.notify_shareid==id, 
                                                      Notification.notify_custid==cus.cust_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect(f'/post/{posid}/')


"""bookappointment notification"""
@user_bp.route('/bookapp/<id>/')
def notebookapp(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus = Customer.query.get(loggedin)
    if loggedin:
        notif = db.session.query(Notification).filter(Notification.notify_baid==id, 
                                                      Notification.notify_custid==cus.cust_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect('/customer/profile/')
    elif desiloggedin:
        notif = db.session.query(Notification).filter(Notification.notify_baid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect('/designer/profile/')
    

"""subscription notification"""
@user_bp.route('/notesub/<id>/')
def notesub(id):
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin:
        notif = db.session.query(Notification).filter(Notification.notify_subid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect('/designer/subplan/')


"""payment notification"""
@user_bp.route('/notepay/<id>/')
def notepay(id):
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin:
        notif = db.session.query(Notification).filter(Notification.notify_paymentid==id, 
                                                      Notification.notify_desiid==des.desi_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect('/designer/subplan/')

"""transaction payment notification"""
@user_bp.route('/notetpay/<id>/')
def notetpay(id):
    loggedin = session.get('customer')
    cus=Customer.query.get(loggedin)
    if loggedin:
        notif = db.session.query(Notification).filter(Notification.notify_tpayid==id, 
                                                      Notification.notify_custid==cus.cust_id, 
                                                      Notification.notify_read=='unread').first()
        notif.notify_read='read'
        db.session.commit()
        return redirect('/customer/profile/')



"""All Designers """
@user_bp.route('/alldesigners/', methods=['GET', 'POST'])
def designers():
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
        
    if request.method == 'GET':   
        des=Designer.query.get(desiloggedin)
        cus=Customer.query.get(loggedin)
        page = request.args.get('page', 1, type=int)
        design=Subscription.query.filter(Subscription.sub_status=='active').paginate(page=page, per_page=50)
        if desiloggedin:
            noti = Notification.query.filter(Notification.notify_read=='unread', 
                                             Notification.notify_desiid==desiloggedin).all()
        elif loggedin:
            noti = Notification.query.filter(Notification.notify_postid | Notification.notify_likeid | 
                                             Notification.notify_baid | Notification.notify_comid | 
                                             Notification.notify_paymentid | Notification.notify_shareid | 
                                             Notification.notify_subid, Notification.notify_read=='unread', 
                                             Notification.notify_custid==cus.cust_id).all()       
        return render_template('designer/alldesigners.html', design=design, des=des, cus=cus, noti=noti)


"""Designers Details """
@user_bp.route('/designer/<id>/', methods=['GET', 'POST'])
def desi_detail(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
        
    if request.method == 'GET':   
        des=Designer.query.get(desiloggedin)
        cus=Customer.query.get(loggedin)
        design=Designer.query.filter(Designer.desi_id==id).first()
        rating1=Rating.query.filter(Rating.rat_rating==1, Rating.rat_desiid==id).all()
        rating2=Rating.query.filter(Rating.rat_rating==2, Rating.rat_desiid==id).all()
        rating3=Rating.query.filter(Rating.rat_rating==3, Rating.rat_desiid==id).all()
        rating4=Rating.query.filter(Rating.rat_rating==4, Rating.rat_desiid==id).all()
        rating5=Rating.query.filter(Rating.rat_rating==5, Rating.rat_desiid==id).all()
        follow = Follow.query.filter_by(follow_desiid=id).all()
        is_following = False
        if loggedin:
            follower = Follow.query.filter_by(follow_custid=loggedin, follow_desiid=id).first()
            if follower:
                is_following = True
        return render_template('designer/designerdetail.html', design=design, des=des, 
                               cus=cus, desiloggedin=desiloggedin, loggedin=loggedin, 
                               rating1=rating1, rating2=rating2, rating3=rating3, rating4=rating4, 
                               rating5=rating5, is_following=is_following, follow=follow)

"""Comment session"""
@user_bp.route('/comment/<int:postid>/', methods=['GET', 'POST'])
def comment(postid):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
    
    if request.method == 'GET':
        return redirect('/trending/')

    if request.method == 'POST':
        if desiloggedin:
            des=Designer.query.get(desiloggedin)
            com=request.form.get('comment')
            comt=Comment.query.filter_by(com_body=com, com_postid=postid, 
                                         com_desiid=des.desi_id).first()
            if comt==None:
                m=Comment(com_body=com, com_postid=postid, com_desiid=des.desi_id)
                d=Notification(notify_desiid=des.desi_id, 
                               notify_postid=postid, notify_read='unread') 
                m.save()
                d.save()
                return redirect(f'/post/{postid}/')
            else:
                flash("You've commemted this before. Write another")
                return redirect(f'/post/{postid}/')

        elif loggedin:
            cus = Customer.query.get(loggedin)
            com=request.form.get('comment')
            comt=Comment.query.filter_by(com_body=com, com_postid=postid, com_custid=cus.cust_id).first()
            if comt==None:
                k=Comment(com_body=com, com_postid=postid, com_custid=cus.cust_id)
                d=Notification(notify_custid=cus.cust_id, notify_postid=postid, notify_read='unread') 
                k.save()
                d.save()
                commenter=k.query.filter_by(com_postid=postid).first()
                commenter_email=commenter.compostobj.designerobj.desi_email
                comment_signal.send(current_app, comment=k, post_author_email=commenter_email)
                return redirect(f'/post/{postid}/')
            else:
                flash("You've commemted this before. Write another")
                return redirect(f'/post/{postid}/')



"""Reply Session """
@user_bp.route('/reply/<int:postid>/<int:commentid>/', methods=['POST', 'GET'])
def reply(postid, commentid):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
    
    if request.method == 'GET':
        return redirect('/trending/')

    if request.method == 'POST':
        if desiloggedin:
            des=Designer.query.get(desiloggedin)
            repl=request.form.get('comrep')
            comt=Comment.query.filter_by(com_body=repl, com_postid=postid, 
                                         com_desiid=des.desi_id, parent_id=commentid).first()
            if comt==None:
                m=Comment(com_body=repl, com_postid=postid, com_desiid=des.desi_id, parent_id=commentid)
                m.save()
                d=Notification(notify_desiid=des.desi_id, notify_comid=commentid, notify_read='unread' ) 
                d.save()
                commenter=m.query.filter_by(com_postid=postid, parent_id=m.parent_id).first()
                dso=Comment.query.filter_by(com_postid=postid, com_id=commentid).first()
                custom=dso.comcustobj.cust_fname
                recipients={'custom':custom}
                commenter_email=dso.comcustobj.cust_email
                reply_signal.send(current_app, comment=m, post_author_email=commenter_email, recipients=recipients)
                return redirect(f'/post/{postid}/')
            else:
                flash("You've commemted this before. Write another")
                return redirect(f'/post/{postid}/')
            
        elif loggedin:
            cus = Customer.query.get(loggedin)
            repl=request.form.get('comrep')
            comt=Comment.query.filter_by(com_body=repl, com_custid=cus.cust_id, 
                                         com_postid=postid, parent_id=commentid).first()
            if comt==None:
                k=Comment(com_body=repl, com_postid=postid, com_custid=cus.cust_id, parent_id=commentid)
                k.save()
                d=Notification(notify_custid=cus.cust_id, notify_comid=commentid, notify_read='unread' ) 
                d.save()
                commenter=k.query.filter_by(com_postid=postid, parent_id=k.parent_id).first()
                dso=Comment.query.filter_by(com_postid=postid, com_id=commentid).first()
                custom=dso.condesiobj.desi_businessName
                recipients={'custom':custom}
                commenter_email=dso.comdesiobj.desi_email
                reply_signal.send(current_app, comment=k, post_author_email=commenter_email, recipients=recipients)
                return redirect(f'/post/{postid}/')
            else:
                flash("You've commemted this before. Write another")
                return redirect(f'/post/{postid}/')


"""like session"""
@user_bp.route('/like/<int:post_id>/', methods=['GET'])
def like(post_id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    post = Posting.query.filter_by(post_id=post_id).first()
    if desiloggedin:
        liking = Like.query.filter_by(like_desiid=desiloggedin, like_postid=post_id).first()
        if not post:
            flash('Post does not exit', category='error')
        elif liking:
            commenter=liking.query.filter_by(like_postid=post_id, like_desiid=desiloggedin).first()
            commenter_email=liking.posts.designerobj.desi_email
            custom=liking.posts.designerobj.desi_businessName
            recipients={"custom":custom}
            unlike_signal.send(current_app, comment=liking, post_author_email=commenter_email, recipients=recipients)
            db.session.delete(liking)
            db.session.commit()
            
        else:
            liking=Like(like_desiid=desiloggedin, like_postid=post_id)
            db.session.add(liking)
            db.session.commit()
            lk=liking.query.filter_by(like_postid=post_id, like_desiid=desiloggedin).first()
            d=Notification(notify_desiid=desiloggedin, notify_likeid=lk.like_id, notify_read='unread') 
            db.session.add(d)
            db.session.commit()
            
            commenter=liking.query.filter_by(like_postid=post_id, like_desiid=desiloggedin).first()
            commenter_email=liking.posts.designerobj.desi_email
            custom=liking.posts.designerobj.desi_businessName
            recipients={"custom":custom}
            like_signal.send(current_app, comment=liking, post_author_email=commenter_email, recipients=recipients)
        return redirect(f'/post/{post_id}/')
        
    elif loggedin:
        liking = Like.query.filter_by(like_custid=loggedin, like_postid=post_id).first()
        if not post:
            flash('Post does not exit', category='error')
        elif liking:
            commenter=liking.query.filter_by(like_postid=post_id, like_custid=loggedin).first()
            commenter_email=liking.posts.designerobj.desi_email
            custom=liking.posts.designerobj.desi_businessName
            recipients={"custom":custom}
            unlike_signal.send(current_app, comment=liking, post_author_email=commenter_email, recipients=recipients)
            db.session.delete(liking)
            db.session.commit()
        else:
            liking=Like(like_custid=loggedin, like_postid=post_id)
            db.session.add(liking)
            db.session.commit()
            lk=liking.query.filter_by(like_postid=post_id, like_desiid=desiloggedin).first()
            d=Notification(notify_custid=loggedin, notify_likeid=lk.like_id, notify_read='unread') 
            db.session.add(d)
            db.session.commit()
            commenter=liking.query.filter_by(like_postid=post_id, like_custid=loggedin).first()
            commenter_email=commenter.posts.designerobj.desi_email
            custom=liking.posts.designerobj.desi_businessName
            recipients={"custom":custom}
            like_signal.send(current_app, comment=liking, post_author_email=commenter_email, recipients=recipients)
        return redirect(f'/post/{post_id}/')

"""Share buttons"""
@user_bp.route('/share/', methods=['GET','POST'])
def share():
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin:
        name = request.form.get('name')
        postid = request.form.get('sharepost')
        user = request.form.get('user')
        if name !="" and postid !="" and user !="":
            sh=Share(share_webname=name, share_postid=postid, share_desiid=user)
            db.session.add(sh)
            db.session.commit()
            d=Notification(notify_desiid=user, notify_shareid=sh.share_id, notify_read='unread') 
            db.session.add(d)
            db.session.commit()
            commenter=Share.query.filter_by(share_postid=postid, share_desiid=desiloggedin).first()
            commenter_email=Share.postshareobj.designerobj.desi_email
            custom=Share.postshareobj.designerobj.desi_businessName
            recipients={"custom":custom}
            share_signal.send(current_app, comment=commenter, post_author_email=commenter_email, recipients=recipients)
            # return redirect(f'/post/{postid}')
            return ('', 204)
    elif loggedin:
        name = request.form.get('name')
        postid = request.form.get('sharepost')
        user = request.form.get('user')
        if name !="" and postid !="" and user !="":
            sh=Share(share_webname=name, share_postid=postid, share_custid=user)
            db.session.add(sh)
            db.session.commit()
            d=Notification(notify_custid=user, notify_shareid=sh.share_id, notify_read='unread') 
            db.session.add(d)
            db.session.commit()
            
            commenter=Share.query.filter_by(share_postid=postid, share_custid=loggedin).first()
            commenter_email=commenter.postshareobj.designerobj.desi_email
            custom=commenter.postshareobj.designerobj.desi_businessName
            recipients={"custom":custom}
            share_signal.send(current_app, comment=commenter, post_author_email=commenter_email, recipients=recipients)
            # return redirect(f'/post/{postid}')
            return ('', 204)

"""token confirmation"""
@user_bp.route('/confirm/<token>/')
def confirm_email(token):
    loggedin = session.get('customer')
    desiloggedin = session.get('designer')
    
    if loggedin:
        try:
            email= confirm_token(token)
        except:
            flash('the confirmation link is invalid or has expired', 'danger')
        cus = Customer.query.filter_by(cust_email=email).first_or_404()
        if cus.cust_status=='actived':
            flash('Account already confirmed. Please login.', 'success')
        else:
            cus.cust_status = 'actived'
            cus.cust_activationdate = datetime.now()
            db.session.commit()
            flash('You have confirmed your account', 'success')
            return redirect('/user/customer/login/')
    
    elif desiloggedin:
        try:
            email= confirm_token(token)
        except:
            flash('the confirmation link is invalid or has expired', 'danger')
        des = Designer.query.filter_by(desi_email=email).first_or_404()
        if des.desi_status=='actived':
            flash('Account already confirmed. Please login.', 'success')
        else:
            des.desi_status = 'actived'
            des.desi_activationdate = datetime.now()
            db.session.commit()
            flash('You have confirmed your account', 'success')
            return redirect('/user/designer/login/')
    return redirect('main.home')


""" unconfirmed token"""
@user_bp.route('/unconfirmed')
def unconfirmed():
    loggedin = session.get('customer')
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    cus=Customer.query.get(loggedin)
    if loggedin:
        cusi = Customer.query.filter_by(cust_id=loggedin).first_or_404()
        if cusi.cust_status=='actived':
            return redirect('/customer/profile/')
    elif desiloggedin:
        desi = Designer.query.filter_by(desi_id=desiloggedin).first_or_404()
        if desi.desi_status=='actived':
            return redirect('/designer/profile/')
    flash('Confirm your account!', 'warning')
    return render_template('user/unconfirmed.html', desiloggedin=desiloggedin, 
                           loggedin=loggedin, des=des, cus=cus)   


"""Resend activation"""
@user_bp.route('/resend/activation')
def resent_confirmation():
    loggedin = session.get('customer')
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    cus=Customer.query.get(loggedin)
    if loggedin:
        cus = Customer.query.filter_by(cust_id=loggedin).first_or_404()
        token = generate_confirmation_token(cus.cust_email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html = render_template('user/activate.html', confirm_url=confirm_url, cus=cus)
        subject = "Please confirm your email"
        send_email(cus.cust_email, subject, html)
        flash('A new confirmation mail has been sent.', 'success')
        return redirect(url_for('unconfirmed'))
    elif desiloggedin:
        des = Designer.query.filter_by(desi_id=desiloggedin).first_or_404()
        token = generate_confirmation_token(des.desi_email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html = render_template('user/activate.html', confirm_url=confirm_url, des=des)
        subject = "Please confirm your email"
        send_email(des.desi_email, subject, html)
        flash('A new confirmation mail has been sent.', 'success')
        return redirect(url_for('unconfirmed')) 
    return redirect('/unconfirmed')


# Customers sections
"""Custormer Signup"""
@user_bp.route('/user/customer/signup/', methods=['GET', 'POST'])
def customerSignup():
    loggedin = session.get('customer')
    cus=Customer.query.get(loggedin)
    state=State.query.all()
    natn=Countries.query.all()
    if loggedin:
        return redirect('/customer/profile/')

    if request.method == 'GET':
        return render_template('user/customersignup.html', state=state, cus=cus, natn=natn)

    if request.method == 'POST':
        fname=request.form.get('fname')
        country=request.form.get('country')
        fstate=request.form.get('fstate')
        cities=request.form.get('cities')
        lname=request.form.get('lname')
        username=request.form.get('username')
        email=request.form.get('email')
        phone=request.form.get('phone')
        pwd=request.form.get('pwd')
        cpwd=request.form.get('cpwd')
        address= request.form.get('address')
        stat=request.form.get('state')
        lga=request.form.get('lga')
        gender=request.form.get('gender')
        pic=request.files.get('pic')
        original_name=pic.filename

        if country == '161':
            if (fname=="" or lname=="" or username=="" or email=="" or 
                phone=="" or pwd=="" or cpwd=="" or address=="" or 
                stat=="" or lga=="" or gender=="" or country==""):
                flash('One or more field is empty', 'danger')
                return redirect('/user/customer/signup/')
        
            # checking length of password
            elif len(pwd) < 8:
                flash('Password should be atleast 8 character long', 'warning')
                return redirect('/user/customer/signup/')
            # compairing password match
            elif pwd !=cpwd:
                flash('Password match error', 'danger')
                return redirect('/user/customer/signup/')
            else:
                # spliting to check email extension
                mail = email.split('@')
                if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    flash('kindly provide a valid email', 'warning')
                    return redirect('/user/customer/signup/')
                else:
                    eemail = mail[0] + '@' + mail[1]
                    # hashing password
                    formated = generate_password_hash(pwd)
                    
                    # checking image field if empty
                    if original_name != "":
                        # spliting image path
                        extension = os.path.splitext(original_name)
                        if extension[1].lower() in ['.jpg', '.gif', '.png']:
                            fn=math.ceil(random.random()*10000000000)
                            saveas = str(fn) + extension[1]
                            pic.save(f'styleitapp/static/images/profile/customer/{saveas}')
                            # committing to Customer table
                            k=Customer(cust_fname=fname, cust_username=username, 
                                       cust_lname=lname, cust_gender=gender, 
                                       cust_phone=phone, cust_email=eemail, 
                                       cust_pass=formated, cust_address=address, 
                                       cust_pic=saveas, cust_stateid=stat, 
                                       cust_lgaid=lga, cust_countryid=country)
                            db.session.add(k)
                            db.session.commit()

                            token = generate_confirmation_token(k.cust_email)
                            confirm_url = url_for('confirm_email', token=token, _external=True)
                            html = render_template('user/activate.html', confirm_url=confirm_url)
                            subject = "Please confirm your email"
                            send_email(k.cust_email, subject, html)
                            flash('Profile setup completed. A confirmation mail has been sent via email', 
                                  'success')
                            return redirect(url_for('unconfirmed'))
                        return redirect('/user/customer/signup/')
        else:
            if (fname=="" or lname=="" or username=="" or email=="" or 
                phone=="" or pwd=="" or cpwd=="" or address=="" or 
                fstate=="" or cities=="" or gender=="" or country==""):
                flash('One or more field is empty', 'danger')
                return redirect('/user/customer/signup/')
        
            # checking length of password
            elif len(pwd) < 8:
                flash('Password should be atleast 8 character long', 'warning')
                return redirect('/user/customer/signup/')
            # compairing password match
            elif pwd !=cpwd:
                flash('Password match error', 'danger')
                return redirect('/user/customer/signup/')
            else:
                # spliting to check email extension
                mail = email.split('@')
                if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    flash('kindly provide a valid email', 'warning')
                    return redirect('/user/customer/signup/')
                else:
                    eemail = mail[0] + '@' + mail[1]
                    # hashing password
                    formated = generate_password_hash(pwd)
                    
                    # checking image field if empty
                    if original_name != "":
                        # spliting image path
                        extension = os.path.splitext(original_name)
                        if extension[1].lower() in ['.jpg', '.gif', '.png']:
                            fn=math.ceil(random.random()*10000000000)
                            saveas = str(fn) + extension[1]
                            pic.save(f'styleitapp/static/images/profile/customer/{saveas}')
                            # committing to Customer table
                            k=Customer(cust_fname=fname, cust_username=username, 
                                       cust_lname=lname, cust_gender=gender, 
                                       cust_phone=phone, cust_email=eemail, 
                                       cust_pass=formated, cust_address=address, 
                                       cust_pic=saveas, cust_state=fstate, 
                                       cust_city=cities, cust_countryid=country)
                            db.session.add(k)
                            db.session.commit()
                            ci=Cities(name=cities)
                            db.session.add(ci)
                            db.session.commit()
                            st=States(name=fstate)
                            db.session.add(st)
                            db.session.commit()

                            token = generate_confirmation_token(k.cust_email)
                            confirm_url = url_for('confirm_email', token=token, _external=True)
                            html = render_template('user/activate.html', confirm_url=confirm_url)
                            subject = "Please confirm your email"
                            send_email(k.cust_email, subject, html)
                            flash('Profile setup completed. A confirmation mail has been sent via email', 
                                  'success')
                            return redirect(url_for('unconfirmed'))
                        return redirect('/user/customer/signup/')


"""Custormer Login"""
@user_bp.route('/user/customer/login/', methods=['GET', 'POST'])
def customerLogin():
    loggedin = session.get('customer')       
    cus=Customer.query.get(loggedin)
    login = CustomerLoginForm()
    if loggedin:
        return redirect('/customer/profile/')
    # rendering login template
    if request.method == 'GET':
        return render_template('user/customerlogin.html', login=login, cus=cus)
        
    if request.method == 'POST':
        # getting form data
        email=request.form.get('email')
        pwd = request.form.get('pwd')
        # validating form data field
        if email=="" or pwd=="":
            flash('Invalid Credentials', 'danger')
            return redirect('/user/customer/login/')
        if email !="" or pwd !="":
            # quering Customer by filtering with email
            user=db.session.query(Customer).filter(Customer.cust_email==email).first()
            if user ==None:
                flash('kindly supply a valid credentials', 'warning')
                return render_template('user/customerlogin.html', login=login, user=user)
            else:
                formated_pwd=user.cust_pass
                # checking password hash
                checking = check_password_hash(formated_pwd, pwd)
                if checking:
                    session['customer']=user.cust_id
                    lo=Login(login_email=user.cust_email, login_custid=user.cust_id)
                    db.session.add(lo)
                    db.session.commit()
                    flash('Login successful, Click on your profile picture to see the side bar', 
                          'success')
                    return redirect('/customer/profile/')
                else:
                    flash('kindly supply a valid email address and password', 'warning')
                    return render_template('user/customerlogin.html', login=login, user=user)


"""Customer Forgotten Password"""
@user_bp.route('/user/customer/forgottenpassword/', methods=['POST', 'GET'])
def customerforgottenpass():
    loggedin = session.get('customer')
    if loggedin:
        return redirect('/customer/profile/')
    if request.method == "GET":
        return render_template('user/forgottenpassword.html')
    if request.method == "POST":
        username=request.form.get('username')
        email=request.form.get('email')
        pwd=request.form.get('pwd')
        cpwd=request.form.get('cpwd')
       
        #validating fileds
        if username =="" or email =="" or pwd =="" or cpwd =="":
            flash('One or more field is empty', 'warning')
            return render_template('user/forgottenpassword.html')
        elif pwd != cpwd:
            flash('invalid credential supplied', 'danger')
            return redirect('/user/customer/forgottenpassword/')
        else:
            formated = generate_password_hash(pwd)
            cust=Customer.query.filter(Customer.cust_email==email).first()
            if check_password_hash(cust.cust_pass,pwd):
                flash('This password have been used earlier','danger')
                return redirect('/user/customer/forgottenpassword/')
            else:
                if cust.cust_username == username:
                    cust.cust_pass=formated
                    db.session.commit()
                    flash('password updated successfully', 'success')
                    return redirect('/user/customer/login/')
                else:
                    flash('invalid busiess name or email address', 'danger')
                    return redirect('/user/customer/forgottenpassword/')

                
"""Customer Profile"""
@user_bp.route('/customer/profile/', methods=['GET', 'POST'])
def customerProfile():
    loggedin = session.get('customer')
    
    if loggedin==None:
        return redirect('/')

    if request.method == 'GET':
        state=State.query.all()
        cus=Customer.query.get(loggedin)
        if cus.cust_status == 'deactived':
            flash('Please confirm your account', 'warning')
            return redirect(url_for('unconfirmed'))
        elif cus.cust_access=='deactived':
            flash('Your account has been deactivated contact Styleit for help', 'danger')
            session.pop('customer', None)
            return redirect('/user/customer/login/')
        else:
            page=request.args.get('page', 1, type=int)
            mylike = Like.query.filter(Like.like_custid==cus.cust_id).paginate(page=page, per_page=30)
            getbk=Bookappointment.query.filter(Bookappointment.ba_custid==
                                               loggedin).order_by(desc(
                                                   Bookappointment.ba_date)).paginate(page=page, per_page=20)
            noti = Notification.query.filter(Notification.notify_read=='unread', 
                                             Notification.notify_custid==cus.cust_id).order_by(desc(
                                                 Notification.notify_date)).all()
            follow = Follow.query.filter_by(follow_custid=loggedin).all()
            return render_template('user/customerprofile.html', loggedin=loggedin, cus=cus, 
                                   state=state, mylike=mylike, getbk=getbk, noti=noti, follow=follow)
    
    if request.method == 'POST':
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        phone=request.form.get('phone')
        address= request.form.get('address')
        if fname != "" or lname != "" or email != "" or phone != "" or address != "":
            upd=Customer.query.get(loggedin)
            upd.cust_fname=fname
            upd.cust_lname=lname
            upd.cust_phone=phone
            upd.cust_email=email
            upd.cust_address=address
            db.session.commit()
            flash('updated successfully', 'success')
            return redirect('/customer/profile/')
        else:
            flash('one or more filed is empty', 'warning')
            return redirect('/customer/profile/')

"""customer logout session"""
@user_bp.route('/customer/logout/')
def customerlogout():
    loggedin = session.get('customer')
    if loggedin==None:
        return redirect('/')
        
    if request.method == 'GET':
        session.pop('customer', None)
        lo=Login.query.filter_by(login_custid=loggedin, logout_date=None).first()
        lo.logout_date=datetime.utcnow()
        db.session.commit()
        return redirect('/')


"""Customers Details """
@user_bp.route('/customer/<id>/', methods=['GET', 'POST'])
def custdetail(id):
    loggedin = session.get('customer')
    desiloggedin = session.get('designer')
    cus=Customer.query.get(loggedin)
    des=Designer.query.get(desiloggedin)
    if loggedin==None and desiloggedin==None:
        return redirect('/')
        
    if request.method == 'GET':         
        design=Customer.query.filter(Customer.cust_id==id).first()
        return render_template('user/customerdetail.html', design=design, cus=cus, des=des)

"""book appointment"""
@user_bp.route('/bookappointment/', methods=['GET', 'POST'])
def book_appointment():
    loggedin = session.get('customer')
    if loggedin==None:
        return redirect('/user/customer/signup/')

    if request.method == 'GET':
        cus=Customer.query.get(loggedin)
        apnt = Subscription.query.filter(Subscription.sub_status=='active').all()
        noti = Notification.query.filter(Notification.notify_postid | Notification.notify_likeid | 
                                         Notification.notify_baid | Notification.notify_comid | 
                                         Notification.notify_paymentid | Notification.notify_shareid | 
                                         Notification.notify_subid, Notification.notify_read=='unread', 
                                         Notification.notify_custid==cus.cust_id).all()
        return render_template('user/bookappointment.html', apnt=apnt, cus=cus, noti=noti)

    if request.method == 'POST':
        getfor = request.form
        dsignername = getfor.get('dsignername')
        bdate = getfor.get('bdate')
        btime = getfor.get('btime')
        cdate = getfor.get('cdate')
        ctime = getfor.get('ctime')
        if dsignername =="" or bdate =="" or btime =="" or cdate =="" or ctime=="":
            flash('Kindly fill each fields', 'warning')
            return redirect(request.url)
        else:
            bookapp=Bookappointment(ba_desiid=dsignername, ba_custid=loggedin, 
                                    ba_bookingDate=bdate, ba_bookingTime=btime, 
                                    ba_collectionDate=cdate, ba_collectionTime=ctime)
            db.session.add(bookapp)
            db.session.commit()
            d=Notification(notify_custid=loggedin, notify_baid=bookapp.ba_id, notify_read='unread')
            db.session.add(d)
            db.session.commit()
            dd=Notification(notify_desiid=dsignername, notify_baid=bookapp.ba_id, notify_read='unread')
            db.session.add(dd)
            db.session.commit()
            
            commenter=Bookappointment.query.filter_by(ba_desiid=dsignername, 
                                                      ba_custid=loggedin, ba_status='not decided').first()
            commenter_email=commenter.desibaobj.desi_email
            custom=commenter.desibaobj.desi_businessName
            recipients={"custom":custom}
            bookappointment_signal.send(current_app, comment=commenter, 
                                        post_author_email=commenter_email, recipients=recipients)
            flash(f'You have made a successful booking with {custom}', 'success')
        return redirect('/customer/profile/')

# customer section ends

# designer section begins
"""Designer Signup"""
@user_bp.route('/user/designer/signup/', methods=['GET', 'POST'])
def designerSignup():
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    state=State.query.all()
    natn=Countries.query.all()
    if desiloggedin:
        return redirect('/designer/profile/')

    if request.method == 'GET':
        return render_template('designer/designersignup.html', state=state, des=des, natn=natn)
    
    if request.method == 'POST':
        fname=request.form.get('fname')
        country=request.form.get('country')
        fstate=request.form.get('fstate')
        cities=request.form.get('cities')
        busname=request.form.get('busname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        phone=request.form.get('phone')
        pwd=request.form.get('pwd')
        cpwd=request.form.get('cpwd')
        address= request.form.get('address')
        stat=request.form.get('state')
        lga=request.form.get('lga')
        gender=request.form.get('gender')
        pic=request.files.get('pic')
        original_name=pic.filename
        
        if country == '161':
            # validating form fields
            if (fname=="" or lname=="" or busname=="" or email=="" or 
                phone=="" or pwd=="" or cpwd=="" or address=="" or 
                stat=="" or lga=="" or gender=="" or country==""):
                flash('One or more field is empty', 'warning')
                return redirect('/user/designer/signup/')
            # checking length of password
            elif len(pwd) < 8:
                flash('Password should be atleast 8 character long', 'warning')
                return redirect('/user/designer/signup/')
            # compairing password match
            elif pwd !=cpwd:
                flash('Password match error', 'danger')
                return redirect('/user/designer/signup/')
            else:
                # spliting to check email extension
                mail = email.split('@')
                if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    flash('kindly provide a valid email', 'warning')
                    return redirect('/user/designer/signup/')
                else:
                    eemail = mail[0] + '@' + mail[1]
                    # print(eemail)
                    # hashing password
                    formated = generate_password_hash(pwd)
                    # checking image field if empty
                    if original_name != "":
                        # spliting image path
                        extension = os.path.splitext(original_name)
                        if extension[1].lower() in ['.jpg', '.gif', '.png']:
                            fn=math.ceil(random.random()*10000000000)
                            saveas = str(fn) + extension[1]
                            pic.save(f'styleitapp/static/images/profile/designer/{saveas}')
                            # committing to Customer table
                            dk=Designer(desi_fname=fname, desi_businessName=busname, 
                                        desi_lname=lname, desi_gender=gender, desi_phone=phone, 
                                        desi_email=eemail, desi_pass=formated, desi_address=address, 
                                        desi_pic=saveas, desi_stateid=stat, 
                                        desi_lgaid=lga, desi_countryid=country)
                            db.session.add(dk)
                            db.session.commit()

                            token = generate_confirmation_token(dk.desi_email)
                            confirm_url = url_for('confirm_email', token=token, _external=True)
                            html = render_template('user/activate.html', confirm_url=confirm_url)
                            subject = "Please confirm your email"
                            send_email(dk.desi_email, subject, html)
                            flash('Profile setup completed. A confirmation mail has been sent via email', 
                                  'success')
                            return redirect(url_for('unconfirmed'))
                        return redirect('/user/designer/signup/')
        else:
            # validating form fields
            if (fname=="" or lname=="" or busname=="" or email=="" or 
                phone=="" or pwd=="" or cpwd=="" or address=="" or 
                fstate=="" or cities=="" or gender=="" or country==""):
                flash('One or more field is empty', 'warning')
                return redirect('/user/designer/signup/')
            # checking length of password
            elif len(pwd) < 8:
                flash('Password should be atleast 8 character long', 'warning')
                return redirect('/user/designer/signup/')
            # compairing password match
            elif pwd !=cpwd:
                flash('Password match error', 'danger')
                return redirect('/user/designer/signup/')
            else:
                # spliting to check email extension
                mail = email.split('@')
                if mail[1] not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    flash('kindly provide a valid email', 'warning')
                    return redirect('/user/designer/signup/')
                else:
                    eemail = mail[0] + '@' + mail[1]
                    # print(eemail)
                    # hashing password
                    formated = generate_password_hash(pwd)
                    # checking image field if empty
                    if original_name != "":
                        # spliting image path
                        extension = os.path.splitext(original_name)
                        if extension[1].lower() in ['.jpg', '.gif', '.png']:
                            fn=math.ceil(random.random()*10000000000)
                            saveas = str(fn) + extension[1]
                            pic.save(f'styleitapp/static/images/profile/designer/{saveas}')
                            # committing to Customer table
                            dk=Designer(desi_fname=fname, desi_businessName=busname, 
                                        desi_lname=lname, desi_gender=gender, 
                                        desi_phone=phone, desi_email=eemail, 
                                        desi_pass=formated, desi_address=address, 
                                        desi_pic=saveas, desi_state=fstate, 
                                        desi_city=cities, desi_countryid=country)
                            db.session.add(dk)
                            db.session.commit()
                            ci=Cities(name=cities)
                            db.session.add(ci)
                            db.session.commit()
                            st=States(name=fstate)
                            db.session.add(st)
                            db.session.commit()

                            token = generate_confirmation_token(dk.desi_email)
                            confirm_url = url_for('confirm_email', token=token, _external=True)
                            html = render_template('user/activate.html', confirm_url=confirm_url)
                            subject = "Please confirm your email"
                            send_email(dk.desi_email, subject, html)
                            flash('Profile setup completed. A confirmation mail has been sent via email', 
                                  'success')
                            return redirect(url_for('unconfirmed'))
                        return redirect('/user/designer/signup/')

"""checking sub status for automatic deactivation"""
@user_bp.before_request
def before_request_func():
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin:
        subt=db.session.query(Subscription).filter(Subscription.sub_desiid==des.desi_id, 
                                                   Subscription.sub_status=='active').first()
        today = date.today()
        if subt != None:
            if subt.sub_enddate < str(today):
                subt.sub_status="deactive"
                db.session.commit()
                commenter_email=subt.subdesiobj.desi_email
                custom=subt.subdesiobj.desi_businessName
                recipients={"custom":custom}
                subdeactivate_signal.send(current_app, comment=subt, post_author_email=commenter_email, 
                                          recipients=recipients)
        else:
            pass

"""Designer Login"""
@user_bp.route('/user/designer/login/', methods=['GET', 'POST'])
def designerLogin():
    logins = DesignerLoginForm()
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin:
        return redirect('/designer/profile/')

    # rendering login template
    if request.method == 'GET':
        return render_template('designer/designerlogin.html', logins=logins, des=des)
    
    if request.method == 'POST':
        # getting form data
        email=request.form.get('email')
        pwd = request.form.get('pwd')
        # validating form data field
        if email=="" or pwd=="":
            flash('Invalid Credentials', 'danger')
            return redirect('/user/designer/login/')
        if email !="" or pwd !="":
            # quering Customer by filtering with email
            designer=db.session.query(Designer).filter(Designer.desi_email==email).first()
            if designer==None:
                flash('kindly supply a valid credentials', category='warning')
                return render_template('designer/designerlogin.html', logins=logins, designer=designer)
            else:
                formated_pwd=designer.desi_pass
                # checking password hash
                checking = check_password_hash(formated_pwd, pwd)
                if checking:
                    session['designer']=designer.desi_id
                    le=Login(login_email=designer.desi_email, login_desiid=designer.desi_id)
                    db.session.add(le)
                    db.session.commit()
                    flash('Login successful, Click your profile picture to view the side bar', category='success')
                    return redirect('/designer/profile/')
                else:
                    flash('kindly supply a valid email address and password', category='warning')
                    return render_template('designer/designerlogin.html', logins=logins, designer=designer)


"""Designer Profile"""
@user_bp.route('/designer/profile/', methods=['GET', 'POST'])
def designerProfile():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    if request.method == 'GET':
        des=Designer.query.get(desiloggedin)
        state=State.query.all()
        states=States.query.all()       
               
        if des.desi_status == 'deactived':
            flash('Please confirm your account', 'warning')
            return redirect(url_for('unconfirmed'))
        elif des.desi_access=='deactived':
            flash('Your account has been deactivated contact Styleit for help')
            session.pop('designer', None)
            return redirect('/user/designer/login/')
        else:
            page = request.args.get('page', 1, type=int)
            pos=Posting.query.filter(Posting.post_desiid==des.desi_id).paginate(page=page, per_page=30)
            getbk=Bookappointment.query.filter(Bookappointment.ba_desiid==
                                               desiloggedin).order_by(desc(
                                                   Bookappointment.ba_date)).paginate(page=page, per_page=20)
            subt=Subscription.query.filter(Subscription.sub_desiid==desiloggedin, 
                                           Subscription.sub_status=='active').first()
            noti = Notification.query.filter(Notification.notify_read=='unread', 
                                             Notification.notify_desiid==des.desi_id).all()
            bk=Job.query.filter((Job.jb_status=='completed') | 
                                (Job.jb_status=='collected')).order_by(desc(Job.jb_date
                                                                            )).paginate(page=page, per_page=20)
            bnk=Bank.query.filter_by(bnk_desiid=desiloggedin).first()
            bnkcode=Bankcodes.query.all()
            follow = Follow.query.filter_by(follow_desiid=desiloggedin).all()
            return render_template('designer/designerprofile.html', desiloggedin=desiloggedin, 
                                   des=des, state=state, pos=pos, getbk=getbk, 
                                   subt=subt, noti=noti, bk=bk, bnk=bnk, 
                                   follow=follow, bnkcode=bnkcode, states=states)

    if request.method == 'POST':
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        phone=request.form.get('phone')
        address=request.form.get('address')

        if fname=="" or lname=="" or email=="" or phone=="" or address=="":
            desi=Designer.query.get(desiloggedin)
            desi.desi_fname=fname
            desi.desi_lname=lname
            desi.desi_email=email
            desi.desi_phone=phone
            desi.desi_address=address
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect('/designer/profile/')
        else:
            flash('One of more field is empty', 'warning')
            return redirect('/designer/profile/')

"""Designer Forgotten Password"""
@user_bp.route('/user/designer/forgottenpassword/', methods=['POST', 'GET'])
def designerforgottenpass():
    desiloggedin = session.get('designer')
    if desiloggedin:
        return redirect('/designer/profile/')

    if request.method == "GET":
        return render_template('designer/forgottenpassword.html')
    if request.method == "POST":
        busname=request.form.get('businessname')
        email=request.form.get('email')
        pwd=request.form.get('pwd')
        cpwd=request.form.get('cpwd')

        if busname =="" or email =="" or pwd =="" or cpwd =="":
            flash('One or more field is empty', 'warning')
            return render_template('designer/forgottenpassword.html')
        elif pwd != cpwd:
            flash('invalid credential supplied', 'danger')
            return redirect('/user/designer/forgottenpassword/')
        else:
            formated = generate_password_hash(pwd)
            desi=Designer.query.filter(Designer.desi_email==email).first()
            if check_password_hash(desi.desi_pass,pwd):
                flash('This password have been used earlier','danger')
                return redirect('/user/designer/forgottenpassword/')
            else:
                if desi.desi_businessName == busname:
                    desi.desi_pass=formated
                    db.session.commit()
                    flash('password updated successfully', 'success')
                    return redirect('/user/designer/login/')
                else:
                    flash('invalid busiess name or email address', 'danger')
                    return redirect('/user/designer/forgottenpassword/')

"""designer logout session"""
@user_bp.route('/designer/logout/')
def designerlogout():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    if request.method == 'GET':
        session.pop('designer', None)
        lo=Login.query.filter_by(login_desiid=desiloggedin, logout_date=None).first()
        lo.logout_date=datetime.utcnow()
        db.session.commit()
        return redirect('/')

"""Posting section"""
@user_bp.route('/posting/', methods=['GET', 'POST'])
def posting():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    if request.method == 'GET':
        pst=Posting.query.filter(Posting.post_id==desiloggedin).all()
        des=Designer.query.get(desiloggedin)
        noti = Notification.query.filter(Notification.notify_read=='unread', 
                                         Notification.notify_desiid==des.desi_id).all()
        return render_template('designer/post.html', des=des, pst=pst, noti=noti)

    if request.method == 'POST':
        des=Designer.query.get(desiloggedin)
        head=request.form.get('title')
        body=request.form.get('body')

        if head=='' or body=='':
            flash('Complete all fields', 'warning')
            return render_template('designer/post.html', des=des)
        else:
            if head !="" or body !="":
                # committing to Customer table
                pos=Posting(post_title=head, post_body=body, post_desiid=des.desi_id)
                db.session.add(pos)
                db.session.commit()      
                flash('Post saved successfully, proceed to add image', 'success')
                posimg = Posting.query.filter(Posting.post_title==head, 
                                              Posting.post_desiid==des.desi_id).first()
                posimg2={posimg.post_id:{"head":posimg.post_title, "body":posimg.post_body, 
                                         "desiid":posimg.post_desiid}}            
                session['postId']=posimg2
                return redirect('/image/')
                

"""image upload"""
@user_bp.route('/image/', methods=['GET','POST'])
def image():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    if request.method == 'GET':
        des=Designer.query.get(desiloggedin)
        noti = Notification.query.filter(Notification.notify_read=='unread', 
                                         Notification.notify_desiid==des.desi_id).all()
        return render_template('designer/addimage.html', des=des, noti=noti)

    if request.method == 'POST':
        imgname=request.form.get('name')
        imgs=request.files.getlist('img')
       
        if imgname=="":
            flash('fill all required fields', 'warning')
            return redirect('/posting/')
        else:
            postId = session.get('postId')
            for x,y in postId.items():
                    pass
            for img in imgs:
                original_name=img.filename
                if original_name != "":
                    # spliting image path
                    extension = os.path.splitext(original_name)
                    if extension[1].lower() in ['.jpg', '.gif', '.png']:
                        fn=math.ceil(random.random()*10000000000)
                        saveas = str(fn) + extension[1]
                        img.save(f'styleitapp/static/images/postpic/{saveas}')     
                        # committing to Customer table
                        
                        pos=Image(image_name=imgname, image_url=saveas,
                                  image_postid=x, Image_desiid=desiloggedin)
                        db.session.add(pos)
            db.session.commit()
            session.pop('postId', None)
            flash("Posted successfuly", 'success')
            return redirect('/designer/profile/')

"""Accept/decline appointment"""
@user_bp.route('/appointment/status/<id>/', methods=['GET', 'POST'])
def appointment_status(id):
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')
    
    if request.method == 'GET':
        return redirect('/designer/profile/')
    
    if request.method == 'POST':
        apt=request.form
        aptaction = apt.get('action')
        
        if aptaction !="":
            if aptaction =="accept":
                apptm = Bookappointment.query.get(id)
                apptm.ba_status=aptaction
                db.session.commit()
                commenter=apptm.query.filter_by(ba_id=id, ba_status=aptaction).first()
                commenter_email=commenter.custbaobj.cust_email
                recipients=commenter_email
                custom=commenter.custbaobj.cust_email
                recipients={'custom':custom}
                acceptappointment_signal.send(current_app, comment=commenter, 
                                              post_author_email=commenter_email, 
                                              recipients=recipients)
                return redirect('/designer/profile/')
            elif aptaction =="decline":
                res = apt.get('response')
                if res != "":   
                    apptm = Bookappointment.query.get(id)
                    apptm.ba_status=aptaction
                    apptm.ba_reason=res
                    db.session.commit()
                    commenter=apptm.query.filter_by(ba_id=id, ba_status=aptaction).first()
                    commenter_email=commenter.custbaobj.cust_email
                    recipients=commenter_email
                    custom=commenter.custbaobj.cust_email
                    declineappointment_signal.send(current_app, comment=commenter, 
                                                   post_author_email=commenter_email, 
                                                   recipients=recipients)
                    return redirect('/designer/profile/')


"""subscription plans"""
@user_bp.route('/designer/subplan/', methods=['GET'])
def subplan():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')
    
    if request.method =='GET':
        des=Designer.query.get(desiloggedin)
        page=request.args.get('page', 1, type=int)
        sublist = Subscription.query.filter_by(sub_desiid=
                                               desiloggedin).order_by(desc(
                                                   Subscription.sub_date)).paginate(page=page, per_page=50)
        noti = Notification.query.filter(Notification.notify_read=='unread', 
                                         Notification.notify_desiid==des.desi_id).all()
        return render_template('designer/subscribeplans.html', des=des, sublist=sublist, noti=noti)


"""subscription"""
@user_bp.route('/designer/sub/', methods=['GET', 'POST'])
def subscribe():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')
    
    if request.method =='GET':
        des=Designer.query.get(desiloggedin)
        return render_template('designer/subscribe.html', des=des)
    
    if request.method == 'POST':
        getform = request.form
        plan = getform.get('plan')
        if plan =="":
            return redirect('/designer/sub/')
        else:
            planb = plan
            refno = int(random.random()*10000000) 
            session['refno'] = refno
            sub = Subscription(sub_plan=planb, sub_ref=refno, sub_desiid=desiloggedin, 
                               sub_startdate=0, sub_enddate=0)
            db.session.add(sub)
            db.session.commit()
            subb=Subscription.query.filter_by(sub_ref=refno, sub_desiid=desiloggedin).first()
            d=Notification(notify_desiid=desiloggedin, notify_subid=subb.sub_id, notify_read='unread') 
            db.session.add(d)
            db.session.commit()
            pay = Payment(payment_transNo=refno, payment_amount=planb, 
                          payment_desiid=desiloggedin, payment_subid=subb.sub_id)
            db.session.add(pay)
            db.session.commit()
            paey=Payment.query.filter_by(payment_transNo=refno, payment_desiid=desiloggedin).first()
            d=Notification(notify_desiid=desiloggedin, notify_paymentid=paey.payment_id, notify_read='unread') 
            db.session.add(d)
            db.session.commit()
            return redirect('/payment/')


""" payment """
@user_bp.route('/payment/', methods=['GET', 'POST'])
def payment():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    des=Designer.query.get(desiloggedin)
    refno = session.get('refno')
    pymt=Payment.query.filter_by(payment_transNo=refno).first()
    if request.method =='GET':
        noti = Notification.query.filter(Notification.notify_read=='unread', 
                                         Notification.notify_desiid==des.desi_id).all()
        return render_template('designer/confirmpayment.html', des=des, pymt=pymt, noti=noti)
    else:
        data = {"email":des.desi_email,"amount":pymt.payment_amount*100, "reference":pymt.payment_transNo}

        headers = {"Content-Type": "application/json","Authorization":f"Bearer {spamming}"}

        response = requests.post('https://api.paystack.co/transaction/initialize', 
                                 headers=headers, data=json.dumps(data))

        rspjson = json.loads(response.text) 
        if rspjson.get('status') == True:
            authurl = rspjson['data']['authorization_url']
            return redirect(authurl)
        else:
            return "Please try again"


@user_bp.route("/user/payverify/")
def paystack():
    reference = request.args.get('reference')
    refno = session.get('refno')
    #update our database 
    headers = {"Content-Type": "application/json","Authorization":f"Bearer {spamming}"}

    response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
    rsp =response.json()#in json format
    if rsp['data']['status'] =='success':
        amt = rsp['data']['amount']
        ipaddress = rsp['data']['ip_address']
        p = Payment.query.filter(Payment.payment_transNo==refno).first()
        tpay=Transaction_payment.query.filter(Transaction_payment.tpay_transNo==refno).first()
        bk=Bookappointment.query.filter_by(ba_id=tpay.tpay_baid).first()
        if p:
            p.payment_status = 'paid'
            db.session.add(p)
            db.session.commit()
            commenter=p.query.filter_by(payment_transNo=refno).first()
            commenter_email=commenter.desipaymentobj.desi_email
            payment_signal.send(current_app, comment=commenter, post_author_email=commenter_email)
            return redirect('/activate/')  #update database and redirect them to the feedback page
        elif tpay:
            tpay.tpay_status = 'paid'
            db.session.add(tpay)
            db.session.commit()
            bk.bk_paystatus = 'paid'
            db.session.add(bk)
            db.session.commit()
            flash("Payment successful", "success")
            commenter=tpay.query.filter_by(tpay_transNo=refno).first()
            commenter_email=commenter.desitpayobj.desi_email
            transpay_signal.send(current_app, comment=commenter, post_author_email=commenter_email)
            return redirect('/customer/profile/')
    else:
        p = Payment.query.filter(Payment.payment_transNo==refno).first()
        tpay=Transaction_payment.query.filter(Transaction_payment.tpay_transNo==refno).first()
        bk=Bookappointment.query.filter_by(ba_id=tpay.tpay_baid).first()
        if p:
            p.payment_status = 'failed'
            db.session.add(p)
            db.session.commit()
            flash("Payment Failed", "danger")
            return redirect('/designer/profile/')
        elif tpay:
            tpay.tpay_status = 'failed'
            db.session.add(tpay)
            db.session.commit()
            bk.bk_paystatus = 'failed'
            db.session.add(bk)
            db.session.commit()
            flash("Payment Failed", "danger")
            return redirect(f'/custpayment/{tpay.tpay_baid}/')


@user_bp.route('/activate/', methods=['GET', 'POST'])
def activating():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    if request.method == 'GET':
        des=Designer.query.get(desiloggedin)
        refno = session.get('refno')
        substat = Subscription.query.filter(Subscription.sub_ref==refno).first()
        # print(substat.sub_plan)
        if substat.sub_plan == '500':
            Dstart = date.today()
            Dend = Dstart + timedelta(days=29)
            # print(Dstart)
            # print(Dend)
            substat.sub_startdate=Dstart
            substat.sub_enddate=Dend
            substat.sub_status='active'
            substat.sub_paystatus='paid'
            db.session.commit()
            
            commenter=Payment.query.filter_by(payment_desiid=desiloggedin, payment_transNo=refno).first()
            commenter_email=commenter.desipaymentobj.desi_email
            custom=commenter.desipaymentobj.desi_businessName
            recipients={"custom":custom}
            subactivate_signal.send(current_app, comment=commenter, 
                                    post_author_email=commenter_email, 
                                    recipients=recipients)
            flash("Activation Successful", "success")
            return redirect('/designer/profile/')  #update database and redirect them to the feedback page
        elif substat.sub_plan == '1350':
            Dstart = date.today()
            Dend = Dstart + timedelta(days=89)
            # print(Dstart)
            # print(Dend)
            substat.sub_startdate=Dstart
            substat.sub_enddate=Dend
            substat.sub_status='active'
            substat.sub_paystatus='paid'
            db.session.commit()
            
            commenter=Payment.query.filter_by(payment_desiid=desiloggedin, payment_transNo=refno).first()
            commenter_email=commenter.desipaymentobj.desi_email
            custom=commenter.desipaymentobj.desi_businessName
            recipients={"custom":custom}
            subactivate_signal.send(current_app, comment=commenter, 
                                    post_author_email=commenter_email, 
                                    recipients=recipients)
            flash("Activation Successful", "success")
            return redirect('/designer/profile/')  #update database and redirect them to the feedback page
        elif substat.sub_plan == '2400':
            Dstart = date.today()
            Dend = Dstart + timedelta(days=179)
            # print(Dstart)
            # print(Dend)
            substat.sub_startdate=Dstart
            substat.sub_enddate=Dend
            substat.sub_status='active'
            substat.sub_paystatus='paid'
            db.session.commit()
            
            commenter=Payment.query.filter_by(payment_desiid=desiloggedin, payment_transNo=refno).first()
            commenter_email=commenter.desipaymentobj.desi_email
            custom=commenter.desipaymentobj.desi_businessName
            recipients={"custom":custom}
            subactivate_signal.send(current_app, comment=commenter, 
                                    post_author_email=commenter_email, 
                                    recipients=recipients)
            flash("Activation Successful", "success")
            return redirect('/designer/profile/')  #update database and redirect them to the feedback page
        elif substat.sub_plan == '4200':
            Dstart = date.today()
            Dend = Dstart + timedelta(days=364)
            # print(Dstart)
            # print(Dend)
            substat.sub_startdate=Dstart
            substat.sub_enddate=Dend
            substat.sub_status='active'
            substat.sub_paystatus='paid'
            db.session.commit()
            
            commenter=Payment.query.filter_by(payment_desiid=desiloggedin, payment_transNo=refno).first()
            commenter_email=commenter.desipaymentobj.desi_email
            custom=commenter.desipaymentobj.desi_businessName
            recipients={"custom":custom}
            subactivate_signal.send(current_app, comment=commenter, 
                                    post_author_email=commenter_email, 
                                    recipients=recipients)
            flash("Activation Successful", "success")
            return redirect('/designer/profile/')  #update database and redirect them to the feedback page
        else:
            flash("Activation Unsuccessful", "danger")
            return redirect('/trending')

"""confim work done"""
@user_bp.route('/complete_task/<id>/', methods=['GET', 'POST'])
def complete_task(id):
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')

    if request.method == 'GET':
        des=Designer.query.get(desiloggedin)
        bk=Bookappointment.query.get(id)
        return render_template('designer/complete_task.html', des=des, bk=bk)
    
    if request.method == 'POST':
        custid=request.form.get('custid')
        lev=request.form.get('lev')
        pic=request.files.get('pic')
        original_name=pic.filename
        if lev !="" and custid !="" and original_name !="":
            extension = os.path.splitext(original_name)
            if extension[1].lower() in ['.jpg', '.gif', '.png']:
                fn=math.ceil(random.random()*10000000000)
                saveas = str(fn) + extension[1]
                pic.save(f'styleitapp/static/images/completed_task/{saveas}')
                # committing to job table
                dk=Job(jb_status=lev, jb_pic=saveas, jb_custid=custid, 
                       jb_desiid=desiloggedin, jb_baid=id)
                db.session.add(dk)
                db.session.commit()
                ds=Bookappointment.query.get(id)
                ds.ba_status=lev
                db.session.commit()
                flash('Thank you for adding more stars to your diginity ', 'success')
                commenter=dk.query.filter_by(jb_baid=id, jb_status=lev).first()
                commenter_email=commenter.jbcustobj.cust_email
                completetask_signal.send(current_app, comment=commenter, post_author_email=commenter_email)
                return redirect('/designer/profile/')
            else:
                flash('a field is empty', 'warning')
                return redirect('/complete_task/{id}') 
        else:
            flash('one or more field is empty', 'warning')
            return redirect('/complete_task/{id}') 


@user_bp.route('/confirm_delivery/<int:id>/', methods=['POST', 'GET'])
def confirm_delivery(id):
    loggedin = session.get('customer')
    if loggedin==None:
        return redirect('/')

    if request.method == 'GET':
        cus=Customer.query.get(loggedin)
        jb=Job.query.filter(Job.jb_baid==id).first()
        return render_template('user/confirm_delivery.html', cus=cus, jb=jb)
    
    if request.method == 'POST':
        desiid=request.form.get('desiid')
        status=request.form.get('custstatus')
        
        if status !="" and desiid !="":
            bk=Bookappointment.query.get(id)
            bk.ba_custstatus=status
            db.session.commit()
            jb=Job.query.filter(Job.jb_baid==id).first()
            jb.jb_status=status
            db.session.commit()
            commenter=jb.query.filter_by(jb_baid=id, jb_status=status).first()
            commenter_email=commenter.jbdesiobj.desi_email
            confirmdelivery_signal.send(current_app, comment=commenter, post_author_email=commenter_email)
            flash("Tahank You! You've confirmed a job weldone for quality service", 'success')
            return redirect('/customer/profile/')
            # return 'You have confoirmed your task delivery'
        else:
            flash('one or more filed is empty')
            return redirect(f'/confirm_delivery/{id}/')


"""payment page for customer"""
@user_bp.route('/custpayment/<int:id>/', methods=['GET', 'POST'])
def custpayment(id):
    loggedin = session.get('customer')
    cus=Customer.query.get(loggedin)
    if loggedin==None:
        return redirect('/')
    
    if request.method=='GET':
        jb=Bookappointment.query.filter(Bookappointment.ba_id==id).first()
        # des=Designer.query.filter(Designer.desi_id==jb.jb_desiid).first()
        return render_template('user/custpayment.html', jb=jb, cus=cus)
    
    if request.method == 'POST':
        sender=request.form.get('custid')
        receiver=request.form.get('desiid')
        amt=request.form.get('amount')
        charges = request.form.get('charges')
        if cus.cust_countryid ==161: 
            if sender !="" and receiver !="" and amt !="" and charges !="":
                refno = int(random.random()*10000000) 
                session['refno'] = refno
                total_amount= int(amt) + int(charges)
                tpay=Transaction_payment(tpay_transNo=refno, tpay_custid=sender, 
                                         tpay_desiid=receiver, tpay_amount=total_amount, 
                                         tpay_baid=id, tpay_currencyicon="NGN")
                db.session.add(tpay)
                db.session.commit()
                pp=Transaction_payment.query.filter_by(tpay_transNo=refno, tpay_custid=loggedin).first()
                dd=Notification(notify_custid=cus.cust_id, notify_tpayid=pp.tpay_id, notify_read='unread') 
                db.session.add(dd)
                db.session.commit()
                return redirect(f'/confirm_payment/{id}/')
        else:
            if sender !="" and receiver !="" and amt !="" and charges !="":
                refno = int(random.random()*10000000) 
                session['refno'] = refno
                total_amount= int(amt) + int(charges)
                tpay=Transaction_payment(tpay_transNo=refno, tpay_custid=sender, 
                                         tpay_desiid=receiver, tpay_amount=total_amount, 
                                         tpay_baid=id, tpay_currencyicon="$")
                db.session.add(tpay)
                db.session.commit()
                pp=Transaction_payment.query.filter_by(tpay_transNo=refno, tpay_custid=loggedin).first()
                dd=Notification(notify_custid=cus.cust_id, notify_tpayid=pp.tpay_id, notify_read='unread') 
                db.session.add(dd)
                db.session.commit()
                return redirect(f'/confirm_payment/{id}/')

""" customer payment """
@user_bp.route('/confirm_payment/<int:id>/', methods=['GET', 'POST'])
def confirm_custpayment(id):
    loggedin = session.get('customer')
    if loggedin==None:
        return redirect('/')

    bk=Bookappointment.query.get(id)
    cus=Customer.query.get(loggedin)
    refno = session.get('refno')
    pymt=Transaction_payment.query.filter_by(tpay_transNo=refno).first()
    if request.method =='GET':
        noti = Notification.query.filter(Notification.notify_read=='unread', 
                                         Notification.notify_custid==cus.cust_id).all()
        return render_template('user/confirmcustpayment.html', bk=bk, pymt=pymt, cus=cus, noti=noti)
    else:
        if pymt.tpay_status=="paid":
            return redirect('/customer/profile/')
        else:
            data = {"email":cus.cust_email,"amount":pymt.tpay_amount*100, "reference":pymt.tpay_transNo}

            headers = {"Content-Type": "application/json","Authorization":f"Bearer {spamming}"}

            response = requests.post('https://api.paystack.co/transaction/initialize', 
                                     headers=headers, data=json.dumps(data))

            rspjson = json.loads(response.text) 
            if rspjson.get('status') == True:
                authurl = rspjson['data']['authorization_url']
                return redirect(authurl)
            else:
                return "Please try again"
            
            
                    
"""Error 404 page"""
@user_bp.errorhandler(404)
def page_not_found(error):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
    else:
        des=Designer.query.get(desiloggedin)
        cus=Customer.query.get(loggedin)
        if desiloggedin:
            noti = Notification.query.filter(Notification.notify_read=='unread', 
                                             Notification.notify_desiid==des.desi_id).all()
        elif loggedin:
            noti = Notification.query.filter(Notification.notify_postid | Notification.notify_likeid | 
                                             Notification.notify_baid | Notification.notify_comid | 
                                             Notification.notify_paymentid | Notification.notify_shareid | 
                                             Notification.notify_subid, Notification.notify_read=='unread', 
                                             Notification.notify_custid==cus.cust_id).all()
        return render_template('user/error.html', des=des, cus=cus,noti=noti, error=error),404


"""Search section"""
@user_bp.route('/postsearch/', methods=['POST', 'GET'])
def search():
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus=Customer.query.get(loggedin)
    word=request.form.get('search')    
    return redirect(f'/postsearch/{word}')

"""the search response"""
@user_bp.route('/postsearch/<word>', methods=['GET'])
def result(word):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    des=Designer.query.get(desiloggedin)
    cus=Customer.query.get(loggedin)
    page = request.args.get('page', 1, type=int)
    wordsearch=(Posting.query.join(Designer)
                .filter(Posting.post_title.ilike(f'%{word}%')| Posting.post_body.ilike(f'%{word}%') | 
                        Designer.desi_businessName.ilike(f'%{word}%'))
                .order_by(desc(Posting.post_id)).paginate(page=page, per_page=50))
    if desiloggedin:
        noti = Notification.query.filter(Notification.notify_read=='unread', 
                                         Notification.notify_desiid==des.desi_id).all()
    elif loggedin:
        noti = Notification.query.filter(Notification.notify_postid | Notification.notify_likeid | 
                                         Notification.notify_baid | Notification.notify_comid | 
                                         Notification.notify_paymentid | Notification.notify_shareid | 
                                         Notification.notify_subid, Notification.notify_read=='unread', 
                                         Notification.notify_custid==cus.cust_id).all()
    return render_template('user/search.html', wordsearch=wordsearch, word=word, cus=cus, des=des, noti=noti)


"""Search section"""
@user_bp.route('/search/', methods=['POST'])
def desisearch():
    word=request.form.get('search')
    return redirect(f'/search/{word}')


""" The search response 2"""
@user_bp.route('/search/<word>', methods=['GET'])
def search_result(word):
    print(word)
    page = request.args.get('page', 1, type=int)
    wordsearch=(Designer.query.join(Lga).join(Subscription)
                .filter(Designer.desi_businessName.ilike(f'%{word}%')| Designer.desi_fname.ilike(f'%{word}%')| 
                        Designer.desi_lname.ilike(f'%{word}%') | Designer.desi_state.ilike(f'%{word}%') | 
                        Designer.desi_city.ilike(f'%{word}%') | Lga.lga_name.ilike(f'%{word}%'), 
                        Subscription.sub_status=='active').order_by(desc(Designer.desi_id))
                .paginate(page=page, per_page=50))
    print(wordsearch.items)
    return render_template('user/search2.html', wordsearch=wordsearch, word=word)


"""delete section"""
@user_bp.route('/trashit/', methods=['GET', 'POST'])
def trashit():
    desiloggedin = session.get('designer')
    if desiloggedin==None:
        return redirect('/')
    
    if request.method=='POST':
        postid = request.form.get('postid')
        print(postid)
        if postid =="":
            flash('file error', 'error')
            return redirect(f'/post/{postid}/')
        else:
            if postid !="":
                posi = Posting.query.filter_by(post_id=postid).first()
                posi.post_delete='deleted'
                db.session.commit()
                msg='successfully deleted'
                return jsonify(msg)


"""Reports """
@user_bp.route('/report/<id>/', methods=['GET', 'POST'])
def report(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
        
    if request.method == 'GET':   
        des=Designer.query.get(desiloggedin)
        cus=Customer.query.get(loggedin)
        if cus:
            design=Designer.query.filter(Designer.desi_id==id).first()
            return render_template('user/report.html', design=design, des=des, 
                                   cus=cus, desiloggedin=desiloggedin, loggedin=loggedin)
        elif des:
            design=Customer.query.filter(Customer.cust_id==id).first()
            design2=Designer.query.get(id)
            return render_template('user/report.html', design=design, des=des, cus=cus, 
                                   desiloggedin=desiloggedin, loggedin=loggedin, design2=design2)



"""Report post """
@user_bp.route('/report/', methods=['POST'])
def reports():
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
    
    if request.method == 'POST':
        custid = request.form.get('custid')
        desid = request.form.get('desid')
        custname = request.form.get('custname')
        desname = request.form.get('desname')
        reson = request.form.get('report')

        if reson !="" and desid !="" or custid !="" or custname !="" or desname !="":
            if loggedin:
                rep = Report(report_reason=reson, report_desiid=desid, reporter=custname)
                db.session.add(rep)
                db.session.commit()
                flash('report logged', 'success')
                return redirect('/customer/profile/')

            elif desiloggedin:
                if custid:
                    rep = Report(report_reason=reson, report_custid=custid, reporter=desname)
                    db.session.add(rep)
                    db.session.commit()
                    flash('report logged', 'success')
                    return redirect('/designer/profile/')
                elif desid:
                    rep = Report(report_reason=reson, report_desiid=desid, reporter=desname)
                    db.session.add(rep)
                    db.session.commit()
                    flash('report logged', 'success')
                    return redirect('/designer/profile/')
                
        else:
            if loggedin:
                flash('one ore more file is empty', 'warning')
                return redirect(f'/report/{desid}/')
            elif desiloggedin:
                flash('one ore more file is empty', 'warning')
                return redirect(f'/report/{custid}/')


@user_bp.route('/rating/<id>/', methods=['GET', 'POST'])
def rating(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin== None:
        return redirect('/')
        
    if request.method == 'GET':
        cus=Customer.query.get(loggedin)
        des=Designer.query.get(desiloggedin)
        if cus:
            design=Designer.query.filter(Designer.desi_id==id).first()
            return render_template('user/rating.html', design=design, des=des, 
                                   cus=cus, desiloggedin=desiloggedin, loggedin=loggedin)
        elif des:
            design=Customer.query.filter(Customer.cust_id==id).first()
            design2=Designer.query.get(id)
            return render_template('user/rating.html', design=design, des=des, 
                                   cus=cus, desiloggedin=desiloggedin, 
                                   loggedin=loggedin, design2=design2)

@user_bp.route('/rating/', methods=['GET', 'POST'])
def rate():
    # desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if loggedin== None:
        return redirect('/')
    
    if request.method == 'POST':
        reson = request.form.get('rate')
        custid = request.form.get('custid')
        desid = request.form.get('desid')
        if reson !="" or custid !="" or desid !="":
            if loggedin:
                rate=Rating(rat_rating=reson, rat_custid=loggedin, rat_desiid=desid)
                db.session.add(rate)
                db.session.commit()
                flash('Thank you for the review', 'success')
                return redirect(f'/designer/{desid}/')
        else:
            if loggedin:
                flash('one ore more file is empty', 'warning')
                return redirect(f'/rating/{desid}/')
            # elif desiloggedin:
            #     flash('one ore more file is empty')
            #     return redirect(f'/rating/{custid}/')   

"""newsletter section"""
@user_bp.route('/newsletter/', methods=['GET', 'POST'])
def newsletter():
    if request.method=='GET':
        return redirect('/')
    
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        if name !="" and email !="":
            nnew=Newsletter.query.filter_by(news_email=email).first()
            if nnew==None:
                newslet=Newsletter(news_name=name, news_email=email)
                db.session.add(newslet)
                db.session.commit()
                msg='Your have subscribed to our newsletter'
                return msg
            elif nnew.news_email==email:
                msg='You have subscribed earlier to our newsletter'
                return msg
        else:
            msg='one or more filed is empty'
            return msg

"""Bank details"""
@user_bp.route('/designer/bankdetail/', methods=['GET','POST'])
def bank_detail():
    desiloggedin = session.get('designer')
    if desiloggedin==None and request.method == 'GET':
        return redirect('/')
    
    if request.method == 'POST':
        name=request.form.get('name')
        bkname=request.form.get('bank')
        acno=request.form.get('acno')
        
        if name != "" and bkname!= "" and acno != "":
            bnk=Bank(bnk_acname=name, bnk_bankname=bkname, bnk_acno=acno, bnk_desiid=desiloggedin)
            db.session.add(bnk)
            db.session.commit()
            flash('Thank you! Your bank detail have been saved.', 'success')
            return redirect('/designer/profile/')


"""Follow session"""
@user_bp.route('/follow/<int:id>/', methods=['GET', 'POST'])
def follow(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin==None:
        return redirect('/')
    
    if request.method == 'POST':
        new_follower=Follow(follow_desiid=id, follow_custid=loggedin)
        db.session.add(new_follower)
        db.session.commit()
        commenter=new_follower.query.filter_by(follow_desiid=id, follow_custid=loggedin).first()
        commenter_email=commenter.desifollowobj.desi_email
        follow_signal.send(current_app, comment=commenter, post_author_email=commenter_email)
        return redirect(f'/designer/{id}/')


"""Unfollow session"""
@user_bp.route('/unfollow/<int:id>/', methods=['GET', 'POST'])
def unfollow(id):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin==None and loggedin==None:
        return redirect('/')
    
    if request.method == 'POST':
        follower=Follow.query.filter_by(follow_desiid=id, follow_custid=loggedin).first()
        if follower:
            commenter=follower.query.filter_by(follow_desiid=id, follow_custid=loggedin).first()
            commenter_email=commenter.desifollowobj.desi_email
            unfollow_signal.send(current_app, comment=commenter, post_author_email=commenter_email)
            db.session.delete(follower)
            db.session.commit()            
            return redirect(f'/designer/{id}/')

"""frequently asked questions"""
@user_bp.route('/faq', methods=['GET'])
def faq():
    return render_template('user/faq.html')


""" signals connects """
@comment_signal.connect
def send_comment_email_alert(sender, comment, post_author_email): 
    subject = f"StyleitHQ: {comment.comcustobj.cust_fname} commented on your post"
    body = (
        f"Hi {comment.compostobj.designerobj.desi_businessName}, \n\n"
        f"{comment.comcustobj.cust_fname} commented on your post: \n" 
        f"{comment.com_body} \n\n" 
        f"Visit: https://www.styleit.africa/post/{comment.com_postid}/ \n\n"
        f"StyleitHQ")
    send_email_alert(subject, body, [post_author_email])


@reply_signal.connect
def send_reply_email_alert(sender, comment, post_author_email, recipients):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin:
        subject = f"StyleitHQ: {comment.comdesiobj.desi_businessName} replied to your comment"
        body = (f"Hi {recipients['custom']},\n\n{comment.comdesiobj.desi_businessName}" 
                f"replied to your comment: \n {comment.com_body} \n\n" 
                f"Visit: https://www.styleit.africa/post/{comment.com_postid}/ \n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])
    elif loggedin:
        subject = f"StyleitHQ: {comment.comcustobj.cust_fname} replied to your comment"
        body = (f"Hi {recipients['custom']},\n\n {comment.comcustobj.cust_fname}" 
                f"replied to your comment: \n {comment.com_body}" 
                f"\n\n Visit: https://www.styleit.africa/post/{comment.com_postid}/ \n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])


@like_signal.connect
def send_like_email_alert(sender, comment, post_author_email, recipients):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin:
        subject = f"StyleitHQ: {comment.desilikesobj.desi_businessName} like your post"
        body = (f"Hi {recipients['custom']},\n\n{comment.desilikesobj.desi_businessName}" 
                f"like your post: \n\n Visit: https://www.styleit.africa/post/{comment.like_postid}/" 
                f"\n\n StyleitHQ") 
        send_email_alert(subject, body, [post_author_email])
    elif loggedin:
        subject = f"StyleitHQ: {comment.custlikesobj.cust_fname} like your post"
        body = (f"Hi {recipients['custom']},\n\n {comment.custlikesobj.cust_fname}" 
                f"like your post:  \n\n Visit: https://www.styleit.africa/post/{comment.like_postid}/" 
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])


@unlike_signal.connect
def send_unlike_email_alert(sender, comment, post_author_email, recipients):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin:
        subject = f"StyleitHQ: {comment.desilikesobj.desi_businessName} unlike your post"
        body = (f"Hi {recipients['custom']},\n\n{comment.desilikesobj.desi_businessName} unlike your post:" 
                f"\n\n Visit: https://www.styleit.africa/post/{comment.like_postid}/" 
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])
    elif loggedin:
        subject = f"StyleitHQ: {comment.custlikesobj.cust_fname} unlike your post"
        body = (f"Hi {recipients['custom']},\n\n {comment.custlikesobj.cust_fname} unlike your post:"
                f"\n\n Visit: https://www.styleit.africa/post/{comment.like_postid}/" 
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])

@subactivate_signal.connect
def send_subactivate_email_alart(sender, comment, post_author_email, recipients):
    subject = f"Subcription Alert by StyleitHQ"
    body = (f"Hi {recipients['custom']},\n\n You have successfully subscribe to a new plan" 
            f"\n\n Your subscription details is as shown below" 
            f"\n plan: {comment.subpaymentobj.sub_plan}" 
            f"\n Sub Start Date: {comment.subpaymentobj.sub_startdate}" 
            f"\n Sub End Date: {comment.subpaymentobj.sub_enddate} \n Thank you for doing business with us." 
            f"\n\n Visit: https://www.styleit.africa/designer/subplan/" 
            f"\n\n StyleitHQ Team" )
    send_email_alert(subject, body, [post_author_email])

@subdeactivate_signal.connect
def send_subdeactivate_email_alart(sender, comment, post_author_email, recipients):
    subject = f"Subcription Alert by StyleitHQ"
    body = (f"Hi {recipients['custom']},\n\n Your subscription have been deactivated." 
            f"\n Kindly click the link below to subscribe. \n Thank you for doing business with us." 
            f"\n\n Visit: https://www.styleit.africa/designer/subplan/ \n\n StyleitHQ Team")
    send_email_alert(subject, body, [post_author_email])

@share_signal.connect
def send_share_email_alart(sender, comment, post_author_email, recipients):
    desiloggedin = session.get('designer')
    loggedin = session.get('customer')
    if desiloggedin:
        subject = f"StyleitHQ: {comment.desishareobj.desi_businessName} shared your post"
        body = (f"Hi {recipients['custom']},\n\n{comment.desishareobj.desi_businessName} shared your post:" 
                f"\n\n Visit: https://www.styleit.africa/post/{comment.share_postid}/" 
                f"\n\n StyleitHQ") 
        send_email_alert(subject, body, [post_author_email])
    elif loggedin:
        subject = f"StyleitHQ: {comment.custshareobj.cust_fname} shared your post"
        body = (f"Hi {recipients['custom']},\n\n {comment.custshareobj.cust_fname} shared your post:" 
                f"\n\n Visit: https://www.styleit.africa/post/{comment.share_postid}/" 
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])


@bookappointment_signal.connect
def send_bookappointment_email_alart(sender, comment, post_author_email, recipients):
    loggedin = session.get('customer')
    if loggedin:
        subject = f"StyleitHQ: {comment.custbaobj.cust_fname} booking appointment"
        body = (f"Hi {recipients['custom']},\n\n {comment.custbaobj.cust_fname} needs your service." 
                f"\n Kindly visit the link below to respond to the appointment" 
                f"\n\n Visit: https://www.styleit.africa/designer/profile/" 
                f"\n\n StyleitHQ")
        send_email_alert(subject, body, [post_author_email])

@acceptappointment_signal.connect
def send_acceptappointment_email_alart(sender, comment, post_author_email, recipients):
    desiloggedin = session.get('designer')
    if desiloggedin:
        subject = f"StyleitHQ: Booking Appointment Update!"
        body = (f"Hi {comment.custbaobj.cust_fname}," 
                f"\n\n {comment.desibaobj.desi_businessName} has accepted your appointment." 
                f"\n Kindly visit the link below to respond to the appointment status" 
                f"\n\n Visit: https://www.styleit.africa/customer/profile/" 
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@declineappointment_signal.connect
def send_declineappointment_email_alart(sender, comment, post_author_email, recipients):
    desiloggedin = session.get('designer')
    if desiloggedin:
        subject = f"StyleitHQ: Booking Appointment Update!"
        body = (f"Hi {comment.custbaobj.cust_fname}," 
                f"\n\n {comment.desibaobj.desi_businessName} has decline your appointment with the" 
                f"below response: \n {comment.ba_reason}. \n\n Kindly visit the link below to to book" 
                f"new appointment \n\n Visit: https://www.styleit.africa/bookappointment/" 
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@completetask_signal.connect
def send_completetask_email_alart(sender, comment, post_author_email):
    desiloggedin = session.get('designer')
    if desiloggedin:
        subject = f"StyleitHQ: Job Update!"
        body = (f"Hi {comment.jbcustobj.cust_fname},\n\n {comment.jbdesiobj.desi_businessName}" 
                f"has completed your task. \n Kindly use the link below to approve delivery" 
                f"and collection \n\n Visit: https://www.styleit.africa/customer/profile/" 
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@confirmdelivery_signal.connect
def send_confirmdelivery_email_alart(sender, comment, post_author_email):
    loggedin = session.get('customer')
    if loggedin:
        subject = f"StyleitHQ: Job Update!"
        body = (f"Hi {comment.jbdesiobj.desi_businessName},\n\n {comment.jbcustobj.cust_fname}" 
                f"has confirm your task delivery. Kindly await your payment from Styleit HQ once" 
                f"payment is confirmed.\n Kindly use the link below to view details." 
                f"\n\n Visit: https://www.styleit.africa/customer/profile/" 
                f"\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])
        
@follow_signal.connect
def send_follow_email_alart(sender, comment, post_author_email):
    loggedin = session.get('customer')
    if loggedin:
        subject = f"StyleitHQ: {comment.custfollowobj.cust_fname} follow you"
        body = (f"Hi {comment.desifollowobj.desi_businessName}," 
                f"\n\n {comment.custfollowobj.cust_fname} started following you for updates."
                f"\n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])

@unfollow_signal.connect
def send_unfollow_email_alart(sender, comment, post_author_email):
    loggedin = session.get('customer')
    if loggedin:
        subject = f"StyleitHQ: {comment.custfollowobj.cust_fname} unfollow you"
        body = (f"Hi {comment.desifollowobj.desi_businessName}," 
                f"\n\n {comment.custfollowobj.cust_fname} just unfollowing you." 
                f"Don't feel down everyone have there reasons, just keep up the" 
                f"good work to gain more followers. \n Thanks." 
                f"\n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])


@payment_signal.connect
def send_payment_email_alart(sender, comment, post_author_email):
    desiloggedin = session.get('designer')
    if desiloggedin:
        subject = f"StyleitHQ: {comment.desipaymentobj.desi_bussinessName} payment update"
        body = (f"Hi {comment.desipaymentobj.desi_businessName}," 
                f"\n\n Your payment for the subscription is successful." 
                f"\n\n Kindly check the subscription plan for update.. \n Thanks." 
                f"\n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])
        
@transpay_signal.connect
def send_transpay_signal_email_alart(sender, comment, post_author_email):
    loggedin = session.get('customer')
    if loggedin:
        subject = f"StyleitHQ: {comment.custtpayobj.cust_fname} payment update"
        body = (f"Hi {comment.custtpayobj.cust_fname}," 
                f"\n\n Your payment for the negotiated {comment.desitpayobj.desi_businessName}" 
                f"payment was successful. Your total charges for payment is  {comment.tpay_amount}." 
                f"\n Thanks. \n\n\n StyleitHQ Team")
        send_email_alert(subject, body, [post_author_email])
      
# @subactivate_signal.connect
# def send_subactivate_email_alart(sender, comment, post_author_email, receipients):
#     desiloggedin = session.get('designer')
#     msg = Message(f"StyleitHQ: Subscription Activation", sender, post_author_email)
#     msg.html= render_template('designer/sub_notification.html', comment=comment)
#     mail.send(msg)


""" list of booking"""
@user_bp.route('/booking_appointment_list/', methods=['GET'])
def bkappoint_list():
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin==None:
        return redirect('/')
    
    if request.method=='GET':
        page = request.args.get('page', 1, type=int)
        getbk=Bookappointment.query.filter(Bookappointment.ba_desiid==
                                           desiloggedin).order_by(desc(Bookappointment.ba_date)
                                                                  ).paginate(page=page, per_page=4)
        return render_template('designer/morepage.html', page=page, getbk=getbk, des=des)


""" List of post list"""
@user_bp.route('/postlist/', methods=['GET'])
def postlist():
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin==None:
        return redirect('/')
    
    if request.method=='GET':
        page = request.args.get('page', 1, type=int)
        pos=Posting.query.filter(Posting.post_desiid==des.desi_id).paginate(page=page, per_page=30)
        return render_template('designer/morepage.html', pos=pos, page=page, des=des)


""" list of job done"""
@user_bp.route('/jobdone/', methods=['GET'])
def jobdone():
    desiloggedin = session.get('designer')
    des=Designer.query.get(desiloggedin)
    if desiloggedin==None:
        return redirect('/')
    
    if request.method=='GET':
        page = request.args.get('page', 1, type=int)
        bk=Job.query.filter((Job.jb_status=='completed') | 
                            (Job.jb_status=='collected')).order_by(desc(Job.jb_date)
                                                                   ).paginate(page=page, per_page=30)
        return render_template('designer/morepage.html', bk=bk, page=page, des=des)


""" List of customer appointment list"""
@user_bp.route('/appoint_list/', methods=['GET'])
def appoint():
    loggedin = session.get('customer')
    cus=Customer.query.get(loggedin)
    
    if loggedin==None:
        return redirect('/')
    
    if request.method=='GET':
        page = request.args.get('page', 1, type=int)
        getbk=Bookappointment.query.filter(Bookappointment.ba_custid==loggedin
                                           ).order_by(desc(Bookappointment.ba_date)
                                                      ).paginate(page=page, per_page=3)
        return render_template('user/morepages.html', getbk=getbk, page=page, cus=cus)


@user_bp.route('/like_list/', methods=['GET'])
def like_list():
    loggedin = session.get('customer')
    cus=Customer.query.get(loggedin)
    
    if loggedin==None:
        return redirect('/')
    
    if request.method=='GET':
        page = request.args.get('page', 1, type=int)
        mylike = Like.query.filter(Like.like_custid==cus.cust_id).paginate(page=page, per_page=1)
        return render_template('user/morepages.html', mylike=mylike, page=page, cus=cus)