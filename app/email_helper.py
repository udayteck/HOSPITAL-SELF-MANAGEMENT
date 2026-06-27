from flask_mail import Message
from threading import Thread
from flask import current_app, url_for
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_html_email(recipient, subject, html_content):
    msg = Message(subject, recipients=[recipient])
    msg.html = html_content
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def build_skd_email_template(title, greeting_text, main_content, button_text=None, button_link=None):
    button_html = ""
    if button_text and button_link:
        button_html = f"""
        <div style="text-align: center; margin: 24px 0;">
            <a href="{button_link}" style="background-color: #14b8a6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 30px; font-weight: bold;">{button_text}</a>
        </div>
        """
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{title}</title></head>
<body style="font-family: Arial, sans-serif; background-color: #f4f7fc; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%); padding: 24px; text-align: center;">
            <div style="width: 60px; height: 60px; background: white; border-radius: 50%; margin: 0 auto; display: inline-block; line-height: 60px;">
                <span style="font-size: 36px;">🏥</span>
            </div>
            <h1 style="color: white; margin: 12px 0 0 0;">SKD Hospital</h1>
            <p style="color: #ccfbf1;">Where Healthcare Meets Hospitality</p>
        </div>
        <div style="padding: 32px 24px;">
            <p style="font-size: 18px; color: #0f766e; font-weight: bold;">{greeting_text}</p>
            {main_content}
            {button_html}
            <hr style="margin: 24px 0;">
            <p style="color: #94a3b8; font-size: 12px; text-align: center;">
                This is a system‑generated email. Please do not reply.<br>
                © 2026 SKD Hospital
            </p>
        </div>
    </div>
</body>
</html>
"""

def send_doctor_notification(doctor_email, patient_name, doctor_name, slot_start, appointment_id):
    subject = "New Appointment Request - SKD Hospital"
    html_content = build_skd_email_template(
        title="New Appointment Request",
        greeting_text=f"Dear Dr. {doctor_name},",
        main_content=f"""
        <p>You have a new appointment request from <strong>{patient_name}</strong>.</p>
        <div style="background: #f0fdfa; border-left: 5px solid #14b8a6; border-radius: 12px; padding: 16px; margin: 24px 0;">
            <p><strong>📅 Date:</strong> {slot_start.strftime('%A, %B %d, %Y')}</p>
            <p><strong>⏰ Time:</strong> {slot_start.strftime('%I:%M %p')}</p>
            <p><strong>🆔 Request ID:</strong> {appointment_id}</p>
        </div>
        <p>Please log in to your doctor dashboard to <strong>confirm</strong> or <strong>reject</strong> this request.</p>
        """,
        button_text="Go to Dashboard",
        button_link=url_for('doctor.dashboard', _external=True)
    )
    send_html_email(doctor_email, subject, html_content)