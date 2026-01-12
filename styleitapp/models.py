from datetime import datetime, timezone
from sqlalchemy import func
from styleitapp import db

"""Posting models"""
class Posting(db.Model):
    post_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    post_title = db.Column(db.String(255), nullable=False)
    post_body = db.Column(db.Text(), nullable=True)
    post_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    post_suspend = db.Column(db.Enum('suspended', 'unsuspended'), server_default='unsuspended')
    post_delete = db.Column(db.Enum('deleted', 'not deleted'), server_default='not deleted')
    #foreignkey
    post_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    post_adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    post_spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    
    #relationship
    imagepostobj = db.relationship("Image", back_populates='postimageobj')
    designerobj = db.relationship("Designer", back_populates='designerpostobj')
    postcomobj = db.relationship('Comment', back_populates='compostobj')
    # likes = db.relationship('Like', backref='posting', lazy='dynamic')
    likes = db.relationship('Like', back_populates='posts')
    sharepostobj = db.relationship('Share', back_populates='postshareobj')
    postnotifyobj = db.relationship('Notification', back_populates='notifypostobj')
    postadminobj = db.relationship('Admin', back_populates='adminpostobj')
    postspadminobj = db.relationship('Superadmin', back_populates='spadminpostobj')
    

"""Image Models"""
class Image(db.Model):
    image_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    image_name = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    #foreignkey
    image_postid = db.Column(db.Integer(), db.ForeignKey('posting.post_id'))
    Image_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    #relationship
    imagedesignerobj = db.relationship("Designer", back_populates='designerimageobj')
    postimageobj= db.relationship("Posting", back_populates='imagepostobj')
    

"""Comment model"""
class Comment(db.Model):
    _N = 6
    com_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    com_body = db.Column(db.Text(), nullable=True)
    com_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    path = db.Column(db.Text, index=True)
    com_suspend = db.Column(db.Enum('suspended', 'unsuspended'), server_default='unsuspended')
    com_delete = db.Column(db.Enum('deleted', 'not deleted'), server_default='not deleted')
    #foreignkey
    com_postid = db.Column(db.Integer(), db.ForeignKey('posting.post_id'))
    com_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    com_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    parent_id = db.Column(db.Integer(), db.ForeignKey('comment.com_id'))
    com_adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    com_spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    #relationship
    compostobj = db.relationship('Posting', back_populates='postcomobj')
    comcustobj = db.relationship('Customer', back_populates='custcomobj')
    comdesiobj = db.relationship('Designer', back_populates='desicomobj')
    comnotifyobj = db.relationship('Notification', back_populates='notifycomobj')
    comadminobj = db.relationship('Admin', back_populates='admincomobj')
    comspadminobj = db.relationship('Superadmin', back_populates='spaadmincomobj')
    
    
    replies = db.relationship(
        'Comment', backref=db.backref('parent', remote_side=[com_id]),
        lazy='dynamic')
    
    # def save(self):
    #     db.session.add(self)
    #     db.session.commit()
    #     prefix = (self.parent.path + '.') if self.parent else ''
    #     self.path = prefix + '{:0{}d}'.format(self.com_id, self._N)
    #     db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.flush()  # ensures com_id is assigned, but does not commit

        prefix = (self.parent.path + '.') if self.parent and self.parent.path else ''
        self.path = prefix + '{:0{}d}'.format(self.com_id, self._N)

        db.session.commit()

    def level(self):
        return len(self.path)//self._N - 1


