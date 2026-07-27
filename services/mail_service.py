import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import settings

async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        print("Warning: SMTP_EMAIL or SMTP_PASSWORD is not set.")
        return False
        
    def _send():
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
            
    return await asyncio.to_thread(_send)

def build_report_html(user_name: str, assets_data: list, ai_report: str) -> str:
    rows = ""
    for a in assets_data:
        color = "#6B8E6B" if a.get('change_pct', 0) >= 0 else "#C0392B"
        rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #444;">{a.get('name')} ({a.get('asset_type')})</td>
            <td style="padding: 10px; border-bottom: 1px solid #444;">{a.get('current_price')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #444; color: {color};">{a.get('change_pct')}%</td>
        </tr>
        """
        
    return f"""
    <div style="font-family: Arial, sans-serif; background-color: #2A2A2A; color: #FAF3E0; padding: 20px;">
        <h1 style="color: #8B7355; border-bottom: 2px solid #8B7355; padding-bottom: 10px;">TrackBucks Portfolio Report</h1>
        <p>Hello {user_name},</p>
        <p>Here is your scheduled portfolio summary:</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #333;">
            <tr style="background-color: #8B7355; color: #fff;">
                <th style="padding: 10px; text-align: left;">Asset</th>
                <th style="padding: 10px; text-align: left;">Current Price</th>
                <th style="padding: 10px; text-align: left;">Change %</th>
            </tr>
            {rows}
        </table>
        
        <h2 style="color: #6B8E6B; margin-top: 30px;">AI Analysis</h2>
        <div style="background-color: #333; padding: 15px; border-left: 4px solid #6B8E6B;">
            {ai_report.replace(chr(10), '<br>')}
        </div>
        
        <p style="margin-top: 30px; font-size: 12px; color: #aaa;">Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """

def build_alert_html(user_name: str, asset_name: str, asset_type: str, change_pct: float, current_price: float, ai_analysis: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; background-color: #2A2A2A; color: #FAF3E0; padding: 20px; border: 2px solid #C0392B;">
        <h1 style="color: #C0392B; border-bottom: 2px solid #C0392B; padding-bottom: 10px;">⚠️ TrackBucks Disaster Alert</h1>
        <p>Hello {user_name},</p>
        <p>Your tracked asset <strong>{asset_name}</strong> ({asset_type}) has experienced a significant drop.</p>
        
        <div style="background-color: #333; padding: 15px; margin: 20px 0;">
            <p><strong>Current Price:</strong> {current_price}</p>
            <p><strong>Drop:</strong> <span style="color: #C0392B; font-weight: bold;">{change_pct}%</span></p>
        </div>
        
        <h2 style="color: #8B7355;">AI Assessment</h2>
        <div style="background-color: #333; padding: 15px; border-left: 4px solid #8B7355;">
            {ai_analysis.replace(chr(10), '<br>')}
        </div>
        
        <p style="margin-top: 30px; font-size: 12px; color: #aaa;">Alert sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """
