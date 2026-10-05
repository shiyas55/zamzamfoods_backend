import io
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.customers.models import Customer, CustomerDocument
from apps.routes.models import Route, Driver

class CustomerDocumentsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_user",
            email="owner@zamzam.com",
            password="OwnerPassword123!",
            role="OWNER",
        )
        self.manager = User.objects.create_user(
            username="manager_user",
            email="manager@zamzam.com",
            password="ManagerPassword123!",
            role="MANAGER",
        )
        self.driver_user = User.objects.create_user(
            username="driver_user",
            email="driver@zamzam.com",
            password="DriverPassword123!",
            role="DRIVER",
        )

        self.route1 = Route.objects.create(name="Route North", code="RN-01")
        self.route2 = Route.objects.create(name="Route South", code="RS-02")

        self.driver = Driver.objects.create(
            user=self.driver_user,
            assigned_route=self.route1,
        )

        self.customer1 = Customer.objects.create(
            name="Al-Noor Bakery",
            owner_name="Noor",
            phone="9876543210",
            address="North Bazaar",
            route=self.route1,
        )
        self.customer2 = Customer.objects.create(
            name="South Star Mart",
            owner_name="Salim",
            phone="9876543211",
            address="South Junction",
            route=self.route2,
        )

    def test_single_document_upload_and_crud(self):
        self.client.force_authenticate(user=self.manager)
        test_file = SimpleUploadedFile("fssai_cert.pdf", b"%PDF-1.4 dummy fssai content", content_type="application/pdf")
        
        # 1. Create
        payload = {
            "customer": str(self.customer1.id),
            "title": "FSSAI Food License 2026",
            "document_type": CustomerDocument.DocumentType.FSSAI_LICENSE,
            "document_number": "FSSAI-1234567890",
            "expiry_date": "2027-12-31",
            "notes": "Renewed valid certificate",
            "file": test_file,
        }
        res = self.client.post("/api/v1/customer-documents/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        doc_id = res.data["id"]
        self.assertEqual(res.data["title"], "FSSAI Food License 2026")
        self.assertEqual(res.data["document_type"], "FSSAI_LICENSE")
        self.assertEqual(res.data["file_name"], "fssai_cert.pdf")
        self.assertGreater(res.data["file_size"], 0)
        self.assertTrue(res.data["file_url"])

        # 2. Retrieve
        res = self.client.get(f"/api/v1/customer-documents/{doc_id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["customer_name"], "Al-Noor Bakery")

        # 3. Update
        res = self.client.patch(f"/api/v1/customer-documents/{doc_id}/", {"notes": "Updated note"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["notes"], "Updated note")

        # 4. Delete
        res = self.client.delete(f"/api/v1/customer-documents/{doc_id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerDocument.objects.filter(id=doc_id).exists())

    def test_multi_file_batch_upload(self):
        self.client.force_authenticate(user=self.owner)
        file1 = SimpleUploadedFile("lease_page1.jpg", b"\xff\xd8\xff dummy image 1", content_type="image/jpeg")
        file2 = SimpleUploadedFile("lease_page2.jpg", b"\xff\xd8\xff dummy image 2", content_type="image/jpeg")
        file3 = SimpleUploadedFile("gst_cert.pdf", b"%PDF-1.4 dummy pdf", content_type="application/pdf")

        payload = {
            "customer": str(self.customer1.id),
            "document_type": CustomerDocument.DocumentType.RENT_AGREEMENT,
            "title": "Shop Lease Agreement",
            "document_number": "AGR-2026-01",
            "expiry_date": "2028-05-01",
            "files": [file1, file2, file3],
        }
        res = self.client.post("/api/v1/customer-documents/batch-upload/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(res.data), 3)
        self.assertEqual(CustomerDocument.objects.filter(customer=self.customer1).count(), 3)
        
        # Verify customer serializer returns documents_count
        cust_res = self.client.get(f"/api/v1/customers/{self.customer1.id}/")
        self.assertEqual(cust_res.status_code, status.HTTP_200_OK)
        self.assertEqual(cust_res.data["documents_count"], 3)

    def test_filtering_and_driver_isolation(self):
        # Create doc on customer 1 (Route North)
        f1 = SimpleUploadedFile("rn.pdf", b"test", content_type="application/pdf")
        CustomerDocument.objects.create(
            customer=self.customer1,
            title="North Doc",
            document_type=CustomerDocument.DocumentType.TRADE_LICENSE,
            file=f1,
            expiry_date="2025-01-01", # expired
            uploaded_by=self.owner,
        )
        # Create doc on customer 2 (Route South)
        f2 = SimpleUploadedFile("rs.pdf", b"test", content_type="application/pdf")
        CustomerDocument.objects.create(
            customer=self.customer2,
            title="South Doc",
            document_type=CustomerDocument.DocumentType.GST_CERTIFICATE,
            file=f2,
            expiry_date="2028-01-01", # active
            uploaded_by=self.owner,
        )

        # Manager can filter by route and customer
        self.client.force_authenticate(user=self.manager)
        res_north = self.client.get(f"/api/v1/customer-documents/?route={self.route1.id}")
        self.assertEqual(res_north.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_north.data if isinstance(res_north.data, list) else res_north.data["results"]), 1)

        res_expired = self.client.get("/api/v1/customer-documents/?is_expired=true")
        self.assertEqual(len(res_expired.data if isinstance(res_expired.data, list) else res_expired.data["results"]), 1)

        # Driver on Route North can ONLY see documents belonging to Route North shops
        self.client.force_authenticate(user=self.driver_user)
        driver_res = self.client.get("/api/v1/customer-documents/")
        self.assertEqual(driver_res.status_code, status.HTTP_200_OK)
        docs = driver_res.data if isinstance(driver_res.data, list) else driver_res.data["results"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["title"], "North Doc")
