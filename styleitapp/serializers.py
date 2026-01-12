import datetime
from styleitapp.models import (Designer, State, Customer, Posting, Image, Comment, Like, 
                               Share, Bookappointment, Subscription, Payment, Notification,
                               Report, Rating, Newsletter, Job, Transaction_payment, Bank, Admin,
                               Follow, Login, Bankcodes, State, Lga, Countries, States, Cities,
                               Activitylog, Superadmin, Transfer)

"""Posting models serialization"""  
def serialize_post(posting):
    return {
        "post_id": posting.post_id,
        "post_title": posting.post_title,
        "post_body": posting.post_body,
        "post_date": posting.post_date.isoformat() if posting.post_date else None,
        "post_suspend": posting.post_suspend,
        "post_delete": posting.post_delete,
        "post_desiid": posting.post_desiid,
        "post_adminid": posting.post_adminid,
        "post_spadminid": posting.post_spadminid,
        "likes_count": len(posting.likes),
        "comments_count": len(posting.postcomobj),
        "images": [serialize_image(image) for image in posting.imagepostobj]
    }

"""Image Models Serialization"""    
def serialize_image(image):
    return {
        "image_id": image.image_id,
        "image_name": image.image_name,
        "image_url": image.image_url,
        "image_postid": image.image_postid,
        "image_desiid": image.Image_desiid
    }


"""Comment model serialization"""    
def serialize_comment(comment):
    return {
        "com_id": comment.com_id,
        "com_body": comment.com_body,
        "com_date": comment.com_date.isoformat() if comment.com_date else None,
        "com_suspend": comment.com_suspend,
        "com_delete": comment.com_delete,
        "com_postid": comment.com_postid,
        "com_custid": comment.com_custid,
        "com_desiid": comment.com_desiid,
        "parent_id": comment.parent_id,
        "com_adminid": comment.com_adminid,
        "com_spadminid": comment.com_spadminid,
        "replies": [serialize_comment(reply) for reply in comment.replies]
    }


"""Customer model serialization"""    
def serialize_customer(customer):
    return {
        "cust_id": customer.cust_id,
        "cust_regdate": customer.cust_regdate.isoformat() if customer.cust_regdate else None,
        "cust_fname": customer.cust_fname,
        "cust_lname": customer.cust_lname,
        "cust_username": customer.cust_username,
        "cust_gender": customer.cust_gender,
        "cust_phone": customer.cust_phone,
        "cust_email": customer.cust_email,
        "cust_address": customer.cust_address,
        "cust_pic": customer.cust_pic,
        "cust_activationdate": customer.cust_activationdate.isoformat() if customer.cust_activationdate else None,
        "cust_status": customer.cust_status,
        "cust_access": customer.cust_access,
        "cust_state": customer.cust_state,
        "cust_city": customer.cust_city,
        "cust_countryid": customer.cust_countryid,
        "cust_stateid": customer.cust_stateid,
        "cust_lgaid": customer.cust_lgaid,
        "state": serialize_state(customer.stateobj) if customer.stateobj else None,
        "lga": serialize_lga(customer.lgaobj) if customer.lgaobj else None
    }


"""State model serialization"""    
def serialize_state(state):
    return {
        "state_id": state.state_id,
        "state_name": state.state_name
    }


"""LGA model serialization""" 
def serialize_lga(lga):
    return {
        "lga_id": lga.lga_id,
        "lga_name": lga.lga_name
    }


"""Designer model serialization"""
def serialize_designer(designer):
    return {
        "desi_id": designer.desi_id,
        "desi_regdate": designer.desi_regdate.isoformat() if designer.desi_regdate else None,
        "desi_fname": designer.desi_fname,
        "desi_lname": designer.desi_lname,
        "desi_businessName": designer.desi_businessName,
        "desi_gender": designer.desi_gender,
        "desi_phone": designer.desi_phone,
        "desi_email": designer.desi_email,
        "desi_address": designer.desi_address,
        "desi_pic": designer.desi_pic,
        "desi_activationdate": designer.desi_activationdate.isoformat() if designer.desi_activationdate else None,
        "desi_status": designer.desi_status,
        "desi_access": designer.desi_access,
        "desi_state": designer.desi_state,
        "desi_city": designer.desi_city,
        "desi_countryid": designer.desi_countryid,
        "desi_stateid": designer.desi_stateid,
        "desi_lgaid": designer.desi_lgaid,
        "state": serialize_state(designer.stateobj2) if designer.stateobj2 else None,
        "lga": serialize_lga(designer.lgaobj2) if designer.lgaobj2 else None
    }
            

