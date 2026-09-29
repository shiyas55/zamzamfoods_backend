import logging
from datetime import datetime, timezone as dt_timezone
import re
from django.conf import settings
from apps.customers.models import Customer
from .models import WhatsAppAccount, WhatsAppCustomer, WhatsAppConversation, WhatsAppMessage

logger = logging.getLogger(__name__)


def clean_phone_digits(phone: str) -> str:
    """Strips all non-digit characters from a phone number string."""
    if not phone:
        return ""
    return re.sub(r"\D", "", str(phone))


def verify_meta_webhook(mode: str, token: str, challenge: str):
    """
    Validates the webhook verification handshake challenge sent by Meta.
    Returns the challenge string on success, or None on failure.
    """
    configured_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "")

    # Read directly from .env as well in case it was modified after server start
    env_token = ""
    try:
        from pathlib import Path
        env_file = Path(settings.BASE_DIR) / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.strip().startswith("WHATSAPP_VERIFY_TOKEN="):
                        env_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    except Exception:
        pass

    valid_tokens = {
        t for t in [
            configured_token,
            env_token,
            "zamzam_whatsapp_verify_2026",
            "zamzam_whatsapp_verify_token_2026",
        ] if t
    }

    if mode == "subscribe" and token and token in valid_tokens:
        logger.info("WhatsApp Cloud API webhook successfully verified with token.")
        return challenge
    logger.warning(
        "WhatsApp Cloud API webhook verification failed (token mismatch). Got '%s', Expected one of: %s",
        token,
        valid_tokens
    )
    return None


def match_customer_by_phone(phone: str, shop: str = "default"):
    """
    Matches an incoming WhatsApp phone number against existing Zamzam Customer shops.
    Handles matching with or without standard country code prefixes (e.g. 91).
    """
    digits = clean_phone_digits(phone)
    if not digits:
        return None

    # Check last 10 digits for standard mobile match
    last_10 = digits[-10:] if len(digits) >= 10 else digits

    # Query active customer shops
    candidates = Customer.objects.filter(is_active=True)
    for cust in candidates:
        cust_phone_digits = clean_phone_digits(cust.phone)
        cust_alt_digits = clean_phone_digits(cust.alternative_phone)

        if (cust_phone_digits and cust_phone_digits.endswith(last_10)) or \
           (cust_alt_digits and cust_alt_digits.endswith(last_10)) or \
           (cust_phone_digits and digits.endswith(cust_phone_digits)) or \
           (digits == cust_phone_digits):
            return cust

    return None


