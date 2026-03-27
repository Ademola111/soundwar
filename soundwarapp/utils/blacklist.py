from flask import Flask, jsonify
from soundwarapp import db, jwt
from soundwarapp.models import TokenBlocklist

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    # If jti exists in DB → revoked
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
    return token is not None

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return (
        jsonify({
            "is_revoked": jti,
            "status": "error",
            "message": "The token has been revoked. Please log in again.",
            "redirect": "/apihome"
        }),
        401
    )


@jwt.unauthorized_loader
def custom_unauthorized_callback(err_str):
    # Called when no JWT is sent
    return jsonify({"message": "Unauthorized access"}), 401

@jwt.invalid_token_loader
def custom_invalid_token_callback(err_str):
    # Called when JWT is invalid
    return jsonify({"message": "Unauthorized access"}), 401

@jwt.expired_token_loader
def custom_expired_token_callback(jwt_header, jwt_payload):
    # Called when JWT is expired
    return jsonify({"message": "Unauthorized access"}), 401