"""Subscription model serialization"""
def serialize_subscription(subscription):
    return {
        "sub_id": subscription.sub_id,
        "sub_plan": subscription.sub_plan,
        "sub_date": subscription.sub_date.isoformat() if subscription.sub_date else None,
        "sub_startdate": subscription.sub_startdate,
        "sub_enddate": subscription.sub_enddate,
        "sub_ref": subscription.sub_ref,
        "sub_status": subscription.sub_status,
        "sub_paystatus": subscription.sub_paystatus,
        "sub_desiid": subscription.sub_desiid
    }


"""Payment model serialization"""        
def serialize_payment(payment):
    return {
        "payment_id": payment.payment_id,
        "payment_transNo": payment.payment_transNo,
        "payment_transdate": payment.payment_transdate.isoformat() if payment.payment_transdate else None,
        "payment_amount": payment.payment_amount,
        "payment_status": payment.payment_status,
        "payment_desiid": payment.payment_desiid,
        "payment_subid": payment.payment_subid
    }


"""Transaction Payment model serialization"""            
def serialize_transaction_payment(tpay):
    return {
        "tpay_id": tpay.tpay_id,
        "tpay_transNo": tpay.tpay_transNo,
        "tpay_transdate": tpay.tpay_transdate.isoformat() if tpay.tpay_transdate else None,
        "tpay_amount": tpay.tpay_amount,
        "tpay_status": tpay.tpay_status,
        "tpay_currencyicon": tpay.tpay_currencyicon,
        "tpay_desiid": tpay.tpay_desiid,
        "tpay_custid": tpay.tpay_custid,
        "tpay_baid": tpay.tpay_baid
    }


"""Admin model serialization"""   
def serialize_transaction_payment(tpay):
    return {
        "tpay_id": tpay.tpay_id,
        "tpay_transNo": tpay.tpay_transNo,
        "tpay_transdate": tpay.tpay_transdate.isoformat() if tpay.tpay_transdate else None,
        "tpay_amount": tpay.tpay_amount,
        "tpay_status": tpay.tpay_status,
        "tpay_currencyicon": tpay.tpay_currencyicon,
        "tpay_desiid": tpay.tpay_desiid,
        "tpay_custid": tpay.tpay_custid,
        "tpay_baid": tpay.tpay_baid,
        "designer": serialize_designer(tpay.desitpayobj) if tpay.desitpayobj else None,
        "customer": serialize_customer(tpay.custtpayobj) if tpay.custtpayobj else None,
        "bookappointment": {
            "ba_id": tpay.tpaybaobj.ba_id,
            "ba_date": tpay.tpaybaobj.ba_date.isoformat() if tpay.tpaybaobj.ba_date else None,
        } if tpay.tpaybaobj else None
    }


"""Like model serialization"""
def serialize_like(like):
    return {
        "like_id": like.like_id,
        "like_date": like.like_date.isoformat() if like.like_date else None,
        "like_postid": like.like_postid,
        "like_desiid": like.like_desiid,
        "like_custid": like.like_custid,
        "designer": serialize_designer(like.desilikesobj) if like.desilikesobj else None,
        "customer": serialize_customer(like.custlikesobj) if like.custlikesobj else None,
        "post": serialize_post(like.posts) if like.posts else None
    }


"""Super admin model serialization"""
def serialize_superadmin(superadmin):
    return {
        "spadmin_id": superadmin.spadmin_id,
        "spadmin_fname": superadmin.spadmin_fname,
        "spadmin_lname": superadmin.spadmin_lname,
        "spadmin_gender": superadmin.spadmin_gender,
        "spadmin_phone": superadmin.spadmin_phone,
        "spadmin_email": superadmin.spadmin_email,
        "spadmin_address": superadmin.spadmin_address,
        "spadmin_pic": superadmin.spadmin_pic,
        "spadmin_status": superadmin.spadmin_status
    }


"""Share model serialization"""
def serialize_share(share):
    return {
        "share_id": share.share_id,
        "share_date": share.share_date.isoformat() if share.share_date else None,
        "share_webname": share.share_webname,
        "share_postid": share.share_postid,
        "share_desiid": share.share_desiid,
        "share_custid": share.share_custid
    }


