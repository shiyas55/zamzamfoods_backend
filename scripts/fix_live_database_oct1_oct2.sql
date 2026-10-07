-- ==============================================================================
-- Zamzam Foods Data Consistency Fix Script
-- Source Backup: zamzam_backup_postgresql_full_20261007_055753.sql
-- Fixes 123 orders where order_date was 2026-10-02 but order_number had ORD-20261003-
-- Safe for execution via Web UI 'Database Restore & Data Import' or psql
-- ==============================================================================

BEGIN;

-- 1. Update order_number in orders_order table

UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0123' WHERE "id" = 'f6c48a49-5050-4e6a-9838-a82a85beb44d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0122' WHERE "id" = 'd61eeb0f-fe44-41ae-9e9c-df866c5d2e80';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0121' WHERE "id" = 'bec78520-87cb-4e78-8675-e1e548007eb1';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0120' WHERE "id" = '48b3391b-192a-465c-8c48-b92ff66c0826';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0119' WHERE "id" = '8429bb7f-b144-45df-95f4-d1de6eb1e34d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0118' WHERE "id" = '2f5eb312-7bb9-45d0-b4fe-61c34dea245e';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0117' WHERE "id" = 'a2bce3a5-e511-483c-b628-4b03ad4b2bf5';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0116' WHERE "id" = 'f0abfef6-86d8-434e-b665-4e7b2bdce685';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0115' WHERE "id" = '34810cae-82fb-48d8-b2c9-a26756588747';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0114' WHERE "id" = 'ac97217c-2d44-49e5-8d08-72e3908e6f00';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0113' WHERE "id" = '711113ba-490d-4ae6-a5ce-b1a977c0283b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0112' WHERE "id" = 'b1d18108-0025-4ff6-a31a-c932cdb349fc';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0111' WHERE "id" = '7b7d4b72-1c10-48d2-b708-25ff39d5f5de';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0110' WHERE "id" = 'b5278943-1024-496a-af72-f11f593cac1a';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0109' WHERE "id" = 'd84e7be9-7d22-41fe-8bf3-f91bac163666';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0108' WHERE "id" = 'ec8e2c3a-dff9-4e42-8df4-fc816d90c81c';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0107' WHERE "id" = '19f5e3eb-5033-41b8-a839-07ec9c9a397b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0106' WHERE "id" = 'f9bc1938-1ff4-4e4a-88f3-9a08ddd82221';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0105' WHERE "id" = '43321701-7cf7-45f3-83a1-d9f09bf2739d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0104' WHERE "id" = '53f601ce-3848-4148-8b85-b6150354c09b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0103' WHERE "id" = '867fab76-d656-4a6d-8508-ea5c9da1bd56';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0102' WHERE "id" = 'e53dc3fa-4a78-48d6-baa1-46f662125201';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0101' WHERE "id" = '2a4e3720-f97e-418c-b970-9fb523c95486';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0100' WHERE "id" = '6e0a8ff0-cfde-4c98-a9cd-b591fa2ce3fd';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0099' WHERE "id" = '711fb594-b9af-4070-8f3b-75fb64e3a276';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0098' WHERE "id" = '9f15aa84-d883-4405-b2fb-3e8bb9c4267a';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0097' WHERE "id" = '43eb2ce1-3931-4c73-a451-6fee80fdfb76';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0096' WHERE "id" = '73d0a1ad-4d0c-4ad2-85a8-d368cffe4ca4';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0095' WHERE "id" = 'a094ff37-3cad-42a6-ba5c-32f0e1d31857';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0094' WHERE "id" = '8a305ac8-16cb-4674-bc0d-2d0789cc5733';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0093' WHERE "id" = 'ec9efb8d-82c1-4633-a67d-b442b978f891';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0092' WHERE "id" = 'b8c5c4c8-e1b0-479c-93f6-59a3e2eeadad';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0091' WHERE "id" = '72330682-d2d3-4a9b-8fef-dfcdb33f0cc8';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0090' WHERE "id" = 'dcca0b41-17ea-4a29-8413-8954be25f2a8';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0089' WHERE "id" = '525d2409-14a6-4c35-91c0-ca00421f5ee1';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0088' WHERE "id" = '3ee1c481-6315-434b-94b5-459c378ff3cc';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0087' WHERE "id" = '2d733e80-76d8-42b6-8494-0192af447819';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0086' WHERE "id" = '1241799a-2943-4d22-b749-3071c7e9f24f';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0085' WHERE "id" = '164cbd66-fcf0-4947-8a80-2e39a0f412cd';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0084' WHERE "id" = '1662e1aa-e5fd-4742-9629-32c99a5c580e';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0083' WHERE "id" = '3b4e521b-16ba-477d-b958-71df7578c1de';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0082' WHERE "id" = 'fbb48066-c280-48c5-9188-bf37b5d240af';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0081' WHERE "id" = '6d117f42-75a6-4a67-8b7d-c26cee6a0d9c';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0080' WHERE "id" = 'e787c812-8e1c-4308-978e-295a944ec76d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0079' WHERE "id" = '2385eac6-a988-4d2e-8cb6-f4ce0c9421d1';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0078' WHERE "id" = 'a16d336e-04f3-49c0-b6c6-3fed2cfb034b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0077' WHERE "id" = '9285f07a-4a14-4f98-9180-c379efcc4b99';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0076' WHERE "id" = '0e86e9ea-b7f9-4a1b-b2c0-706fab66a813';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0075' WHERE "id" = '6f1ab5b9-3a64-4d68-b134-220ee525099d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0074' WHERE "id" = 'f766a694-03c6-4b08-b40a-11355c4b1651';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0073' WHERE "id" = '6778d0ed-1256-476b-8ca8-aabb6fa4e262';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0072' WHERE "id" = '209c55d0-0718-4add-854b-3548b51f1382';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0071' WHERE "id" = '895b582a-6547-4621-98ce-0db920298dbf';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0070' WHERE "id" = '01f9dc58-2df3-4804-a5b0-8ea83428001b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0069' WHERE "id" = '9f60c0ad-daaa-410c-b330-21414e357022';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0068' WHERE "id" = '503f4bf6-04c2-480b-8819-c86847b36cb1';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0067' WHERE "id" = '019078a2-7cfb-4787-bf81-c32dae7160d9';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0066' WHERE "id" = '1db79235-9ce7-4ab2-89f3-03eb072ee8c4';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0065' WHERE "id" = 'bacaf10c-e06f-4570-ab33-0ec1c2c3744d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0064' WHERE "id" = 'b4055d8c-faa7-4ef6-8fe7-50894910cf4b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0063' WHERE "id" = '8937525f-fed7-45ff-ab05-976d88a7bf2b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0062' WHERE "id" = 'e00ec815-2c3a-49a1-ade8-c95f956ecdf2';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0061' WHERE "id" = 'ea96e110-8a47-409f-aee1-a154761644e0';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0060' WHERE "id" = 'fd921924-a47c-4167-9a0e-6c21bcc02087';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0059' WHERE "id" = '680ee3b2-c042-4655-a541-bd7314d0e831';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0058' WHERE "id" = 'fe4da496-6877-4689-b8ea-d5ea514cec22';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0057' WHERE "id" = 'b85eb1a0-7088-4584-b583-3df754dd9d87';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0056' WHERE "id" = '0974548c-8713-4c4a-a569-21231e323110';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0055' WHERE "id" = '2f079507-20f7-4a73-8ff4-ab2f891a312b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0054' WHERE "id" = '87f18a6b-81f2-4391-98aa-96ea3492d867';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0053' WHERE "id" = 'f31639e7-6482-4f26-ae1e-9ea7c66dabd9';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0052' WHERE "id" = '5c24cef1-efa4-4378-adc9-d498e53bd472';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0051' WHERE "id" = 'ebd5db11-0bf3-4887-ae3b-b22ebda1783d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0050' WHERE "id" = '39e48052-0ab6-44a0-90db-6dd23fe895a2';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0049' WHERE "id" = '989b5862-e821-4110-af21-c58e98b03337';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0048' WHERE "id" = 'c7fe2e26-60ce-47ae-a989-e1124d7114e0';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0047' WHERE "id" = '943907dc-7d43-4174-9deb-3eb86536e2b2';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0046' WHERE "id" = '9319a769-1e80-4302-8d16-21d4b19305fc';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0045' WHERE "id" = 'd755d41c-d64c-4cf6-afa0-f7983c7d3dd0';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0044' WHERE "id" = 'ec6dee09-565c-4a05-a284-9bcee1706e9a';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0043' WHERE "id" = 'd0db478d-41ce-4b80-8c24-1f9ed5b7f8cd';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0042' WHERE "id" = '2def027f-c43e-40df-a3c0-49edd946c2cb';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0041' WHERE "id" = '5c5907fb-2355-4cee-997e-c7c476527caf';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0040' WHERE "id" = '3fc2725d-cb2b-4baa-8780-17f6191f93c3';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0039' WHERE "id" = 'c05893f9-bfef-4dd6-9cb5-06956a7566ab';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0038' WHERE "id" = 'f617a098-7adf-4cb3-8af5-1909d85e06c6';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0037' WHERE "id" = 'e02a9c98-a8d9-45a0-a2a1-246ba29bc218';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0036' WHERE "id" = '687658cc-07fd-4c63-a71c-4b74d6e2ebe7';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0035' WHERE "id" = '77e1f8e4-e9d2-4b8d-a272-31034c8f2755';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0034' WHERE "id" = 'da677e59-0e65-4d46-aae3-ea24ff12988f';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0033' WHERE "id" = '591778bb-305e-430c-a1eb-b7e32f78cc36';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0032' WHERE "id" = '30479f40-fea9-4044-ad1f-7b3e8a9602ec';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0031' WHERE "id" = 'ac11012f-64d0-497d-bb6b-a322bb8451fa';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0030' WHERE "id" = '8b357fbd-9375-4654-ace2-2692015190c1';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0029' WHERE "id" = '7d4ac75c-2991-49a0-9a38-ec2ac7d7bbb9';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0028' WHERE "id" = 'c5824ee7-0fd7-4b07-b164-ad854bd5b439';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0027' WHERE "id" = '09e22414-af62-4f4a-8349-a537042754c4';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0026' WHERE "id" = '707b2581-0bba-4330-8305-96e7fbcde0dd';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0025' WHERE "id" = '1a0b7ce9-111b-416a-8ab0-f9e95b76f8b1';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0024' WHERE "id" = '9191fc1e-b2f2-4b35-885b-f1e2fbb8725b';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0023' WHERE "id" = '22ffc937-1b26-4035-b69a-a3598b35bcfa';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0022' WHERE "id" = 'f018475a-7c73-42fc-913b-537a02cb9b8e';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0021' WHERE "id" = 'a07c3735-d3fd-40cd-b8b6-c774b1c2c38d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0020' WHERE "id" = 'b4cf2c5f-3895-494d-b3a9-e0e649162510';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0019' WHERE "id" = '6bd7c764-2c89-48cb-96f8-39ee90493e64';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0018' WHERE "id" = '1e96177c-91c0-4532-8f69-ba5bf1904a97';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0017' WHERE "id" = '5be62f77-82b4-47bd-8c38-c162aa08d1eb';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0016' WHERE "id" = '1975cd4f-d62b-401f-9839-c0b39f8e5374';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0015' WHERE "id" = '8d52f6f0-d50a-4dbe-a296-e3462c16fc16';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0014' WHERE "id" = 'bfae2d82-a1c8-47d2-90ca-e7d379127074';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0013' WHERE "id" = '03cc9ffa-0e91-4c0e-95ec-535a62ace3fc';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0012' WHERE "id" = 'c518468b-5bc3-41d4-9b26-e53ac824b85d';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0011' WHERE "id" = '0dd1a128-6e62-4c9a-a906-8ddd76aef070';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0010' WHERE "id" = 'e5c1f745-3e7b-4b32-b730-7092382da356';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0009' WHERE "id" = '2052a12f-2590-4a4d-a14a-b75b0e553096';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0008' WHERE "id" = '87262b76-8b35-4124-b103-6b2d676f10c7';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0007' WHERE "id" = '5d74d0d8-1b72-4b71-85f5-a1e172eb2fe3';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0006' WHERE "id" = '3b192460-3b4e-4d3b-80c7-b6b3955fe9fa';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0005' WHERE "id" = 'afeddce8-ade6-4508-bccb-8890cb830742';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0004' WHERE "id" = '290ce1b1-fd4e-4d02-a7e4-149e3335c140';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0003' WHERE "id" = '5c82debb-661d-4648-836d-c91fe59147fc';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0002' WHERE "id" = 'a4f1d7d1-7dc0-47de-9f3b-327eb9ed17ca';
UPDATE "orders_order" SET "order_number" = 'ORD-20261002-0001' WHERE "id" = '647c5e0f-9c62-4606-bc48-9215f8f4d476';