"""Customer model"""
class Customer(db.Model):
    cust_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    cust_regdate = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    cust_fname = db.Column(db.String(255), nullable=False)
    cust_lname = db.Column(db.String(255), nullable=False)
    cust_username = db.Column(db.String(255), nullable=False)
    cust_gender = db.Column(db.Enum('male','female'), nullable=False)
    cust_phone = db.Column(db.String(225), nullable=False)
    cust_email = db.Column(db.String(255), nullable=False)
    cust_pass = db.Column(db.String(255), nullable=False)
    cust_password_changed_at = db.Column(db.DateTime, nullable=True)
    cust_address = db.Column(db.Text(), nullable=True)
    cust_pic = db.Column(db.String(255), nullable=True)
    cust_activationdate = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    cust_status = db.Column(db.Enum('actived','suspended','banned','dormant', 'deactived'), server_default='deactived')
    cust_access = db.Column(db.Enum('actived', 'deactived'), server_default='actived')
    cust_state=db.Column(db.String(225), nullable=True)
    cust_city=db.Column(db.String(225), nullable=True)
    cust_nin = db.Column(db.String(11), nullable=True)
    cust_passport = db.Column(db.String(9), nullable=True)
    cust_vinpic = db.Column(db.String(255), nullable=True)
    cust_refercode = db.Column(db.String(225), nullable=True)
    
    #foreignkey
    cust_countryid = db.Column(db.Integer(), db.ForeignKey('countries.country_id'))
    cust_stateid = db.Column(db.Integer(), db.ForeignKey('state.state_id'))
    cust_lgaid = db.Column(db.Integer(), db.ForeignKey('lga.lga_id'))
    cust_adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    cust_spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    #relationship
    custcountry = db.relationship('Countries', back_populates='countryobjcust')
    stateobj = db.relationship('State', back_populates='statecustomerobj')
    lgaobj = db.relationship('Lga', back_populates='lgacustomerobj')
    custcomobj = db.relationship('Comment', back_populates='comcustobj')
    likecustobj = db.relationship('Like', back_populates='custlikesobj')
    sharecustobj = db.relationship('Share', back_populates='custshareobj')
    bacustobj = db.relationship('Bookappointment', back_populates='custbaobj')
    custnotifyobj = db.relationship('Notification', back_populates='notifycustobj')
    reportcustobj = db.relationship('Report', back_populates='custreportobj')
    ratcustobj = db.relationship('Rating', back_populates='custratobj')
    custjbobj=db.relationship('Job', back_populates='jbcustobj')
    tpaycustobj=db.relationship('Transaction_payment', back_populates='custtpayobj')
    followcustobj = db.relationship('Follow', back_populates='custfollowobj')
    logincustobj = db.relationship('Login', back_populates='custloginobj')
    custadminobj = db.relationship('Admin', back_populates='admincustobj')
    custspadminobj = db.relationship('Superadmin', back_populates='spadmincustobj')
    custjtiobj= db.relationship('TokenBlocklist', back_populates='jticustobj')

    

"""State model"""
class State(db.Model): 
    state_id = db.Column(db.Integer(), primary_key=True,autoincrement=True)
    state_name = db.Column(db.String(255), nullable=False)
    #set up the relationship
    statecustomerobj = db.relationship('Customer', back_populates ='stateobj')
    statedesignerobj = db.relationship('Designer', back_populates ='stateobj2')
    statelgaobj = db.relationship('Lga', back_populates='lgastateobj')
    statesrobj = db.relationship('Salesrep', back_populates='srstateobj')
    

"""LGA model"""
class Lga(db.Model): 
    lga_id = db.Column(db.Integer(), primary_key=True,autoincrement=True)
    lga_name = db.Column(db.String(255), nullable=False)
    #foreignkey
    lga_stateid = db.Column(db.Integer(), db.ForeignKey('state.state_id'))
    #set up the relationship
    lgacustomerobj = db.relationship('Customer', back_populates ='lgaobj')
    lgadesignerobj = db.relationship('Designer', back_populates ='lgaobj2')
    lgastateobj = db.relationship('State', back_populates ='statelgaobj')
    lgasrobj = db.relationship('Salesrep', back_populates='srlgaobj')
    

