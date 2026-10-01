"""
Email Utilities
"""
from flask import current_app
from flask_mail import Message, Mail

mail = Mail()


def send_activation_email(to_email: str, username: str, activation_url: str) -> bool:
    """Send the one-time account activation email."""
    try:
        msg = Message(
            subject="Activate Your SoundWars Account",
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #00c9a7, #00b4d8); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: #fff; margin: 0;">SoundWars</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <h2>Activate your account</h2>
                    <p>Hi {username},</p>
                    <p>Thanks for joining SoundWars. Confirm your email address to activate your account.</p>
                    <p style="text-align: center;"><a href="{activation_url}" style="display: inline-block; background: #00c9a7; color: #fff; padding: 12px 30px; text-decoration: none; border-radius: 5px;">Activate Account</a></p>
                    <p>This link will expire in 24 hours.</p>
                    <p>Best,<br>The SoundWars Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send activation email: {e}")
        return False


def send_password_reset_email(to_email: str, username: str, reset_url: str) -> bool:
    """Send password reset email"""
    try:
        msg = Message(
            subject="Reset Your SoundWars Password",
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00c9a7, #00b4d8); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: #fff; margin: 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #00c9a7; color: #fff; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎵 SoundWars</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>Hi {username},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                    <p>Best,<br>The SoundWars Team</p>
                </div>
                <div class="footer">
                    <p>© 2024 SoundWars. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
        return False


def send_reparticipation_email(to_email: str, username: str, stage_name: str) -> bool:
    """Send an email notification to a past winner who can re-enter."""
    try:
        msg = Message(
            subject="You're eligible to compete again in SoundWars! 🎉",
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )

        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00c9a7, #00b4d8); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: #fff; margin: 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #00c9a7; color: #fff; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎵 SoundWars</h1>
                </div>
                <div class="content">
                    <h2>Hi {stage_name},</h2>
                    <p>Great news! Your past win makes you eligible to compete in SoundWars again.</p>
                    <p>To rejoin the next competition, simply sign in and complete the artist registration payment. You will also need to upload a new track for verification.</p>
                    <p style="text-align: center;">
                        <a href="{current_app.config.get('FRONTEND_URL', 'http://localhost:8080')}/login" class="button">Sign in to compete</a>
                    </p>
                    <p>We look forward to hearing your next hit!</p>
                    <p>Best,<br>The SoundWars Team</p>
                </div>
                <div class="footer">
                    <p>© 2024 SoundWars. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send re-participation email: {e}")
        return False


def send_welcome_email(to_email: str, username: str) -> bool:
    """Send welcome email to new users"""
    try:
        msg = Message(
            subject="Welcome to SoundWars! 🎵",
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00c9a7, #00b4d8); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: #fff; margin: 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎵 SoundWars</h1>
                </div>
                <div class="content">
                    <h2>Welcome to SoundWars!</h2>
                    <p>Hi {username},</p>
                    <p>Thank you for joining SoundWars - the ultimate music competition platform!</p>
                    <p>You can now:</p>
                    <ul>
                        <li>Vote for your favorite songs</li>
                        <li>Discover amazing new artists</li>
                        <li>Support the music community</li>
                    </ul>
                    <p>Best,<br>The SoundWars Team</p>
                </div>
                <div class="footer">
                    <p>© 2024 SoundWars. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email: {e}")
        return False