-- 2. Update credit transaction notes referencing old order numbers
UPDATE "credits_credittransaction"
SET "notes" = REPLACE("notes", 'ORD-20261003-', 'ORD-20261002-')
WHERE "notes" LIKE '%#ORD-20261003-%';

-- 3. Delete ghost order-edit adjustments (reference_order_id IS NOT NULL)
DELETE FROM "credits_credittransaction"
WHERE "transaction_type" = 'ADJUSTMENT'
  AND "reference_order_id" IS NOT NULL;

-- 4. Delete legacy Fast Wholesale Entry test adjustments
DELETE FROM "credits_credittransaction"
WHERE "transaction_type" = 'ADJUSTMENT'
  AND "notes" LIKE '%Fast Wholesale Entry%';

-- 5. Explicitly reconcile FAMOUS KATTANGAL (Customer ID: 2c4e3160-a549-42e5-81e7-007f6759d558)
-- Oct 1 Order (#ORD-20261001-0021): Bill ₹360.00, Paid ₹500.00 -> Ending Oct 1 Balance: ₹4,870.00
-- Oct 2 Order (#ORD-20261002-0022): 100 Kubbus @ ₹4.50 (₹450.00) + 10 Romali @ ₹9.00 (₹90.00) = Bill ₹540.00, Paid ₹0.00 -> Ending Oct 2 Balance: ₹5,410.00

-- Ensure Oct 2 Order total is ₹540.00 and order_number is ORD-20261002-0022
UPDATE "orders_order"
SET "order_number" = 'ORD-20261002-0022',
    "total_amount" = 540.00
WHERE "id" = 'f018475a-7c73-42fc-913b-537a02cb9b8e';

-- Update order items for Oct 2
UPDATE "orders_orderitem"
SET "unit_price" = 4.50,
    "subtotal" = 450.00
WHERE "order_id" = 'f018475a-7c73-42fc-913b-537a02cb9b8e'
  AND "product_id" = 'aecd1280-ef53-4445-a8a6-7b0256046bd6';

UPDATE "orders_orderitem"
SET "unit_price" = 9.00,
    "subtotal" = 90.00
WHERE "order_id" = 'f018475a-7c73-42fc-913b-537a02cb9b8e'
  AND "product_id" = '8f196b7d-42c2-4af8-90d7-b20fc63c7914';

-- Reconcile CREDIT_SALE for Oct 2 (Balance before = Oct 1 closing ₹4,870.00, Amount = ₹540.00, Balance after = ₹5,410.00)
UPDATE "credits_credittransaction"
SET "amount" = 540.00,
    "balance_after" = 5410.00,
    "notes" = 'Credit sale for order #ORD-20261002-0022'
WHERE "reference_order_id" = 'f018475a-7c73-42fc-913b-537a02cb9b8e'
  AND "transaction_type" = 'CREDIT_SALE';

-- Reconcile FAMOUS KATTANGAL current balance: ₹4,870.00 + ₹540.00 = ₹5,410.00
UPDATE "customers_customer"
SET "current_balance" = 5410.00
WHERE "id" = '2c4e3160-a549-42e5-81e7-007f6759d558';

COMMIT;