"""Designer model"""
class Designer(db.Model):
    desi_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    desi_regdate = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    desi_fname = db.Column(db.String(255), nullable=False)
    desi_lname = db.Column(db.String(255), nullable=False)
    desi_businessName = db.Column(db.String(255), nullable=False)
    desi_gender = db.Column(db.Enum('male','female'), nullable=False)
    desi_phone = db.Column(db.String(225), nullable=False)
    desi_email = db.Column(db.String(255), nullable=False)
    desi_pass = db.Column(db.String(255), nullable=False)
    desi_password_changed_at = db.Column(db.DateTime, nullable=True)
    desi_address = db.Column(db.Text(), nullable=True)
    desi_bio = db.Column(db.Text(), nullable=True)
    desi_about = db.Column(db.Text(), nullable=True)
    desi_pic = db.Column(db.String(255), nullable=True)
    desi_activationdate = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    desi_status = db.Column(db.Enum('actived','suspended','banned','dormant', 'deactived'), server_default='deactived')
    desi_access = db.Column(db.Enum('actived', 'deactived'), server_default='actived')
    desi_state=db.Column(db.String(225), nullable=True)
    desi_city=db.Column(db.String(225), nullable=True)
    desi_nin = db.Column(db.String(11), nullable=True)
    desi_passport = db.Column(db.String(9), nullable=True)
    desi_vinpic = db.Column(db.String(255), nullable=True)
    desi_refercode = db.Column(db.String(225), nullable=True)
    
    #foreignkey
    desi_countryid = db.Column(db.Integer(), db.ForeignKey('countries.country_id'))
    desi_stateid = db.Column(db.Integer(), db.ForeignKey('state.state_id'))
    desi_lgaid = db.Column(db.Integer(), db.ForeignKey('lga.lga_id'))
    desi_adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    desi_spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    #relationship
    desicountry = db.relationship('Countries', back_populates='countryobj')
    stateobj2 = db.relationship('State', back_populates='statedesignerobj')
    lgaobj2 = db.relationship('Lga', back_populates='lgadesignerobj')
    designerpostobj = db.relationship("Posting", back_populates='designerobj')
    designerimageobj = db.relationship("Image", back_populates='imagedesignerobj')
    desicomobj = db.relationship('Comment', back_populates='comdesiobj')
    desisubobj = db.relationship('Subscription', back_populates='subdesiobj')
    likedesiobj = db.relationship('Like', back_populates='desilikesobj')
    sharedesiobj = db.relationship('Share', back_populates='desishareobj')
    badesiobj = db.relationship('Bookappointment', back_populates='desibaobj')
    paymentdesiobj=db.relationship('Payment', back_populates='desipaymentobj')
    desinotifyobj = db.relationship('Notification', back_populates='notifydesiobj')
    reportdesiobj = db.relationship('Report', back_populates='desireportobj')
    ratdesiobj = db.relationship('Rating', back_populates='desiratobj')
    desijbobj=db.relationship('Job', back_populates='jbdesiobj')
    tpaydesiobj=db.relationship('Transaction_payment', back_populates='desitpayobj')
    bnkdesiobj = db.relationship('Bank', back_populates='desibnkobj')
    followdesiobj = db.relationship('Follow', back_populates='desifollowobj')
    logindesiobj = db.relationship('Login', back_populates='desiloginobj')
    desiadminobj = db.relationship('Admin', back_populates='admindesiobj')
    desispadminobj = db.relationship('Superadmin', back_populates='spadmindesiobj')
    desijtinobj = db.relationship('TokenBlocklist', back_populates='jtidesiobj')
         

"""Subscription model"""
class Subscription(db.Model):
    sub_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    sub_plan = db.Column(db.String(255), nullable=False)
    sub_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sub_startdate = db.Column(db.String(255), nullable=True)
    sub_enddate = db.Column(db.String(255), nullable=True)
    sub_ref = db.Column(db.Integer(), nullable=True)
    sub_status = db.Column(db.Enum('active', 'deactive'), server_default='deactive')
    sub_paystatus = db.Column(db.Enum('pending', 'paid', 'failed'), server_default='pending')
    #foreignkey
    sub_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    #relationship
    subdesiobj = db.relationship('Designer', back_populates='desisubobj')
    paysubobj=db.relationship('Payment', back_populates='subpaymentobj')
    subnotifyobj = db.relationship('Notification', back_populates='notifysubobj')


