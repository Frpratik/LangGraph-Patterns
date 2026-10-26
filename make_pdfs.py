#run this once to create the two pdfs that the RAG part will read
#python make_pdfs.py

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
styles = getSampleStyleSheet()


def make_pdf(filename: str, title: str, sections: dict):
    doc = SimpleDocTemplate(os.path.join(DATA_DIR, filename), pagesize=A4)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for heading, lines in sections.items():
        story.append(Paragraph(heading, styles["Heading2"]))
        for line in lines:
            story.append(Paragraph(line, styles["BodyText"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))
    doc.build(story)
    print(f"created data/{filename}")


make_pdf("billing_policy.pdf", "HiveBoard - Billing and Refund Policy", {
    "1. Plans and pricing": [
        "HiveBoard has three plans: Basic costs Rs 499 per month, Pro costs Rs 999 per month and Business costs Rs 2499 per month.",
        "Annual plans are available for all tiers and cost 10 months of the monthly price (Business annual is Rs 24990).",
        "All prices are exclusive of 18 percent GST. An invoice is emailed after every successful payment.",
    ],
    "2. Billing cycle and renewal": [
        "Your billing cycle starts on the day you subscribe. Plans renew automatically at the end of each cycle.",
        "Cancellation takes effect at the end of the current cycle. You keep access until then, and no partial month is refunded.",
    ],
    "3. Failed payments": [
        "If a payment fails we retry it 3 times over 5 days. If all retries fail the account is suspended.",
        "A suspended account is restored immediately once the payment is completed. Data is kept for 30 days.",
    ],
    "4. Refund policy": [
        "Monthly plans: a full refund is available within 7 days of the first purchase. After 7 days no refund is given.",
        "Annual plans: a full refund is available within 14 days of purchase. After 14 days no refund is given.",
        "Duplicate or accidental double charges are refunded in full at any time, no matter how old.",
        "Refunds above Rs 2000 need manager approval before they are processed.",
        "Approved refunds reach the original payment method in 5 to 7 business days.",
    ],
})

make_pdf("tech_faq.pdf", "HiveBoard - Technical Support FAQ", {
    "1. Login problems": [
        "Use the Forgot Password link on the login page. The reset link is valid for 30 minutes.",
        "After 5 wrong password attempts the account is locked for 15 minutes. Wait and try again, or reset the password.",
        "If two factor authentication codes are not accepted, check that your phone time is set to automatic.",
    ],
    "2. App crashes and slow performance": [
        "Update to the latest version of the app first. Most crashes are fixed in updates.",
        "Clear the app cache from Settings, then restart the app. On the web, hard refresh with Ctrl+Shift+R.",
        "Supported browsers are the latest two versions of Chrome, Edge, Firefox and Safari.",
    ],
    "3. Sync issues": [
        "If boards do not sync, check your internet connection and log out and back in once.",
        "Sync can take up to 2 minutes on large boards with more than 500 cards.",
    ],
    "4. Data and API": [
        "You can export all your data as CSV or JSON from Settings, then Data Export. Exports are ready in a few minutes.",
        "The API allows 100 requests per minute on the Pro plan and 500 per minute on Business. Basic has no API access.",
        "Live service status is shown on the status page. If the status page is green and the problem remains, contact support with a screenshot.",
    ],
})
