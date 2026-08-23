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
        color = "#9CAF88" if a.get('change_pct', 0) >= 0 else "#C0392B"
        sign = "+" if a.get('change_pct', 0) > 0 else ""
        rows += f"""
        <tr>
            <td style="padding: 12px 15px; border-bottom: 1px solid #E0E0E0; color: #333333; font-weight: 500;">{a.get('name')} <span style="color: #8B8C89; font-size: 0.9em; font-weight: normal;">({a.get('asset_type')})</span></td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #E0E0E0; color: #333333;">₹{a.get('current_price')}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #E0E0E0; color: {color}; font-weight: bold;">{sign}{a.get('change_pct')}%</td>
        </tr>
        """
        
    import markdown
    # Convert AI markdown to HTML
    ai_html = markdown.markdown(ai_report)
        
    return f"""
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #F9F6EE; padding: 40px 20px; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #EAEAEA;">
            <div style="background-color: #8B7355; color: #F9F6EE; padding: 25px 30px;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 0.5px;">TrackBucks Portfolio Review</h1>
            </div>
            
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #333333; margin-top: 0;">Hi {user_name},</p>
                <p style="font-size: 16px; color: #555555; margin-bottom: 25px;">Here is your scheduled portfolio summary. Let's take a look at how things are doing.</p>
                
                <div style="border-radius: 8px; overflow: hidden; border: 1px solid #E0E0E0; margin-bottom: 35px;">
                    <table style="width: 100%; border-collapse: collapse; background-color: #FFFFFF;">
                        <thead>
                            <tr style="background-color: #F5F5DC; color: #333333; text-align: left;">
                                <th style="padding: 12px 15px; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Asset</th>
                                <th style="padding: 12px 15px; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Price</th>
                                <th style="padding: 12px 15px; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Change</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
                
                <h2 style="color: #9CAF88; font-size: 20px; border-bottom: 2px solid #F5F5DC; padding-bottom: 8px; margin-bottom: 20px;">My Thoughts on This</h2>
                <div style="color: #444444; font-size: 15px; background-color: #FAFAFA; padding: 20px; border-left: 4px solid #9CAF88; border-radius: 0 8px 8px 0;">
                    {ai_html}
                </div>
                
                <p style="margin-top: 40px; font-size: 12px; color: #8B8C89; text-align: center; border-top: 1px solid #EAEAEA; padding-top: 20px;">
                    Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>
    </div>
    """

def build_alert_html(user_name: str, asset_name: str, asset_type: str, change_pct: float, current_price: float, ai_analysis: str) -> str:
    import markdown
    ai_html = markdown.markdown(ai_analysis)
    
    return f"""
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #F9F6EE; padding: 40px 20px; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 25px rgba(192, 57, 43, 0.15); border: 1px solid #FADBD8;">
            <div style="background-color: #C0392B; color: #FFFFFF; padding: 25px 30px;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 0.5px;">⚠️ Urgent Market Update</h1>
            </div>
            
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #333333; margin-top: 0;">Hi {user_name},</p>
                <p style="font-size: 16px; color: #555555;">I wanted to reach out because one of your assets just experienced a significant drop.</p>
                
                <div style="background-color: #FDEDEC; border-radius: 8px; padding: 20px; margin: 25px 0; border: 1px solid #F5B7B1; text-align: center;">
                    <h2 style="margin: 0 0 10px 0; color: #C0392B; font-size: 22px;">{asset_name} <span style="font-size: 16px; color: #922B21; font-weight: normal;">({asset_type})</span></h2>
                    <p style="margin: 5px 0; font-size: 16px; color: #641E16;">Current Price: <strong>₹{current_price}</strong></p>
                    <p style="margin: 5px 0; font-size: 18px; color: #C0392B;">Today's Drop: <strong>{change_pct}%</strong></p>
                </div>
                
                <h2 style="color: #8B7355; font-size: 20px; border-bottom: 2px solid #F5F5DC; padding-bottom: 8px; margin-bottom: 20px;">Let's Break This Down</h2>
                <div style="color: #444444; font-size: 15px; background-color: #FAFAFA; padding: 20px; border-left: 4px solid #8B7355; border-radius: 0 8px 8px 0;">
                    {ai_html}
                </div>
                
                <p style="margin-top: 40px; font-size: 12px; color: #8B8C89; text-align: center; border-top: 1px solid #EAEAEA; padding-top: 20px;">
                    Alert sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>
    </div>
    """