"""Payment model"""
class Payment(db.Model):
    payment_id=db.Column(db.Integer(), primary_key=True,autoincrement=True)
    payment_transNo=db.Column(db.Integer(), nullable=True)
    payment_transdate=db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    payment_amount=db.Column(db.Float(), nullable=False)
    payment_status = db.Column(db.Enum('pending', 'paid', 'failed'), server_default='pending')
    #foreignkey
    payment_desiid = db.Column(db.Integer(), db.ForeignKey("designer.desi_id"))
    payment_subid = db.Column(db.Integer(), db.ForeignKey("subscription.sub_id"))
    #relationship
    desipaymentobj=db.relationship('Designer', back_populates='paymentdesiobj')
    subpaymentobj=db.relationship('Subscription', back_populates='paysubobj')
    paynotifyobj = db.relationship('Notification', back_populates='notifypayobj')


"""Transaction Payment model"""
class Transaction_payment(db.Model):
    tpay_id=db.Column(db.Integer(), primary_key=True,autoincrement=True)
    tpay_transNo=db.Column(db.Integer(), nullable=True)
    tpay_transdate=db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    tpay_amount=db.Column(db.Float(), nullable=False)
    tpay_status = db.Column(db.Enum('pending', 'paid', 'failed'), server_default='pending')
    tpay_currencyicon = db.Column(db.String(10), nullable=False)
    #foreignkey
    tpay_desiid = db.Column(db.Integer(), db.ForeignKey("designer.desi_id"))
    tpay_custid = db.Column(db.Integer(), db.ForeignKey("customer.cust_id"))
    tpay_baid = db.Column(db.Integer(), db.ForeignKey('bookappointment.ba_id'))
    
    #relationship
    desitpayobj=db.relationship('Designer', back_populates='tpaydesiobj')
    custtpayobj=db.relationship('Customer', back_populates='tpaycustobj')
    tpaynotifyobj = db.relationship('Notification', back_populates='notifytpayobj')
    tpaybaobj = db.relationship('Bookappointment', back_populates='batpayobj')
    tpaytfobj = db.relationship('Transfer', back_populates='tftpayobj')
            

"""Admin model"""
class Admin (db.Model):
    admin_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    admin_fname = db.Column(db.String(255), nullable=False)
    admin_lname = db.Column(db.String(255), nullable=False)
    admin_gender = db.Column(db.Enum('male','female'), nullable=False)
    admin_phone = db.Column(db.String(225), nullable=False)
    admin_email = db.Column(db.String(255), nullable=False)
    admin_pass = db.Column(db.String(255), nullable=False)
    admin_address = db.Column(db.Text(), nullable=True)
    admin_secretword = db.Column(db.String(255), nullable=False)
    admin_pic = db.Column(db.String(255), nullable=True)
    admin_status = db.Column(db.Enum('active','suspended','deactive'), server_default='active')
    #Relationship
    loginadminobj = db.relationship('Login', back_populates='adminloginobj')
    adminpostobj = db.relationship('Posting', back_populates='postadminobj')
    admincomobj = db.relationship('Comment', back_populates='comadminobj')
    admincustobj = db.relationship('Customer', back_populates='custadminobj')
    admindesiobj = db.relationship('Designer', back_populates='desiadminobj')
    adminactlogobj = db.relationship('Activitylog', back_populates='actlogadminobj')
    adminjtiobj = db.relationship('TokenBlocklist', back_populates='jtiadminobj')


"""Like model"""
class Like(db.Model):
    like_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    like_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    #foreignKey
    like_postid = db.Column(db.Integer(), db.ForeignKey('posting.post_id'))
    like_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    like_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    
    
    #relationship
    desilikesobj = db.relationship('Designer', back_populates='likedesiobj')
    custlikesobj = db.relationship('Customer', back_populates='likecustobj')
    posts = db.relationship('Posting', back_populates='likes')
    likenotifyobj = db.relationship('Notification', back_populates='notifylikeobj')