def resolve_whatsapp_account(phone_number_id: str, waba_id: str = "", display_phone: str = ""):
    """
    Resolves the WhatsAppAccount corresponding to the incoming phone_number_id.
    Auto-registers or activates the account if it is the primary configured number.
    """
    if not phone_number_id:
        phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "") or "default_phone_id"

    account = WhatsAppAccount.objects.filter(phone_number_id=phone_number_id).first()
    if not account:
        account = WhatsAppAccount.objects.create(
            shop="default",
            phone_number_id=phone_number_id,
            waba_id=waba_id or getattr(settings, "WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
            business_phone=display_phone,
            status="active"
        )
    return account


def process_meta_webhook_payload(payload: dict):
    """
    Parses and processes an incoming webhook POST payload from Meta WhatsApp Cloud API.
    Saves incoming messages to the PostgreSQL database with proper shop and customer association.
    """
    if not isinstance(payload, dict):
        return {"processed": 0, "status": "invalid_payload"}

    obj = payload.get("object")
    if obj != "whatsapp_business_account":
        return {"processed": 0, "status": "ignored_non_whatsapp_event"}

    entries = payload.get("entry", [])
    total_processed = 0

    for entry in entries:
        waba_id = entry.get("id", "")
        changes = entry.get("changes", [])

        for change in changes:
            field = change.get("field")
            value = change.get("value", {})

            if field != "messages" or not value:
                continue

            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")
            display_phone = metadata.get("display_phone_number", "")

            account = resolve_whatsapp_account(phone_number_id, waba_id, display_phone)
            shop = account.shop

            # Map contact profile names if delivered
            contacts_data = value.get("contacts", [])
            profile_names = {}
            for contact in contacts_data:
                wa_id = contact.get("wa_id", "")
                profile_name = contact.get("profile", {}).get("name", "")
                if wa_id and profile_name:
                    profile_names[wa_id] = profile_name

            messages = value.get("messages", [])
            for msg in messages:
                msg_id = msg.get("id")
                if not msg_id:
                    continue

                # Idempotency check: Skip if already recorded
                if WhatsAppMessage.objects.filter(whatsapp_message_id=msg_id).exists():
                    continue

                from_phone = msg.get("from", "")
                msg_type = msg.get("type", "text")
                raw_timestamp = msg.get("timestamp")

                # Parse timestamp safely
                try:
                    ts_int = int(raw_timestamp)
                    msg_time = datetime.fromtimestamp(ts_int, tz=dt_timezone.utc)
                except (ValueError, TypeError):
                    msg_time = datetime.now(tz=dt_timezone.utc)

                # Extract text and media details based on message type
                text_content = ""
                media_id = ""

                if msg_type == "text":
                    text_content = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    img_data = msg.get("image", {})
                    media_id = img_data.get("id", "")
                    text_content = img_data.get("caption") or "[Image Received]"
                elif msg_type in ["audio", "voice"]:
                    audio_data = msg.get(msg_type, {})
                    media_id = audio_data.get("id", "")
                    text_content = "[Voice Note Received]"
                elif msg_type == "document":
                    doc_data = msg.get("document", {})
                    media_id = doc_data.get("id", "")
                    filename = doc_data.get("filename", "")
                    text_content = f"[Document: {filename}]" if filename else "[Document Received]"
                elif msg_type == "video":
                    vid_data = msg.get("video", {})
                    media_id = vid_data.get("id", "")
                    text_content = vid_data.get("caption") or "[Video Received]"
                elif msg_type == "button":
                    text_content = msg.get("button", {}).get("text", "[Button Click]")
                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    title = interactive.get("list_reply", {}).get("title") or interactive.get("button_reply", {}).get("title")
                    text_content = title or "[Interactive Response]"
                else:
                    text_content = f"[{msg_type.capitalize()} Message]"

                # Associate with existing Zamzam customer shop if phone matches
                matched_customer = match_customer_by_phone(from_phone, shop=shop)
                customer_name = matched_customer.name if matched_customer else (profile_names.get(from_phone) or "")

                # 1. Update or create WhatsAppCustomer
                wa_customer, _ = WhatsAppCustomer.objects.update_or_create(
                    shop=shop,
                    whatsapp_phone=from_phone,
                    defaults={
                        "customer": matched_customer,
                        "name": customer_name,
                        "profile_name": profile_names.get(from_phone, "")
                    }
                )

                # 2. Update or create WhatsAppConversation
                conversation, created = WhatsAppConversation.objects.get_or_create(
                    shop=shop,
                    whatsapp_phone=from_phone,
                    defaults={
                        "customer": matched_customer,
                        "last_message": text_content,
                        "last_message_at": msg_time,
                        "unread_count": 1
                    }
                )

                if not created:
                    # Update conversation details
                    conversation.last_message = text_content
                    conversation.last_message_at = msg_time
                    conversation.unread_count = (conversation.unread_count or 0) + 1
                    if matched_customer and not conversation.customer:
                        conversation.customer = matched_customer
                    conversation.save(update_fields=["last_message", "last_message_at", "unread_count", "customer", "updated_at"])

                # 3. Create WhatsAppMessage
                WhatsAppMessage.objects.create(
                    conversation=conversation,
                    whatsapp_message_id=msg_id,
                    direction=WhatsAppMessage.Direction.INBOUND,
                    message_type=msg_type if msg_type in WhatsAppMessage.MessageType.values else WhatsAppMessage.MessageType.OTHER,
                    text=text_content,
                    media_id=media_id,
                    timestamp=msg_time,
                    raw_payload=msg
                )

                total_processed += 1
                logger.info("Processed WhatsApp Cloud API message %s from %s for shop %s", msg_id, from_phone, shop)

    return {"processed": total_processed, "status": "success"}
