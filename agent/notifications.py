import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path)


class NotificationService:
    def __init__(self):
        self.pushover_token = os.getenv("PUSHOVER_TOKEN")
        self.pushover_user = os.getenv("PUSHOVER_USER")
        self.smtp_email = os.getenv("SMTP_EMAIL")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.use_tls = os.getenv("USE_TLS", "false").lower() == "true"
        self.notification_enabled = any([
            self.pushover_token,
            self.smtp_email and self.smtp_password,
        ])
    
    def send_scan_complete(
        self, 
        recommendations: List[Dict], 
        regime: str,
        scan_time: datetime,
        sp500_count: int = 0,
        other_count: int = 0
    ):
        if not recommendations:
            return
        
        message = self._format_html_email(recommendations, regime, scan_time, sp500_count, other_count)
        
        subject = f"📊 MIDAS: {regime} Market | {len(recommendations)} Trades (S&P500 + Other)"
        
        if self.pushover_token and self.pushover_user:
            self._send_pushover(message, subject)
        
        if self.smtp_email and self.smtp_password:
            self._send_email(
                subject=subject,
                body=message,
                to_email=self.smtp_email
            )
    
    def send_alert(
        self, 
        ticker: str, 
        strategy: str, 
        signal: str,
        confidence: int
    ):
        message = f"""
🚨 HIGH CONFIDENCE ALERT

{ticker} - {strategy}
Confidence: {confidence}%
Signal: {signal}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M ET')}
"""
        if self.pushover_token and self.pushover_user:
            self._send_pushover(message, f"🚨 {ticker} Alert")
    
    def _calculate_target(self, entry: float, stop: float, trade_type: str, existing_target: float = None) -> float:
        if existing_target:
            return existing_target
        
        risk = abs(entry - stop)
        if trade_type == "LONG":
            return round(entry + (risk * 2), 2)
        else:  # SHORT
            return round(entry - (risk * 2), 2)
    
    def _format_html_email(
        self, 
        recommendations, 
        regime: str, 
        scan_time: datetime,
        sp500_count: int = 0,
        other_count: int = 0
    ) -> str:
        regime_emoji = "📈" if regime == "TREND" else "📊" if regime == "RANGE" else "❓"
        regime_color = "#10b981" if regime == "TREND" else "#f59e0b" if regime == "RANGE" else "#6b7280"
        
        recs_dict = []
        for r in recommendations:
            if hasattr(r, 'model_dump'):
                recs_dict.append(r.model_dump())
            elif isinstance(r, dict):
                recs_dict.append(r)
        
        sp500_recs = [r for r in recs_dict if r.get('is_sp500', False)]
        other_recs = [r for r in recs_dict if not r.get('is_sp500', False)]
        
        sp500_swing = [r for r in sp500_recs if 'SWING' in str(r.get('type', ''))][:10]
        sp500_intraday = [r for r in sp500_recs if 'INTRADAY' in str(r.get('type', ''))][:10]
        other_swing = [r for r in other_recs if 'SWING' in str(r.get('type', ''))][:10]
        other_intraday = [r for r in other_recs if 'INTRADAY' in str(r.get('type', ''))][:10]
        
        def build_table(recs, show_target_col=True):
            if not recs:
                return '<p style="color:#9ca3af;padding:20px;">No opportunities found</p>'
            
            target_header = '<th style="padding:10px;text-align:left;">Target</th>' if show_target_col else ''
            
            rows = ""
            for rec in recs:
                strategies = rec.get("strategies_triggered", [])
                
                trade_type = rec.get('type', 'LONG')
                entry = rec.get("entry_price", 0)
                stop = rec.get("stop_loss", 0)
                
                is_short = "SHORT" in trade_type.upper()
                direction = "SHORT" if is_short else "LONG"
                target = self._calculate_target(entry, stop, direction, rec.get("take_profit"))
                
                direction_color = "#ef4444" if is_short else "#10b981"
                direction_emoji = "📉" if is_short else "📈"
                
                conf_color = "#10b981" if rec.get('confidence_score', 0) >= 80 else "#fbbf24" if rec.get('confidence_score', 0) >= 60 else "#9ca3af"
                
                strategies_html = ""
                for s in strategies:
                    priority_color = "#ffd700" if s.get("priority") == "ELITE" else "#10b981" if s.get("priority") == "HIGH" else "#60a5fa"
                    strategies_html += f'<span style="background:{priority_color};color:#000;padding:2px 6px;border-radius:3px;font-size:10px;margin:2px;display:inline-block;">{s["name"]}</span>'
                
                target_html = f'<td style="padding:10px;border-bottom:1px solid #374151;color:#10b981;font-weight:bold;">${target:.2f}</td>' if show_target_col else ''
                
                rows += f"""
                <tr style="background:#1f2937;">
                    <td style="padding:10px;border-bottom:1px solid #374151;font-weight:bold;">#{rec['rank']}</td>
                    <td style="padding:10px;border-bottom:1px solid #374151;">
                        <strong style="font-size:16px;color:#60a5fa;">{rec['ticker']}</strong>
                        <span style="font-size:11px;color:{direction_color};margin-left:5px;">{direction_emoji}</span>
                        <br><span style="font-size:10px;color:#9ca3af;">{rec.get('stock_price', '')}</span>
                    </td>
                    <td style="padding:10px;border-bottom:1px solid #374151;font-weight:bold;color:{direction_color};">{trade_type}</td>
                    <td style="padding:10px;border-bottom:1px solid #374151;font-weight:bold;color:#10b981;">${entry:.2f}</td>
                    <td style="padding:10px;border-bottom:1px solid #374151;font-weight:bold;color:#ef4444;">${stop:.2f}</td>
                    {target_html}
                    <td style="padding:10px;border-bottom:1px solid #374151;font-weight:bold;color:#fbbf24;">{rec.get('holding_period', 'N/A')}</td>
                    <td style="padding:10px;border-bottom:1px solid #374151;font-weight:bold;color:{conf_color};font-size:16px;">{rec.get('confidence_score', 0)}%</td>
                </tr>
                <tr style="background:#111827;">
                    <td colspan={7 if show_target_col else 6} style="padding:12px;border-bottom:2px solid #374151;">
                        <div style="margin-bottom:8px;">
                            <strong style="color:#fff;font-size:11px;">STRATEGIES:</strong><br>
                            {strategies_html}
                        </div>
                        <div>
                            <strong style="color:#fff;font-size:11px;">REASONING:</strong><br>
                            <span style="color:#d1d5db;font-size:11px;">{rec.get('reasoning', 'No reasoning provided')}</span>
                        </div>
                    </td>
                </tr>
                """
            
            return f"""
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#374151;color:#fff;">
                        <th style="padding:10px;text-align:left;width:40px;">#</th>
                        <th style="padding:10px;text-align:left;">Ticker</th>
                        <th style="padding:10px;text-align:left;width:70px;">Type</th>
                        <th style="padding:10px;text-align:left;">Entry</th>
                        <th style="padding:10px;text-align:left;">Stop</th>
                        {target_header}
                        <th style="padding:10px;text-align:left;">Hold</th>
                        <th style="padding:10px;text-align:left;width:50px;">Conf</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @media only screen and (max-width: 600px) {{
            table {{ font-size: 11px; }}
            th, td {{ padding: 5px !important; }}
        }}
    </style>
</head>
<body style="margin:0;padding:0;background:#111827;font-family:Arial,sans-serif;">
    <div style="max-width:950px;margin:0 auto;padding:15px;">
        
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);padding:25px;border-radius:12px 12px 0 0;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:26px;">📊 MIDAS</h1>
            <p style="color:#93c5fd;margin:8px 0 0;font-size:13px;">Daily Trade Recommendations</p>
        </div>
        
        <!-- Regime Banner -->
        <div style="background:{regime_color};padding:20px;text-align:center;">
            <h2 style="color:#fff;margin:0;font-size:30px;">{regime_emoji} {regime} MARKET</h2>
            <p style="color:#fff;margin:8px 0 0;font-size:13px;opacity:0.9;">
                Scan: {scan_time.strftime('%Y-%m-%d %H:%M ET')} | {sp500_count} S&P 500 + {other_count} Other Stocks Scanned
            </p>
        </div>
        
        <!-- S&P 500 Section -->
        <div style="background:#1f2937;padding:20px;border-radius:0 0 0 0;margin-top:0;">
            <h3 style="color:#ffd700;margin:0 0 15px 0;font-size:20px;border-bottom:2px solid #ffd700;padding-bottom:10px;">
                🏛️ S&P 500 TRADES (Top 10 Each)
            </h3>
            
            <!-- S&P 500 SWING -->
            <h4 style="color:#3b82f6;margin:15px 0 10px 0;font-size:16px;">📈 SWING ({len(sp500_swing)})</h4>
            {build_table(sp500_swing, True)}
            
            <!-- S&P 500 INTRADAY -->
            <h4 style="color:#f97316;margin:20px 0 10px 0;font-size:16px;">⚡ INTRADAY ({len(sp500_intraday)})</h4>
            {build_table(sp500_intraday, True)}
        </div>
        
        <!-- Other Stocks Section -->
        <div style="background:#1f2937;padding:20px;border-radius:0 0 12px 12px;margin-top:2px;">
            <h3 style="color:#a855f7;margin:0 0 15px 0;font-size:20px;border-bottom:2px solid #a855f7;padding-bottom:10px;">
                🚀 OTHER STOCKS (Small Cap, Penny, etc.) (Top 10 Each)
            </h3>
            
            <!-- Other SWING -->
            <h4 style="color:#3b82f6;margin:15px 0 10px 0;font-size:16px;">📈 SWING ({len(other_swing)})</h4>
            {build_table(other_swing, True)}
            
            <!-- Other INTRADAY -->
            <h4 style="color:#f97316;margin:20px 0 10px 0;font-size:16px;">⚡ INTRADAY ({len(other_intraday)})</h4>
            {build_table(other_intraday, True)}
        </div>
        
        <!-- Footer -->
        <div style="text-align:center;padding:20px;color:#6b7280;font-size:11px;">
            <p>Generated by MIDAS | 📈=LONG 📉=SHORT | {len(recommendations)} Total Recommendations</p>
        </div>
        
    </div>
</body>
</html>
        """
        return html
    
    def _send_pushover(self, message: str, title: str):
        try:
            import requests
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": self.pushover_token,
                    "user": self.pushover_user,
                    "message": message,
                    "title": title,
                    "priority": 1,
                    "sound": "magic"
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Pushover error: {e}")
            return False
    
    def _send_email(self, subject: str, body: str, to_email: str):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))
            
            if self.use_tls:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(self.smtp_email, self.smtp_password)
                    server.send_message(msg)
            else:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(self.smtp_email, self.smtp_password)
                    server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False


_notification_service = None

def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
