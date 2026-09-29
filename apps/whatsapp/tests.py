from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.conf import settings
from apps.customers.models import Customer
from apps.routes.models import Route
from apps.accounts.models import User
from .models import WhatsAppAccount, WhatsAppCustomer, WhatsAppConversation, WhatsAppMessage


class WhatsAppCloudAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.route = Route.objects.create(name="North Route", code="NR")
        self.customer = Customer.objects.create(
            name="Al Madina Supermarket",
            owner_name="Ahmed Khan",
            phone="9876543210",
            route=self.route,
            address="Building 12, Market Road"
        )
        self.user = User.objects.create_user(
            username="manager1",
            password="testpassword123",
            role=User.Role.MANAGER
        )
        self.verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "zamzam_verify_token_2026")

    def test_webhook_verification_success(self):
        url = reverse("whatsapp:webhook")
        response = self.client.get(
            url,
            {"hub.mode": "subscribe", "hub.verify_token": self.verify_token, "hub.challenge": "1158201236"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "1158201236")

    def test_webhook_verification_failure(self):
        url = reverse("whatsapp:webhook")
        response = self.client.get(
            url,
            {"hub.mode": "subscribe", "hub.verify_token": "wrong_token", "hub.challenge": "1158201236"}
        )
        self.assertEqual(response.status_code, 403)

    def test_webhook_incoming_text_message(self):
        url = reverse("whatsapp:webhook")
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "200345678901234",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15550254583",
                                    "phone_number_id": "100234567890123"
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Ahmed Store Manager"},
                                        "wa_id": "919876543210"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "wamid.HBgLMjAyNjA5MjcxMjU1",
                                        "timestamp": "1711234567",
                                        "type": "text",
                                        "text": {
                                            "body": "Salam brother, please send 45 Kubbus today."
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        # Confirm message was stored in DB
        msg = WhatsAppMessage.objects.filter(whatsapp_message_id="wamid.HBgLMjAyNjA5MjcxMjU1").first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.text, "Salam brother, please send 45 Kubbus today.")
        self.assertEqual(msg.direction, "inbound")
        self.assertEqual(msg.message_type, "text")

        # Confirm conversation exists and is matched to the customer
        conversation = msg.conversation
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.customer, self.customer)
        self.assertEqual(conversation.whatsapp_phone, "919876543210")
        self.assertEqual(conversation.last_message, "Salam brother, please send 45 Kubbus today.")
        self.assertEqual(conversation.unread_count, 1)

    def test_conversations_api(self):
        # First trigger incoming message
        self.test_webhook_incoming_text_message()

        self.client.force_authenticate(user=self.user)
        url = reverse("whatsapp:conversation_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) and "results" in data else data
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["customer"]["name"], "Al Madina Supermarket")

        # Test customer conversation endpoint
        cust_url = reverse("whatsapp:customer_conversation", kwargs={"customer_id": self.customer.id})
        cust_resp = self.client.get(cust_url)
        self.assertEqual(cust_resp.status_code, 200)
        cust_data = cust_resp.json()
        self.assertEqual(cust_data["whatsapp_phone"], "919876543210")
        self.assertGreaterEqual(len(cust_data["messages"]), 1)

    def test_tenant_security_isolation(self):
        # Create a conversation belonging to a different shop
        other_conv = WhatsAppConversation.objects.create(
            shop="other_shop_tenant",
            whatsapp_phone="919999999999",
            last_message="Private message for another shop",
            unread_count=1
        )

        # Authenticate user from "default" shop
        self.client.force_authenticate(user=self.user)

        # Request conversation list
        url = reverse("whatsapp:conversation_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) and "results" in data else data

        # Confirm the other shop's conversation is NOT returned
        conv_ids = [c["id"] for c in results]
        self.assertNotIn(str(other_conv.id), conv_ids)

        # Confirm direct access to another shop's conversation returns 404
        detail_url = reverse("whatsapp:conversation_detail", kwargs={"pk": other_conv.id})
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, 404)

