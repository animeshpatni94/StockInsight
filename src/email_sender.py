"""
Email sender module using Resend API.
https://resend.com/docs/send-with-python
"""

import os
import time
from typing import Optional, List
from datetime import datetime
from pathlib import Path

import resend

from config import EMAIL_CONFIG


def send_email(to_email: str, subject: str, html_content: str, 
               cc_emails: Optional[List[str]] = None) -> bool:
    """
    Send an HTML email using Resend API.
    
    Args:
        to_email: Recipient email address (can be comma-separated for multiple)
        subject: Email subject line
        html_content: HTML body of the email
        cc_emails: Optional list of CC recipients
    
    Returns:
        True if sent successfully, False otherwise
    """
    api_key = os.getenv('RESEND_API_KEY')
    sender_address = os.getenv('RESEND_FROM_EMAIL', 'Stock Insight <onboarding@resend.dev>')
    
    if not api_key:
        print("  Warning: RESEND_API_KEY not configured")
        print("  Set RESEND_API_KEY in environment variables")
        return _save_email_locally(to_email, subject, html_content)
    
    # Initialize Resend with API key
    resend.api_key = api_key
    
    # Parse multiple recipients (comma-separated)
    recipients = [email.strip() for email in to_email.split(',') if email.strip()]
    
    max_retries = EMAIL_CONFIG.get('max_retries', 3)
    retry_delay = EMAIL_CONFIG.get('retry_delay_seconds', 5)
    
    for attempt in range(max_retries):
        try:
            print(f"  Sending email to {', '.join(recipients)}...")
            
            # Build email parameters
            params: resend.Emails.SendParams = {
                "from": sender_address,
                "to": recipients,
                "subject": subject,
                "html": html_content
            }
            
            # Add CC recipients if provided
            if cc_emails:
                params["cc"] = cc_emails
            
            # Send email via Resend
            response = resend.Emails.send(params)
            
            if response and response.get('id'):
                print(f"  ✓ Email sent successfully! Message ID: {response.get('id')}")
                return True
            else:
                print(f"  Unexpected response: {response}")
                    
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                print(f"  Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("  All retry attempts exhausted")
                return _save_email_locally(to_email, subject, html_content)
    
    return False


def _save_email_locally(to_email: str, subject: str, html_content: str) -> bool:
    """
    Save email as local HTML file when sending fails.
    
    Args:
        to_email: Intended recipient
        subject: Email subject
        html_content: HTML content
    
    Returns:
        True if saved successfully
    """
    
    try:
        # Create output directory
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"email_report_{timestamp}.html"
        filepath = output_dir / filename
        
        # Add metadata header to the HTML
        metadata = f"""
        <!-- 
        Email Report - Saved Locally
        To: {to_email}
        Subject: {subject}
        Generated: {datetime.now().isoformat()}
        Note: Email delivery failed, report saved locally
        -->
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(metadata + html_content)
        
        print(f"  ✓ Email saved locally to: {filepath}")
        return True
        
    except Exception as e:
        print(f"  Failed to save email locally: {str(e)}")
        return False


def send_test_email(to_email: str) -> bool:
    """
    Send a test email to verify configuration.
    
    Args:
        to_email: Test recipient email
    
    Returns:
        True if successful
    """
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .box { background: #e3f2fd; padding: 20px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🎉 Test Email Successful!</h1>
            <p>Your Stock Insight Agent email configuration is working correctly.</p>
            <p>You will receive monthly reports at this address.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated test email from Stock Insight Agent.
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(
        to_email=to_email,
        subject="📊 Stock Insight Agent - Test Email",
        html_content=test_html
    )


def validate_email_config() -> dict:
    """
    Validate email configuration and return status.
    
    Returns:
        Dictionary with configuration status
    """
    api_key = os.getenv('RESEND_API_KEY')
    sender_address = os.getenv('RESEND_SENDER')
    recipient = os.getenv('RECIPIENT_EMAIL')
    
    status = {
        'resend_api_key': bool(api_key),
        'sender_address': bool(sender_address),
        'recipient_email': bool(recipient),
        'is_configured': bool(api_key and recipient)
    }
    
    if status['is_configured']:
        # Mask sensitive data for logging
        status['api_key_preview'] = api_key[:8] + '...' if api_key else None
        status['sender_address_value'] = sender_address or 'Stock Insight <onboarding@resend.dev>'
        status['recipient_email_value'] = recipient
    
    return status


if __name__ == "__main__":
    # Test configuration when run directly
    print("Email Configuration Status:")
    print("-" * 40)
    
    config = validate_email_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    if config['is_configured']:
        print("\n✓ Email is configured!")
        print("Run with --test flag to send a test email")
    else:
        print("\n✗ Email not fully configured")
        print("Set the following environment variables:")
        print("  - RESEND_API_KEY (required)")
        print("  - RESEND_SENDER (optional, defaults to onboarding@resend.dev)")
        print("  - RECIPIENT_EMAIL (required)")
