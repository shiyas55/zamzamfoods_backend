import os
import django
from datetime import datetime, timedelta, timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.customers.models import Customer
from apps.whatsapp.models import WhatsAppAccount, WhatsAppCustomer, WhatsAppConversation, WhatsAppMessage
from apps.whatsapp.services import clean_phone_digits


def seed_whatsapp_data():
    print("Seeding WhatsApp Cloud API test account and messages...")

    # 1. Ensure WhatsAppAccount
    account, _ = WhatsAppAccount.objects.get_or_create(
        phone_number_id="100234567890123",
        defaults={
            "shop": "default",
            "waba_id": "200345678901234",
            "business_phone": "+91 98450 12345",
            "status": "active",
        }
    )

    customers = list(Customer.objects.filter(is_active=True)[:10])
    if not customers:
        print("No customers found in database. Please run add_shops.py first.")
        return

    now = datetime.now(tz=timezone.utc)

    sample_conversations = [
        {
            "offset_min": 15,
            "messages": [
                ("Salam brother, please send today's wholesale order.", "text", 25),
                ("[Voice Note: 0:24]", "voice", 22),
                ("Order requirement:\n• Kubbus: 45 pkts\n• Romali: 20 pkts", "text", 18),
                ("Please confirm delivery timing for North Route.", "text", 15),
            ]
        },
        {
            "offset_min": 35,
            "messages": [
                ("Salam! Today extra requirement for evening catering.", "text", 50),
                ("• Kubbus: 80 packets\n• Romali: 40 packets", "text", 40),
                ("Will transfer payment via GPay upon delivery.", "text", 35),
            ]
        },
        {
            "offset_min": 75,
            "messages": [
                ("Salam, yesterday's Romali stock was very fresh. Thank you.", "text", 90),
                ("For today: Kubbus 30, Romali 15 please.", "text", 75),
            ]
        },
        {
            "offset_min": 120,
            "messages": [
                ("[Store Photo: Display Rack Empty]", "image", 140),
                ("Bread shelf is empty, please send driver early if possible.", "text", 120),
            ]
        },
        {
            "offset_min": 180,
            "messages": [
                ("Standard daily order for today: 25 Kubbus, 10 Romali.", "text", 180),
            ]
        },
    ]

    for i, sample in enumerate(sample_conversations):
        if i >= len(customers):
            break
        cust = customers[i]
        phone_digits = clean_phone_digits(cust.phone)
        if len(phone_digits) == 10:
            phone_digits = f"91{phone_digits}"

        wa_cust, _ = WhatsAppCustomer.objects.update_or_create(
            shop="default",
            whatsapp_phone=phone_digits,
            defaults={
                "customer": cust,
                "name": cust.name,
                "profile_name": cust.owner_name or cust.name,
            }
        )

        last_text = sample["messages"][-1][0]
        last_time = now - timedelta(minutes=sample["offset_min"])

        conv, _ = WhatsAppConversation.objects.update_or_create(
            shop="default",
            whatsapp_phone=phone_digits,
            defaults={
                "customer": cust,
                "last_message": last_text,
                "last_message_at": last_time,
                "unread_count": len(sample["messages"]),
            }
        )

        for m_idx, (text, mtype, mins_ago) in enumerate(sample["messages"]):
            msg_id = f"wamid.TEST_{cust.id}_{m_idx}_{mins_ago}"
            msg_time = now - timedelta(minutes=mins_ago)
            WhatsAppMessage.objects.update_or_create(
                whatsapp_message_id=msg_id,
                defaults={
                    "conversation": conv,
                    "direction": WhatsAppMessage.Direction.INBOUND,
                    "message_type": mtype,
                    "text": text,
                    "media_id": f"media_sample_{m_idx}" if mtype in ["voice", "image"] else "",
                    "timestamp": msg_time,
                    "raw_payload": {"from": phone_digits, "type": mtype, "text": {"body": text}}
                }
            )

    print(f"Successfully seeded {len(sample_conversations)} real WhatsApp conversations with incoming messages!")


if __name__ == '__main__':
    seed_whatsapp_data()
