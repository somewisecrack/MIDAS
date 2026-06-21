#!/usr/bin/env python3
"""
Email Notification Setup for Trading Agent

Instructions:
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication
3. Go to App Passwords (search for it)
4. Create a new app password for "Mail"
5. Enter the 16-character password below

Note: You MUST use an App Password, not your regular Gmail password.
"""

import os
import sys

def setup_email():
    print("=" * 60)
    print("  TRADING AGENT - EMAIL NOTIFICATION SETUP")
    print("=" * 60)
    print()
    print("This script will help you configure email notifications.")
    print()
    print("REQUIREMENTS:")
    print("  1. Gmail account with 2-Factor Authentication enabled")
    print("  2. An App Password (not your regular password)")
    print()
    print("To get an App Password:")
    print("  1. Go to: https://myaccount.google.com/security")
    print("  2. Search for 'App Passwords'")
    print("  3. Create one for 'Mail'")
    print()
    
    email = input("Enter your Gmail address: ").strip()
    if not email:
        print("Email required.")
        return
    
    password = input("Enter your App Password (16 characters): ").strip()
    if not password:
        print("App Password required.")
        return
    
    # Test the connection
    print("\nTesting email connection...")
    try:
        import smtplib
        import ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(email, password)
        
        print("[OK] Email connection successful!")
        
        # Ask if user wants to save to shell profile
        save = input("\nSave to ~/.zshrc? (y/n): ").strip().lower()
        if save == 'y':
            with open(os.path.expanduser("~/.zshrc"), "a") as f:
                f.write(f'\n# Trading Agent Email\n')
                f.write(f'export SMTP_EMAIL="{email}"\n')
                f.write(f'export SMTP_PASSWORD="{password}"\n')
            print("Saved to ~/.zshrc")
            print("Run 'source ~/.zshrc' or restart terminal to apply.")
        
        print("\nSETUP COMPLETE!")
        print("Restart the trading agent for changes to take effect:")
        print("  cd /Users/rahulgirishkumar/TRADING")
        print("  python3 -m agent.main")
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  - Make sure you used an App Password, not your regular password")
        print("  - Make sure 2FA is enabled on your Google account")
        print("  - Check if 'Less secure app access' is disabled (this is expected)")
        return False
    
    return True


if __name__ == "__main__":
    setup_email()
