#!/usr/bin/env python3
"""Test email notification"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.notifications import get_notification_service

def test_email():
    print("Testing email notification...")
    
    notifier = get_notification_service()
    
    if not notifier.smtp_email:
        print("ERROR: SMTP_EMAIL not configured in .env file")
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        print(f"\nEdit {env_path} and add your credentials:")
        print("  SMTP_EMAIL=your_email@gmail.com")
        print("  SMTP_PASSWORD=your_app_password")
        return False
    
    # Test with sample data
    test_recs = [
        {
            "rank": 1,
            "ticker": "AAPL",
            "type": "SWING",
            "entry_price": 175.50,
            "stop_loss": 168.00,
            "holding_period": "3-5 days",
            "confidence_score": 85,
            "strategies_triggered": [
                {"name": "Minervini SEPA", "signal": "Stage 2 uptrend"}
            ]
        }
    ]
    
    success = notifier.send_scan_complete(
        recommendations=test_recs,
        regime="TREND",
        scan_time=__import__('datetime').datetime.now()
    )
    
    if success:
        print("✓ Test email sent successfully!")
        print(f"  To: {notifier.smtp_email}")
    else:
        print("✗ Failed to send test email")
        print("  Check your .env settings and app password")
    
    return success

if __name__ == "__main__":
    test_email()