"""Super admin model"""
class Superadmin (db.Model):
    spadmin_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    spadmin_fname = db.Column(db.String(255), nullable=False)
    spadmin_lname = db.Column(db.String(255), nullable=False)
    spadmin_gender = db.Column(db.Enum('male','female'), nullable=False)
    spadmin_phone = db.Column(db.String(225), nullable=False)
    spadmin_email = db.Column(db.String(255), nullable=False)
    spadmin_pass = db.Column(db.String(255), nullable=False)
    spadmin_address = db.Column(db.Text(), nullable=True)
    spadmin_secretword = db.Column(db.String(255), nullable=False)
    spadmin_pic = db.Column(db.String(255), nullable=True)
    spadmin_status = db.Column(db.Enum('active','suspended','deactive'), server_default='active')
    # Relationship
    loginspadminobj = db.relationship('Login', back_populates='spadminloginobj')
    spadminpostobj = db.relationship('Posting', back_populates='postspadminobj')
    spaadmincomobj = db.relationship('Comment', back_populates='comspadminobj')
    spadmincustobj = db.relationship('Customer', back_populates='custspadminobj')
    spadmindesiobj = db.relationship('Designer', back_populates='desispadminobj')
    spadminactlogobj = db.relationship('Activitylog', back_populates='actlogspadminobj')
    superadminjtiobj = db.relationship('TokenBlocklist', back_populates='jtisuperadminobj')


"""Share model"""
class Share(db.Model):
    share_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    share_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    share_webname = db.Column(db.String(255), nullable=False)
    #foreignKey
    share_postid = db.Column(db.Integer(), db.ForeignKey('posting.post_id'))
    share_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    share_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    #relationship
    desishareobj = db.relationship('Designer', back_populates='sharedesiobj')
    custshareobj = db.relationship('Customer', back_populates='sharecustobj')
    postshareobj = db.relationship('Posting', back_populates='sharepostobj')
    sharenotifyobj = db.relationship('Notification', back_populates='notifyshareobj')


"""Booking appointment model"""
class Bookappointment(db.Model):
    ba_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    ba_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ba_bookingDate = db.Column(db.String(255), nullable=False)
    ba_bookingTime = db.Column(db.String(255), nullable=False)
    ba_collectionDate = db.Column(db.String(255), nullable=False)
    ba_collectionTime = db.Column(db.String(255), nullable=False)
    ba_status = db.Column(db.Enum('accept', 'decline', 'not decided', 'completed', 'not done'), nullable=False, server_default='not decided')
    ba_custstatus = db.Column(db.Enum('collected', 'not collected'), nullable=False, server_default='not collected')
    ba_paystatus = db.Column(db.Enum('pending', 'paid', 'failed'), server_default='pending')
    ba_reason = db.Column(db.String(255), nullable=True)
    
    #foreignKey
    ba_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    ba_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    #relationship
    desibaobj = db.relationship('Designer', back_populates='badesiobj')
    custbaobj = db.relationship('Customer', back_populates='bacustobj')
    banotifyobj = db.relationship('Notification', back_populates='notifybaobj')
    bajbobj=db.relationship('Job', back_populates='jbbaobj')
    batpayobj = db.relationship('Transaction_payment', back_populates='tpaybaobj')


"""Job done model"""
class Job(db.Model):
    jb_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    jb_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    jb_status=db.Column(db.Enum("not done", "completed", "collected"), nullable=False, server_default="not done")
    jb_pic=db.Column(db.String(225), nullable=False)
    
    #foreignKey
    jb_custid=db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    jb_desiid=db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    jb_baid = db.Column(db.Integer(), db.ForeignKey('bookappointment.ba_id'))

    #relationship
    jbbaobj=db.relationship('Bookappointment', back_populates='bajbobj')
    jbcustobj=db.relationship('Customer', back_populates='custjbobj')
    jbdesiobj=db.relationship('Designer', back_populates='desijbobj')
    

