"""
Payment Routes - Flutterwave Integration
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import requests
import hashlib
import hmac
from soundwarapp import db, csrf
from ..models import User, Artist, Payment, Contest, ContestEntry
from ..utils.security import sanitize_input, validate_transaction_ref

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@csrf.exempt
@payments_bp.route('/initialize', methods=['POST'])
@jwt_required()
def initialize_payment():
    """Initialize Flutterwave payment for artist registration"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not user.artist:
        return jsonify({'error': 'Artist profile required'}), 403

    contest = Contest.get_current()
    if not contest:
        return jsonify({'error': 'No active contest season available'}), 400

    artist = user.artist
    if not artist.can_participate():
        return jsonify({
            'error': 'Past winners cannot participate for 24 months',
            'months_remaining': artist.months_until_eligible()
        }), 403

    entry = artist.get_contest_entry(contest)
    if entry is None:
        entry = ContestEntry(artist_id=artist.id, contest_id=contest.id, status='pending_payment')
        db.session.add(entry)
        db.session.commit()

    if entry.is_paid and entry.is_verified:
        return jsonify({'error': 'This contest season has already been paid for'}), 409

    data = request.get_json(silent=True) or {}
    tx_ref = data.get('tx_ref') or data.get('transaction_ref')

    if not tx_ref or not validate_transaction_ref(tx_ref):
        return jsonify({'error': 'Invalid transaction reference'}), 400

    existing = Payment.query.filter_by(tx_ref=tx_ref).first()
    if existing:
        return jsonify({'error': 'Transaction reference already used'}), 409

    payment = Payment(
        user_id=user.id,
        contest_id=contest.id,
        transaction_id=tx_ref,
        tx_ref=tx_ref,
        amount=current_app.config['ARTIST_REGISTRATION_FEE'],
        currency='NGN',
        status='pending',
        payment_purpose='contest_registration'
    )

    db.session.add(payment)
    db.session.commit()

    flw_secret = current_app.config.get('FLUTTERWAVE_SECRET_KEY')
    if not flw_secret:
        return jsonify({'error': 'Flutterwave secret key is not configured'}), 500

    headers = {
        'Authorization': f'Bearer {flw_secret}',
        'Content-Type': 'application/json',
        'accept': 'application/json'
    }

    amount = current_app.config['ARTIST_REGISTRATION_FEE']
    currency = 'NGN'
    email = data.get('email') or user.email
    fullname = data.get('fullname') or user.name
    phone_number = data.get('phone_number') or ''
    redirect_url = data.get('redirect_url') or f"{current_app.config.get('FRONTEND_URL', 'http://localhost:8080')}/payment/success"

    customer = {
        'email': email,
        'name': fullname,
    }
    if phone_number:
        customer['phone_number'] = phone_number

    payload = {
        'tx_ref': tx_ref,
        'amount': amount,
        'currency': currency,
        'redirect_url': redirect_url,
        'payment_options': 'card,banktransfer',
        'customer': customer,
        'customizations': {
            'title': 'SoundWars Artist Registration',
            'description': 'Contest participation fee',
            'logo': f"{current_app.config.get('FRONTEND_URL', 'http://localhost:8080')}/favicon.ico",
        },
    }

    try:
        response = requests.post(
            current_app.config.get('FLUTTERWAVE_INIT_URL', 'https://api.flutterwave.com/v3/payments'),
            headers=headers,
            json=payload,
            timeout=30
        )

        result = response.json()

        if response.status_code >= 400:
            flutterwave_error = result.get('message') or result.get('error') or 'Unable to initialize payment with Flutterwave'
            current_app.logger.error('Flutterwave initialization failed: %s', result)
            return jsonify({'error': flutterwave_error}), 502

        payment_link = (result.get('data') or {}).get('link') or (result.get('data') or {}).get('payment_link')
        if not payment_link:
            return jsonify({'error': 'Flutterwave did not provide a payment link'}), 502

        payment.transaction_id = str((result.get('data') or {}).get('id') or payment.transaction_id)
        payment.flw_ref = (result.get('data') or {}).get('flw_ref')
        entry.status = 'pending_payment'
        db.session.commit()

        return jsonify({
            'message': 'Payment initialized',
            'payment_link': payment_link,
            'payment': payment.to_dict()
        }), 201
    except requests.exceptions.RequestException as e:
        current_app.logger.error('Flutterwave API error: %s', e)
        return jsonify({'error': 'Unable to initialize payment with Flutterwave'}), 502


