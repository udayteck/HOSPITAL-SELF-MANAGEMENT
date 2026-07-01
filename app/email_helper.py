import os
import requests

def send_html_email(to_email, subject, html_content):
    """
    Send an HTML email using Brevo API.
    Returns True on success, False on failure.
    """
    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        print("❌ BREVO_API_KEY not set")
        return False

    from_email = os.environ.get('MAIL_DEFAULT_SENDER', 'sdkhospital479@gmail.com')

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    data = {
        "sender": {"email": from_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 201:
            print(f"✅ Email sent to {to_email}")
            return True
        else:
            print(f"❌ Brevo error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Email exception: {e}")
        return False


def build_skd_email_template(title, greeting_text, main_content):
    """
    Build a styled HTML email template consistent with SKD Hospital brand.
    """
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0a0e1a; color: #fff; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #1a1a2e; padding: 30px; border-radius: 12px; border: 1px solid #00ccb0;">
            <h1 style="color: #00ccb0; text-align: center;">SKD Hospital</h1>
            <h2 style="color: #fff;">{title}</h2>
            <p style="color: #ccc;">{greeting_text}</p>
            <div style="background: #0f172a; border-left: 5px solid #00ccb0; border-radius: 8px; padding: 16px; margin: 24px 0;">
                {main_content}
            </div>
            <p style="color: #999; text-align: center; font-size: 12px;">This is an automated message from SKD Hospital.</p>
        </div>
    </body>
    </html>
    """