"""Notification model"""
class Notification(db.Model):
    notify_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    notify_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    notify_read = db.Column(db.Enum('read', 'unread'), nullable=False, server_default='unread')
    # foreignKey
    notify_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    notify_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    notify_postid = db.Column(db.Integer(), db.ForeignKey('posting.post_id'))
    notify_likeid = db.Column(db.Integer(), db.ForeignKey('like.like_id'))
    notify_comid = db.Column(db.Integer(), db.ForeignKey('comment.com_id'))
    notify_shareid = db.Column(db.Integer(), db.ForeignKey('share.share_id'))
    notify_baid = db.Column(db.Integer(), db.ForeignKey('bookappointment.ba_id'))
    notify_subid = db.Column(db.Integer(), db.ForeignKey('subscription.sub_id'))
    notify_paymentid = db.Column(db.Integer(), db.ForeignKey('payment.payment_id'))
    notify_tpayid = db.Column(db.Integer(), db.ForeignKey('transaction_payment.tpay_id'))
    
    # relationship
    notifydesiobj = db.relationship('Designer', back_populates='desinotifyobj')
    notifycustobj = db.relationship('Customer', back_populates='custnotifyobj')
    notifypostobj = db.relationship('Posting', back_populates='postnotifyobj')
    notifylikeobj = db.relationship('Like', back_populates='likenotifyobj')
    notifycomobj = db.relationship('Comment', back_populates='comnotifyobj')
    notifyshareobj = db.relationship('Share', back_populates='sharenotifyobj')
    notifybaobj = db.relationship('Bookappointment', back_populates='banotifyobj')
    notifysubobj = db.relationship('Subscription', back_populates='subnotifyobj')
    notifypayobj = db.relationship('Payment', back_populates='paynotifyobj')
    notifytpayobj = db.relationship('Transaction_payment', back_populates='tpaynotifyobj')    

    def save(self):
        db.session.add(self)
        db.session.commit()


"""Report model"""
class Report(db.Model):
    report_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    report_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    report_reason = db.Column(db.String(255), nullable=False)
    reporter=db.Column(db.String(255), nullable=False)
    #foreignKey
    report_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    report_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    #relationship
    desireportobj = db.relationship('Designer', back_populates='reportdesiobj')
    custreportobj = db.relationship('Customer', back_populates='reportcustobj')


"""Rating model"""
class Rating(db.Model):
    rat_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    rat_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    rat_rating= db.Column(db.Integer(), nullable=False)
    #foreignKey
    rat_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    rat_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    #relationship
    desiratobj = db.relationship('Designer', back_populates='ratdesiobj')
    custratobj = db.relationship('Customer', back_populates='ratcustobj')


"""Newsletter model"""
class Newsletter(db.Model):
    news_id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    news_name=db.Column(db.String(225), nullable=False)
    news_email=db.Column(db.String(225), nullable=False)
    news_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


"""Band details model"""
class Bank(db.Model):
    bnk_id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    bnk_acname=db.Column(db.String(225), nullable=False)
    bnk_bankname=db.Column(db.String(225), nullable=False)
    bnk_acno=db.Column(db.String(15), nullable=False)
    bnk_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    #forignKey
    bnk_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    
    #relationship
    desibnkobj = db.relationship('Designer', back_populates='bnkdesiobj')


"""Bank codes model"""
class Bankcodes(db.Model):
    id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name=db.Column(db.String(100), nullable=False)
    code=db.Column(db.String(10), nullable=False)
    
    def __init__(self, id, name, code):
        self.id = id
        self.name = name
        self.code = code


"""Follow models"""    
class Follow(db.Model):
    follow_id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    #foreignKey
    follow_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    follow_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    #relationship
    desifollowobj = db.relationship('Designer', back_populates='followdesiobj')
    custfollowobj = db.relationship('Customer', back_populates='followcustobj')


"""Login model"""
class Login(db.Model):
    login_id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    login_email=db.Column(db.String(225), nullable=False)
    login_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    logout_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    last_active_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    #foreignKey
    login_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    login_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    login_adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    login_spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    #relationship
    desiloginobj = db.relationship('Designer', back_populates='logindesiobj')
    custloginobj = db.relationship('Customer', back_populates='logincustobj')
    adminloginobj = db.relationship('Admin', back_populates='loginadminobj')
    spadminloginobj = db.relationship('Superadmin', back_populates='loginspadminobj')