@csrf.exempt
@payments_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_payment():
    """Verify Flutterwave payment"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    tx_ref = data.get('tx_ref')
    
    if not transaction_id:
        return jsonify({'error': 'Transaction ID required'}), 400
    
    # Verify with Flutterwave API
    flw_secret = current_app.config['FLUTTERWAVE_SECRET_KEY']
    
    headers = {
        'Authorization': f'Bearer {flw_secret}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify',
            headers=headers,
            timeout=30
        )
        
        result = response.json()
        
        if result.get('status') != 'success':
            return jsonify({'error': 'Payment verification failed'}), 400
        
        payment_data = result.get('data', {})
        
        # Verify amount and currency
        expected_amount = current_app.config['ARTIST_REGISTRATION_FEE']
        if payment_data.get('amount') != expected_amount or payment_data.get('currency') != 'NGN':
            return jsonify({'error': 'Invalid payment amount'}), 400
        
        # Verify payment status
        if payment_data.get('status') != 'successful':
            return jsonify({'error': 'Payment not successful'}), 400
        
        # Update or create payment record
        payment = Payment.query.filter_by(tx_ref=tx_ref).first()
        
        if payment:
            payment.transaction_id = str(transaction_id)
            payment.flw_ref = payment_data.get('flw_ref')
            payment.status = 'successful'
            payment.payment_type = payment_data.get('payment_type')
            payment.verified_at = datetime.utcnow()
        else:
            payment = Payment(
                user_id=user.id,
                transaction_id=str(transaction_id),
                tx_ref=tx_ref or payment_data.get('tx_ref'),
                flw_ref=payment_data.get('flw_ref'),
                amount=payment_data.get('amount'),
                currency='NGN',
                status='successful',
                payment_type=payment_data.get('payment_type'),
                verified_at=datetime.utcnow()
            )
            db.session.add(payment)
        
        # Update contest entry and artist profile
        if user.artist:
            user.artist.is_paid = True
            user.artist.is_verified = True
            user.artist.payment_id = payment.id

        entry = ContestEntry.query.filter_by(artist_id=user.artist.id, contest_id=payment.contest_id).first()
        if entry:
            entry.is_paid = True
            entry.is_verified = True
            entry.status = 'approved'
            user.artist.is_paid = True
            user.artist.is_verified = True
            user.artist.payment_id = payment.id
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment verified successfully',
            'payment': payment.to_dict()
        }), 200
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Flutterwave API error: {e}")
        return jsonify({'error': 'Payment verification failed'}), 500


@csrf.exempt
@payments_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    """Handle Flutterwave webhook"""
    # Verify webhook signature
    signature = request.headers.get('verif-hash')
    secret_hash = current_app.config.get('FLUTTERWAVE_WEBHOOK_SECRET')
    
    if secret_hash and signature != secret_hash:
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.get_json()
    
    if data.get('event') == 'charge.completed':
        payment_data = data.get('data', {})
        
        if payment_data.get('status') == 'successful':
            tx_ref = payment_data.get('tx_ref')
            
            payment = Payment.query.filter_by(tx_ref=tx_ref).first()
            
            if payment and payment.status == 'pending':
                payment.transaction_id = str(payment_data.get('id'))
                payment.flw_ref = payment_data.get('flw_ref')
                payment.status = 'successful'
                payment.payment_type = payment_data.get('payment_type')
                payment.verified_at = datetime.utcnow()
                
                # Update artist and contest entry
                user = User.query.get(payment.user_id)
                if user and user.artist:
                    user.artist.is_paid = True
                    user.artist.is_verified = True
                    user.artist.payment_id = payment.id
                entry = ContestEntry.query.filter_by(artist_id=user.artist.id, contest_id=payment.contest_id).first()
                if entry:
                    entry.is_paid = True
                    entry.is_verified = True
                    entry.status = 'approved'
                
                db.session.commit()
    
    return jsonify({'status': 'received'}), 200


@csrf.exempt
@payments_bp.route('/status/<tx_ref>', methods=['GET'])
@jwt_required()
def get_payment_status(tx_ref):
    """Get payment status by transaction reference"""
    user_id = get_jwt_identity()
    
    payment = Payment.query.filter_by(
        tx_ref=tx_ref,
        user_id=user_id
    ).first()
    
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    
    return jsonify({'payment': payment.to_dict()}), 200
