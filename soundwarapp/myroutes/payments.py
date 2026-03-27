"""
Payment Routes - Flutterwave Integration
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import requests
import hashlib
import hmac

from ..models import db, User, Artist, Payment
from ..utils.security import sanitize_input, validate_transaction_ref

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@payments_bp.route('/initialize', methods=['POST'])
@jwt_required()
def initialize_payment():
    """Initialize Flutterwave payment for artist registration"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    tx_ref = data.get('tx_ref')
    
    if not tx_ref or not validate_transaction_ref(tx_ref):
        return jsonify({'error': 'Invalid transaction reference'}), 400
    
    # Check if transaction ref already exists
    existing = Payment.query.filter_by(tx_ref=tx_ref).first()
    if existing:
        return jsonify({'error': 'Transaction reference already used'}), 409
    
    # Create pending payment record
    payment = Payment(
        user_id=user.id,
        transaction_id='pending',
        tx_ref=tx_ref,
        amount=current_app.config['ARTIST_REGISTRATION_FEE'],
        currency='NGN',
        status='pending',
        payment_purpose='artist_registration'
    )
    
    db.session.add(payment)
    db.session.commit()
    
    return jsonify({
        'message': 'Payment initialized',
        'payment': payment.to_dict()
    }), 201


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
        
        # Update artist profile
        if user.artist:
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
                
                # Update artist
                user = User.query.get(payment.user_id)
                if user and user.artist:
                    user.artist.is_paid = True
                    user.artist.is_verified = True
                
                db.session.commit()
    
    return jsonify({'status': 'received'}), 200


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