"""Transfer model"""
class Transfer(db.Model):
    tf_id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    tf_createdAt = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    tf_updatedAt = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    tf_reference = db.Column(db.Integer(), nullable=True)
    tf_RecipientCode = db.Column(db.String(225), nullable=False)
    tf_receiverAcName = db.Column(db.String(100), nullable=False)
    tf_receiverAcNo = db.Column(db.String(10), nullable=False)
    tf_receiverbankName = db.Column(db.String(100), nullable=False)
    tf_receiverEmail = db.Column(db.String(225), nullable=False)
    tf_amountRemited = db.Column(db.String(225), nullable=False)
    tf_integrationCode = db.Column(db.String(10), nullable=False)
    tf_receiptId = db.Column(db.String(225), nullable=False)
    tf_message = db.Column(db.String(225), nullable=False)
    tf_depositor = db.Column(db.String(225), nullable=False)
    tf_tpayreference = db.Column(db.Integer(), nullable=True)
    tf_status = db.Column(db.Enum("pending","success", "failed", "reversed"), nullable=False, server_default="pending")
    # ForeignKey
    tf_tpayid = db.Column(db.Integer(), db.ForeignKey('transaction_payment.tpay_id'))
    #Relationship
    tftpayobj = db.relationship('Transaction_payment', back_populates='tpaytfobj')


"""Countries model"""
class Countries(db.Model):
    country_id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    country_name=db.Column(db.String(225), nullable=False)
    # relationship
    countryobj = db.relationship('Designer', back_populates='desicountry')
    countryobjcust = db.relationship('Customer', back_populates='custcountry')


"""States model"""
class States(db.Model):
    id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name=db.Column(db.String(225), nullable=False)


"""Cities model"""
class Cities(db.Model):
    id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    name=db.Column(db.String(225), nullable=False)


"""Activity log model"""
class Activitylog(db.Model):
    id=db.Column(db.Integer(), primary_key=True, autoincrement=True)
    adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    link = db.Column(db.String(2048), nullable=False)
    date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    #relationship
    actlogspadminobj = db.relationship('Superadmin', back_populates='spadminactlogobj')
    actlogadminobj = db.relationship('Admin', back_populates='adminactlogobj')

class Salesrep(db.Model):
    sr_id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    sr_name = db.Column(db.String(255), nullable=False)
    sr_gender = db.Column(db.Enum('male','female'), nullable=False)
    sr_phone = db.Column(db.String(225), nullable=False)
    sr_email = db.Column(db.String(255), nullable=False)
    sr_address = db.Column(db.Text(), nullable=True)
    sr_pic = db.Column(db.String(255), nullable=True)
    sr_refercode = db.Column(db.Integer(), nullable=True)
    
    #foreignkey
    sr_stateid = db.Column(db.Integer(), db.ForeignKey('state.state_id'))
    sr_lgaid = db.Column(db.Integer(), db.ForeignKey('lga.lga_id'))
    
    #relationship
    srstateobj = db.relationship('State', back_populates='statesrobj')
    srlgaobj = db.relationship('Lga', back_populates='lgasrobj')

class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    jti_desiid = db.Column(db.Integer(), db.ForeignKey('designer.desi_id'))
    jti_custid = db.Column(db.Integer(), db.ForeignKey('customer.cust_id'))
    jti_adminid = db.Column(db.Integer(), db.ForeignKey('admin.admin_id'))
    jti_spadminid = db.Column(db.Integer(), db.ForeignKey('superadmin.spadmin_id'))
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    jticustobj = db.relationship('Customer', back_populates='custjtiobj')
    jtidesiobj = db.relationship('Designer', back_populates='desijtinobj')
    jtiadminobj = db.relationship('Admin', back_populates='adminjtiobj')
    jtisuperadminobj = db.relationship('Superadmin', back_populates='superadminjtiobj')

