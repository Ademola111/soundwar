from flask import Flask, jsonify
from styleitapp import db, jwt
from styleitapp.models import TokenBlocklist

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