"""Booking appointment model serialization"""
def serialize_bookappointment(bookappointment):
    return {
        "ba_id": bookappointment.ba_id,
        "ba_date": bookappointment.ba_date.isoformat() if bookappointment.ba_date else None,
        "ba_bookingDate": bookappointment.ba_bookingDate,
        "ba_bookingTime": bookappointment.ba_bookingTime,
        "ba_collectionDate": bookappointment.ba_collectionDate,
        "ba_collectionTime": bookappointment.ba_collectionTime,
        "ba_status": bookappointment.ba_status,
        "ba_custstatus": bookappointment.ba_custstatus,
        "ba_paystatus": bookappointment.ba_paystatus,
        "ba_reason": bookappointment.ba_reason,
        "ba_desiid": bookappointment.ba_desiid,
        "ba_custid": bookappointment.ba_custid,
        "designer": serialize_designer(bookappointment.desibaobj) if bookappointment.desibaobj else None,
        "customer": serialize_customer(bookappointment.custbaobj) if bookappointment.custbaobj else None
    }


"""Job done model serialization"""    
def serialize_job(job):
    return {
        "jb_id": job.jb_id,
        "jb_date": job.jb_date.isoformat() if job.jb_date else None,
        "jb_status": job.jb_status,
        "jb_pic": job.jb_pic,
        "jb_custid": job.jb_custid,
        "jb_desiid": job.jb_desiid,
        "jb_baid": job.jb_baid
    }


"""Notification model serialization"""
def serialize_notification(notification):
    return {
        "notify_id": notification.notify_id,
        "notify_date": notification.notify_date.isoformat() if notification.notify_date else None,
        "notify_read": notification.notify_read,
        "notify_desiid": notification.notify_desiid,
        "notify_custid": notification.notify_custid,
        "notify_postid": notification.notify_postid
    }


"""Report model serialization"""
def serialize_report(report):
    return {
        "report_id": report.report_id,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "report_reason": report.report_reason,
        "reporter": report.reporter,
        "report_desiid": report.report_desiid,
        "report_custid": report.report_custid
    }


"""Rating model serialization"""
def serialize_rating(rating):
    return {
        "rat_id": rating.rat_id,
        "rat_date": rating.rat_date.isoformat() if rating.rat_date else None,
        "rat_rating": rating.rat_rating,
        "rat_desiid": rating.rat_desiid,
        "rat_custid": rating.rat_custid
    }


"""Newsletter model serialization"""
def serialize_newsletter(newsletter):
    return {
        "news_id": newsletter.news_id,
        "news_name": newsletter.news_name,
        "news_email": newsletter.news_email,
        "news_date": newsletter.news_date.isoformat() if newsletter.news_date else None
    }


"""Band details model serialization"""
def serialize_bank(bank):
    return {
        "bnk_id": bank.bnk_id,
        "bnk_acname": bank.bnk_acname,
        "bnk_bankname": bank.bnk_bankname,
        "bnk_acno": bank.bnk_acno,
        "bnk_date": bank.bnk_date.isoformat() if bank.bnk_date else None,
        "bnk_desiid": bank.bnk_desiid
    }


"""Bank codes model serialization"""
def serialize_bankcodes(bankcodes):
    return {
        "id": bankcodes.id,
        "name": bankcodes.name,
        "code": bankcodes.code
    }


"""Follow models serialization"""
def serialize_follow(follow):
    return {
        "follow_id": follow.follow_id,
        "follow_desiid": follow.follow_desiid,
        "follow_custid": follow.follow_custid
    }


"""Login model serialization"""
def serialize_login(login):
    return {
        "login_id": login.login_id,
        "login_email": login.login_email,
        "login_date": login.login_date.isoformat() if login.login_date else None,
        "logout_date": login.logout_date.isoformat() if login.logout_date else None
    }


"""Transfer model serialization"""
def serialize_transfer(transfer):
    return {
        "tf_id": transfer.tf_id,
        "tf_createdAt": transfer.tf_createdAt.isoformat(),
        "tf_updatedAt": transfer.tf_updatedAt.isoformat(),
        "tf_reference": transfer.tf_reference,
        "tf_status": transfer.tf_status
    }


"""Countries model"""
def serialize_countries(country):
    return {
        "country_id": country.country_id,
        "country_name": country.country_name
        }


"""States model"""
def serialize_states(state):
    return {
        "id": state.id,
        "name": state.name
        }


"""Cities model"""
def serialize_cities(city):
    return {
        "id": city.id,
        "name": city.name
        }


"""Activity log model"""
def serialize_activitylog(activity):
    return {
        "id": activity.id,
        "link": activity.link,
        "date": activity.date.isoformat()
        }