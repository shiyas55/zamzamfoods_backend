-- ==============================================================================
-- Zamzam Foods — Comprehensive 128-Shop Ledger Reconciliation (Oct 1 to Oct 7)
-- Automatically aligns all customer opening balances, order numbers, and ledger entries
-- Safe for execution via Web UI 'Database Restore & Data Import' or Supabase SQL Editor
-- ==============================================================================
BEGIN;

-- 1. Correct all 123 misaligned Oct 2 order numbers (ORD-20261003- -> ORD-20261002-)
-- ==============================================================================
-- Zamzam Foods Data Consistency Fix Script
-- Source Backup: zamzam_backup_postgresql_full_20261007_055753.sql
-- Fixes 123 orders where order_date was 2026-10-02 but order_number had ORD-20261003-
-- Safe for execution via Web UI 'Database Restore & Data Import' or psql
-- ==============================================================================



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

-- 2. Delete all 185 bogus Fast Wholesale Entry adjustment entries
DELETE FROM "credits_credittransaction"
WHERE "transaction_type" = 'ADJUSTMENT'
  AND "notes" LIKE '%Fast Wholesale Entry%';

-- 3. Delete all 9 ghost order-edit adjustment entries
DELETE FROM "credits_credittransaction"
WHERE "transaction_type" = 'ADJUSTMENT'
  AND "reference_order_id" IS NOT NULL;

-- 4. Update CREDIT_SALE transactions and current_balance for all shops
-- 6o clock karanthur: Oct 2 Credit Sale (amount: 540.00, balance_after: 3805.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 3805.00 WHERE "reference_order_id" = '8a305ac8-16cb-4674-bc0d-2d0789cc5733' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 3805.00 WHERE "id" = 'dc0833e8-5314-4c90-a64d-5fac03113c3b';
-- 6th clock koduvally: Oct 2 Credit Sale (amount: 590.00, balance_after: 1290.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1290.00 WHERE "reference_order_id" = '2052a12f-2590-4a4d-a14a-b75b0e553096' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1290.00 WHERE "id" = 'a49ed078-9384-41e8-9e48-d2d894718dd8';
-- adam golden chick: Oct 2 Credit Sale (amount: 580.00, balance_after: 580.00)
UPDATE "credits_credittransaction" SET "amount" = 580.00, "balance_after" = 580.00 WHERE "reference_order_id" = '2f079507-20f7-4a73-8ff4-ab2f891a312b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 580.00 WHERE "id" = '651e2320-d0f3-4474-9236-b9bd8d297f10';
-- ajwa karanthur: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'a094ff37-3cad-42a6-ba5c-32f0e1d31857' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '94bd972d-9d43-4979-99b5-8fdfe2b8ff49';
-- al aroosh mandi: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '73d0a1ad-4d0c-4ad2-85a8-d368cffe4ca4' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'fa5f8714-b3d3-4754-b791-9ae7a9d0a1af';
-- alankar nadakkav: Oct 2 Credit Sale (amount: 250.00, balance_after: 500.00)
UPDATE "credits_credittransaction" SET "amount" = 250.00, "balance_after" = 500.00 WHERE "reference_order_id" = '647c5e0f-9c62-4606-bc48-9215f8f4d476' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 500.00 WHERE "id" = '42e1bf84-de07-41ac-abf3-2bb4f74e7e01';
-- alfain koduvally: Oct 2 Credit Sale (amount: 515.00, balance_after: 1365.00)
UPDATE "credits_credittransaction" SET "amount" = 515.00, "balance_after" = 1365.00 WHERE "reference_order_id" = 'e5c1f745-3e7b-4b32-b730-7092382da356' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1365.00 WHERE "id" = '97b29e8e-b39a-4b8f-ba8d-df17f096408c';
-- alka bekery: Oct 2 Credit Sale (amount: 535.00, balance_after: 1477.00)
UPDATE "credits_credittransaction" SET "amount" = 535.00, "balance_after" = 1477.00 WHERE "reference_order_id" = '0dd1a128-6e62-4c9a-a906-8ddd76aef070' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1477.00 WHERE "id" = 'e48ccb86-5329-408d-8b48-5d45399b47ca';
-- alshai shawarma shop: Oct 2 Credit Sale (amount: 590.00, balance_after: 1020.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1020.00 WHERE "reference_order_id" = '0974548c-8713-4c4a-a569-21231e323110' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1020.00 WHERE "id" = 'c29e9f36-b976-43a2-b238-4a21a9e48587';
-- anshif kubbooos: Oct 2 Credit Sale (amount: 480.00, balance_after: 600.00)
UPDATE "credits_credittransaction" SET "amount" = 480.00, "balance_after" = 600.00 WHERE "reference_order_id" = 'f0abfef6-86d8-434e-b665-4e7b2bdce685' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = -280.00 WHERE "id" = '6669f392-6a1b-4379-b65b-8e33909fc152';
-- AR bekery: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'c518468b-5bc3-41d4-9b26-e53ac824b85d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '50eedcfe-7830-42cf-b7e8-baff55c7a444';
-- area 51 muhsin: Oct 2 Credit Sale (amount: 590.00, balance_after: 7880.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 7880.00 WHERE "reference_order_id" = 'b85eb1a0-7088-4584-b583-3df754dd9d87' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 7880.00 WHERE "id" = '40f3d622-ef3b-4763-b87d-7356be83219d';
-- aroosh balusseri: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '03cc9ffa-0e91-4c0e-95ec-535a62ace3fc' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '23261a04-aafb-4226-a083-8543df44b4a2';
-- beach mansoor: Oct 2 Credit Sale (amount: 590.00, balance_after: 3155.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 3155.00 WHERE "reference_order_id" = 'a4f1d7d1-7dc0-47de-9f3b-327eb9ed17ca' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 3155.00 WHERE "id" = '590d7a56-16db-4100-a363-debb5a096bc2';
-- beach rumali: Oct 2 Credit Sale (amount: 590.00, balance_after: 2170.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 2170.00 WHERE "reference_order_id" = '5c82debb-661d-4648-836d-c91fe59147fc' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2170.00 WHERE "id" = 'cc7dd423-0623-4058-964c-2e935186caf6';
-- berrys koduvally: Oct 2 Credit Sale (amount: 480.00, balance_after: 41080.00)
UPDATE "credits_credittransaction" SET "amount" = 480.00, "balance_after" = 41080.00 WHERE "reference_order_id" = 'bfae2d82-a1c8-47d2-90ca-e7d379127074' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 41080.00 WHERE "id" = '3abb6682-74e6-4cb9-bcb6-834ebcebd026';
-- berrys pottammal kozhikode: Oct 2 Credit Sale (amount: 470.00, balance_after: 99370.00)
UPDATE "credits_credittransaction" SET "amount" = 470.00, "balance_after" = 99370.00 WHERE "reference_order_id" = '43eb2ce1-3931-4c73-a451-6fee80fdfb76' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 99370.00 WHERE "id" = 'bef9c287-0151-4a7c-802c-ea0c1668d056';
-- big verity hotel: Oct 2 Credit Sale (amount: 540.00, balance_after: 545.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 545.00 WHERE "reference_order_id" = 'fe4da496-6877-4689-b8ea-d5ea514cec22' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 545.00 WHERE "id" = '90b663d7-fffa-478e-bb4f-7dea1dc18801';
-- bismi: Oct 2 Credit Sale (amount: 5040.00, balance_after: 10080.00)
UPDATE "credits_credittransaction" SET "amount" = 5040.00, "balance_after" = 10080.00 WHERE "reference_order_id" = '290ce1b1-fd4e-4d02-a7e4-149e3335c140' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 10080.00 WHERE "id" = '93351bf1-1a2d-40d8-b34f-6adfd4af79dc';
-- broast: Oct 2 Credit Sale (amount: 515.00, balance_after: 760.00)
UPDATE "credits_credittransaction" SET "amount" = 515.00, "balance_after" = 760.00 WHERE "reference_order_id" = '8d52f6f0-d50a-4dbe-a296-e3462c16fc16' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 760.00 WHERE "id" = 'abb3e630-c065-440a-8701-0d4f70b533db';
-- brothers mukkam: Oct 2 Credit Sale (amount: 590.00, balance_after: 600.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 600.00 WHERE "reference_order_id" = '1975cd4f-d62b-401f-9839-c0b39f8e5374' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 600.00 WHERE "id" = '77aaf71d-58b6-478c-83b0-185d8729f1a1';
-- bun basket: Oct 2 Credit Sale (amount: 490.00, balance_after: 2930.00)
UPDATE "credits_credittransaction" SET "amount" = 490.00, "balance_after" = 2930.00 WHERE "reference_order_id" = 'a2bce3a5-e511-483c-b628-4b03ad4b2bf5' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2930.00 WHERE "id" = '20dab026-f4da-4c7c-907b-ac77521bf390';
-- burnight medical college: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '680ee3b2-c042-4655-a541-bd7314d0e831' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'acffbfc0-e27a-47a2-be42-44977d4525f5';
-- cafe 19: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'fd921924-a47c-4167-9a0e-6c21bcc02087' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'c2aa4bea-5cc5-4884-9901-d1cc84ee40e8';
-- chai bea: Oct 2 Credit Sale (amount: 590.00, balance_after: 3410.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 3410.00 WHERE "reference_order_id" = 'ea96e110-8a47-409f-aee1-a154761644e0' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 3410.00 WHERE "id" = '75df1ec9-30cd-48f8-ad50-0494d387d98a';
-- chai kattangal: Oct 2 Credit Sale (amount: 590.00, balance_after: 860.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 860.00 WHERE "reference_order_id" = '1e96177c-91c0-4532-8f69-ba5bf1904a97' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 860.00 WHERE "id" = '0889dc8d-eb0f-4376-9685-a47c0ab331cc';
-- chai.in: Oct 2 Credit Sale (amount: 590.00, balance_after: 1340.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1340.00 WHERE "reference_order_id" = '5be62f77-82b4-47bd-8c38-c162aa08d1eb' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1340.00 WHERE "id" = '6d0fab5b-f5a1-4d69-91b0-2b7ad7274f43';
-- chakkara panthal: Oct 2 Credit Sale (amount: 590.00, balance_after: 790.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 790.00 WHERE "reference_order_id" = 'e00ec815-2c3a-49a1-ade8-c95f956ecdf2' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 790.00 WHERE "id" = 'd52eaa2a-9399-4fea-accd-63a036ecf0ff';
-- chappathi kakka: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = '2f5eb312-7bb9-45d0-b4fe-61c34dea245e' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = 'd6b1d0fd-6527-4706-870c-2f25b78f1bdc';
-- chick co: Oct 2 Credit Sale (amount: 530.00, balance_after: 3365.00)
UPDATE "credits_credittransaction" SET "amount" = 530.00, "balance_after" = 3365.00 WHERE "reference_order_id" = '8937525f-fed7-45ff-ab05-976d88a7bf2b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 3365.00 WHERE "id" = 'c4892f20-ee28-4dcf-98d5-f635c76e77c8';
-- chopstick palazhi: Oct 2 Credit Sale (amount: 590.00, balance_after: 2790.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 2790.00 WHERE "reference_order_id" = 'b4055d8c-faa7-4ef6-8fe7-50894910cf4b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2790.00 WHERE "id" = '35d7dcde-4a67-4fd8-828a-f7620e79d3cf';
-- cm momos: Oct 2 Credit Sale (amount: 590.00, balance_after: 710.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 710.00 WHERE "reference_order_id" = 'bacaf10c-e06f-4570-ab33-0ec1c2c3744d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 710.00 WHERE "id" = '94dc3226-bb3a-4e28-94ae-953f79136112';
-- corner narikkuni stand: Oct 2 Credit Sale (amount: 535.00, balance_after: 455.00)
UPDATE "credits_credittransaction" SET "amount" = 535.00, "balance_after" = 455.00 WHERE "reference_order_id" = '6bd7c764-2c89-48cb-96f8-39ee90493e64' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 455.00 WHERE "id" = '631a1b07-6104-488e-9ec1-dae8fa71b1ff';
-- corner pullaloor: Oct 2 Credit Sale (amount: 590.00, balance_after: 1550.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1550.00 WHERE "reference_order_id" = 'b4cf2c5f-3895-494d-b3a9-e0e649162510' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1550.00 WHERE "id" = 'f51bb7bf-d197-491d-a7af-773f9bfd4661';
-- cross road nadakkav: Oct 2 Credit Sale (amount: 810.00, balance_after: 4745.00)
UPDATE "credits_credittransaction" SET "amount" = 810.00, "balance_after" = 4745.00 WHERE "reference_order_id" = 'afeddce8-ade6-4508-bccb-8890cb830742' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 4745.00 WHERE "id" = '23ab0b69-fdb1-49da-803b-0f38f3079fc7';
-- crunch bun puthiyangadi: Oct 2 Credit Sale (amount: 590.00, balance_after: 1880.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1880.00 WHERE "reference_order_id" = '3b192460-3b4e-4d3b-80c7-b6b3955fe9fa' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1880.00 WHERE "id" = '383aeae6-e08a-4686-bb5e-664f11fdcb83';
-- dahban mandi: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '1db79235-9ce7-4ab2-89f3-03eb072ee8c4' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '496dd817-f7dd-4793-b46c-c4181cf61b70';
-- dana arakkinar: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '019078a2-7cfb-4787-bf81-c32dae7160d9' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'd8ce3cad-7cb2-49d3-96d5-3a25aa064c10';
-- dana areekad: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '503f4bf6-04c2-480b-8819-c86847b36cb1' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '1a182ba5-f01f-412f-aec9-3db0bd775c67';
-- donor mukkam: Oct 2 Credit Sale (amount: 540.00, balance_after: 1035.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 1035.00 WHERE "reference_order_id" = 'a07c3735-d3fd-40cd-b8b6-c774b1c2c38d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1035.00 WHERE "id" = '75352512-01fb-4a40-8068-aa762b289e85';
-- easy foods kkr: Oct 2 Credit Sale (amount: 90.00, balance_after: 340.00)
UPDATE "credits_credittransaction" SET "amount" = 90.00, "balance_after" = 340.00 WHERE "reference_order_id" = '8429bb7f-b144-45df-95f4-d1de6eb1e34d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 959.00 WHERE "id" = 'c02ad963-8cf1-4307-8bf5-41fa028c9517';
-- FAMOUS KATTANGAL: Oct 2 Credit Sale (amount: 540.00, balance_after: 5410.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 5410.00 WHERE "reference_order_id" = 'f018475a-7c73-42fc-913b-537a02cb9b8e' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 5410.00 WHERE "id" = '2c4e3160-a549-42e5-81e7-007f6759d558';
-- famous mundikkal thazham: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = '9f15aa84-d883-4405-b2fb-3e8bb9c4267a' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = 'd34d7a6f-d41c-4941-ba02-a6daf4bdf248';
-- famous padanilam: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = '711fb594-b9af-4070-8f3b-75fb64e3a276' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = 'bda56798-ea35-4dc8-832e-d52ac1b2f05c';
-- felafil karuvanpoyil: Oct 2 Credit Sale (amount: 590.00, balance_after: 690.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 690.00 WHERE "reference_order_id" = '22ffc937-1b26-4035-b69a-a3598b35bcfa' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 690.00 WHERE "id" = '8e9b437e-683a-4316-82fc-506200d7234d';
-- food keys koduvally: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '9191fc1e-b2f2-4b35-885b-f1e2fbb8725b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '56332230-64b5-42c5-aeae-614cfc00f228';
-- food qissa: Oct 2 Credit Sale (amount: 590.00, balance_after: 640.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 640.00 WHERE "reference_order_id" = '9f60c0ad-daaa-410c-b330-21414e357022' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 640.00 WHERE "id" = '536feb85-6ad8-4cb3-a1af-32e81f0ad7c5';
-- fresca: Oct 2 Credit Sale (amount: 590.00, balance_after: 600.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 600.00 WHERE "reference_order_id" = '1a0b7ce9-111b-416a-8ab0-f9e95b76f8b1' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1790.00 WHERE "id" = '1d049c43-2af2-4a19-8c52-7fa0308ca8ea';
-- friends bekery: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '6e0a8ff0-cfde-4c98-a9cd-b591fa2ce3fd' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'b78b29e6-c443-4142-9735-0feedfea0c89';
-- G dine ulliyeri: Oct 2 Credit Sale (amount: 480.00, balance_after: 1480.00)
UPDATE "credits_credittransaction" SET "amount" = 480.00, "balance_after" = 1480.00 WHERE "reference_order_id" = '09e22414-af62-4f4a-8349-a537042754c4' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1480.00 WHERE "id" = '23a2d638-5e81-4a64-87c8-483b22f3134f';
-- galaxy: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '707b2581-0bba-4330-8305-96e7fbcde0dd' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '5e6a19ca-5008-47c2-8865-396e175b2e92';
-- grill cafe: Oct 2 Credit Sale (amount: 540.00, balance_after: 500.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 500.00 WHERE "reference_order_id" = '01f9dc58-2df3-4804-a5b0-8ea83428001b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 500.00 WHERE "id" = '0b38a4d5-bc22-413f-8231-7f73a351f15f';
-- grill chouk treat: Oct 2 Credit Sale (amount: 540.00, balance_after: 6140.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 6140.00 WHERE "reference_order_id" = '895b582a-6547-4621-98ce-0db920298dbf' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 6140.00 WHERE "id" = '39eb1902-7d9f-4074-aa46-334c51db9a94';
-- happy kiyakkoth koduvally: Oct 2 Credit Sale (amount: 490.00, balance_after: 490.00)
UPDATE "credits_credittransaction" SET "amount" = 490.00, "balance_after" = 490.00 WHERE "reference_order_id" = 'c5824ee7-0fd7-4b07-b164-ad854bd5b439' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 490.00 WHERE "id" = 'd4a18ab0-6880-4ce8-b6fc-6af1575a640a';
-- happy koduvally: Oct 2 Credit Sale (amount: 490.00, balance_after: 670.00)
UPDATE "credits_credittransaction" SET "amount" = 490.00, "balance_after" = 670.00 WHERE "reference_order_id" = '7d4ac75c-2991-49a0-9a38-ec2ac7d7bbb9' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 670.00 WHERE "id" = '1cf8f2a4-ac4e-48f2-99f0-74d9e1f795c5';
-- happy narikkuni: Oct 2 Credit Sale (amount: 490.00, balance_after: 1030.00)
UPDATE "credits_credittransaction" SET "amount" = 490.00, "balance_after" = 1030.00 WHERE "reference_order_id" = '8b357fbd-9375-4654-ace2-2692015190c1' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1030.00 WHERE "id" = '63ccb492-a4f9-44b1-bd82-ea92d09139b7';
-- jisha bekery: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '2a4e3720-f97e-418c-b970-9fb523c95486' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '54fc57f3-9778-4594-9224-c5ebef1d3269';
-- jucify kkr: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'e53dc3fa-4a78-48d6-baa1-46f662125201' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'fbd00739-694b-49ea-83db-e512afd52a2b';
-- kakkodi bekery: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = 'ac11012f-64d0-497d-bb6b-a322bb8451fa' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = '2efa7fce-4b48-41e3-824c-135d5b6e91b3';
-- kannadikkal 2: Oct 2 Credit Sale (amount: 640.00, balance_after: 1315.00)
UPDATE "credits_credittransaction" SET "amount" = 640.00, "balance_after" = 1315.00 WHERE "reference_order_id" = '209c55d0-0718-4add-854b-3548b51f1382' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1315.00 WHERE "id" = '0ab72049-0b24-414e-b620-ccccd937ccc3';
-- karthika bakes kannadkkal 1: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '6778d0ed-1256-476b-8ca8-aabb6fa4e262' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '5305c2a9-b5e0-44cd-b2dd-df56fc8f7725';
-- khaleej restaurent: Oct 2 Credit Sale (amount: 590.00, balance_after: 970.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 970.00 WHERE "reference_order_id" = 'f766a694-03c6-4b08-b40a-11355c4b1651' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 970.00 WHERE "id" = '1a233bc7-e647-47e0-862d-a509ccf29bee';
-- king felafil koduvally: Oct 2 Credit Sale (amount: 490.00, balance_after: 2090.00)
UPDATE "credits_credittransaction" SET "amount" = 490.00, "balance_after" = 2090.00 WHERE "reference_order_id" = '30479f40-fea9-4044-ad1f-7b3e8a9602ec' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2090.00 WHERE "id" = 'a303dabb-4ea7-4efd-a15b-eb5272f4f3fd';
-- le shawaya: Oct 2 Credit Sale (amount: 590.00, balance_after: 970.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 970.00 WHERE "reference_order_id" = '867fab76-d656-4a6d-8508-ea5c9da1bd56' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 970.00 WHERE "id" = '814ae516-6610-454e-84f0-31002126828c';
-- live alfahm mangav: Oct 2 Credit Sale (amount: 540.00, balance_after: 2745.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 2745.00 WHERE "reference_order_id" = '6f1ab5b9-3a64-4d68-b134-220ee525099d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2745.00 WHERE "id" = 'bcb83141-1c79-4ca2-9176-3e4c989cccee';
-- malabar bakes: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '5d74d0d8-1b72-4b71-85f5-a1e172eb2fe3' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '06461738-e4f1-45ea-a9e6-6076a53f79d0';
-- mandi pokkunnu: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '0e86e9ea-b7f9-4a1b-b2c0-706fab66a813' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '39506eaf-b662-4bdf-8ff6-e9b373c58894';
-- mandi shop: Oct 2 Credit Sale (amount: 590.00, balance_after: 640.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 640.00 WHERE "reference_order_id" = '591778bb-305e-430c-a1eb-b7e32f78cc36' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2471.00 WHERE "id" = 'c1cf92ef-7902-40f5-9c6e-be5ae7df1322';
UPDATE "customers_customer" SET "current_balance" = 0.00 WHERE "id" = '88a2c57e-5e0b-403f-9796-e6b281b30f8c';
UPDATE "customers_customer" SET "current_balance" = 0.00 WHERE "id" = '037aef4b-6d12-4ad3-ba59-478a4104fea7';
-- maruthadans bekery: Oct 2 Credit Sale (amount: 700.00, balance_after: 1985.00)
UPDATE "credits_credittransaction" SET "amount" = 700.00, "balance_after" = 1985.00 WHERE "reference_order_id" = 'da677e59-0e65-4d46-aae3-ea24ff12988f' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1985.00 WHERE "id" = 'a5ad7e7c-975b-4e22-8c46-c851cba5e3fc';
-- mims cool: Oct 2 Credit Sale (amount: 540.00, balance_after: 4070.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 4070.00 WHERE "reference_order_id" = '9285f07a-4a14-4f98-9180-c379efcc4b99' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 4070.00 WHERE "id" = '74f6ce17-be92-4f40-9ddc-0445eb804beb';
-- miya miya: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '77e1f8e4-e9d2-4b8d-a272-31034c8f2755' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'd46085e1-ef78-4a53-99b6-0a0f9acce034';
-- morris kovoor: Oct 2 Credit Sale (amount: 590.00, balance_after: 700.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 700.00 WHERE "reference_order_id" = 'a16d336e-04f3-49c0-b6c6-3fed2cfb034b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 700.00 WHERE "id" = 'ea6a58ed-76ad-4e1c-9310-3a9c9271ae35';
-- MR  supermarket muriyanal: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '53f601ce-3848-4148-8b85-b6150354c09b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '680122de-47da-424e-851d-3f955b56a58c';
-- MR hypermarket: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '2385eac6-a988-4d2e-8cb6-f4ce0c9421d1' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '47c25c46-6aee-49a3-a31c-5938e3f255cc';
-- mr hypermartket: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'e787c812-8e1c-4308-978e-295a944ec76d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '802f067e-e6ee-4c09-8ab2-b8f13cc17229';
-- mr mandi velliparamba: Oct 2 Credit Sale (amount: 590.00, balance_after: 2220.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 2220.00 WHERE "reference_order_id" = '6d117f42-75a6-4a67-8b7d-c26cee6a0d9c' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2220.00 WHERE "id" = '0d413073-7e88-41a0-b409-30ca27db474a';
-- msr corner: Oct 2 Credit Sale (amount: 590.00, balance_after: 680.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 680.00 WHERE "reference_order_id" = '687658cc-07fd-4c63-a71c-4b74d6e2ebe7' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 680.00 WHERE "id" = '57bd5f24-146e-4a51-a989-d71ad8e98897';
-- mukkam rumali: Oct 2 Credit Sale (amount: 590.00, balance_after: 1310.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1310.00 WHERE "reference_order_id" = 'e02a9c98-a8d9-45a0-a2a1-246ba29bc218' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1310.00 WHERE "id" = '0d72471e-d721-4102-a751-33b0af323102';
-- mundikkal tea shop: Oct 2 Credit Sale (amount: 590.00, balance_after: 640.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 640.00 WHERE "reference_order_id" = '43321701-7cf7-45f3-83a1-d9f09bf2739d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 640.00 WHERE "id" = '9e261061-bdc2-4d8c-bc20-179a943b57ab';
-- nanmanda teashop: Oct 2 Credit Sale (amount: 590.00, balance_after: 730.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 730.00 WHERE "reference_order_id" = 'f617a098-7adf-4cb3-8af5-1909d85e06c6' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 730.00 WHERE "id" = 'b771c38f-4813-4f55-89e7-9fa1dc855482';
-- ngo crunchy tales: Oct 2 Credit Sale (amount: 590.00, balance_after: 1420.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1420.00 WHERE "reference_order_id" = 'fbb48066-c280-48c5-9188-bf37b5d240af' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1420.00 WHERE "id" = '0a680a34-0db8-4491-9c3f-871b8d9bb4db';
-- ninja arakkinar: Oct 2 Credit Sale (amount: 540.00, balance_after: 1710.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 1710.00 WHERE "reference_order_id" = '3b4e521b-16ba-477d-b958-71df7578c1de' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1710.00 WHERE "id" = 'c1bee817-98f1-4b76-a7bc-8748f13e0fe5';
-- ninja mugadar beach: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = '87262b76-8b35-4124-b103-6b2d676f10c7' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = 'c3f64959-21e4-4702-a992-8cd1c5d5b689';
-- nit kattangal: Oct 2 Credit Sale (amount: 590.00, balance_after: 2810.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 2810.00 WHERE "reference_order_id" = 'c05893f9-bfef-4dd6-9cb5-06956a7566ab' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2810.00 WHERE "id" = '960fa41b-75b4-4855-a7ef-57c51d47e916';
-- nkg: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '3fc2725d-cb2b-4baa-8780-17f6191f93c3' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '346d0ee8-2f70-474b-b32b-f06cbc3f4660';
-- nook manasseri: Oct 2 Credit Sale (amount: 540.00, balance_after: 2420.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 2420.00 WHERE "reference_order_id" = '5c5907fb-2355-4cee-997e-c7c476527caf' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2420.00 WHERE "id" = '2d35e722-d6ee-4fc0-9f0c-ec6a262bfa45';
-- orkid bekery velliparmba: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '1662e1aa-e5fd-4742-9629-32c99a5c580e' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '1fb39cd6-c1b9-4fc2-b85e-99fce18b2c1b';
-- ossobocco: Oct 2 Credit Sale (amount: 590.00, balance_after: 610.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 610.00 WHERE "reference_order_id" = '164cbd66-fcf0-4947-8a80-2e39a0f412cd' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 610.00 WHERE "id" = 'fa25ce12-0bb5-4c5e-bf6a-a8ce9960c417';
-- pappaya pullaloor: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '2def027f-c43e-40df-a3c0-49edd946c2cb' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'd60478ba-8252-4856-bcd9-360195648218';
UPDATE "customers_customer" SET "current_balance" = 470.00 WHERE "id" = '7bc5658d-f208-44e9-b7c6-6db0313470bd';
-- periyangad bekery: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'f9bc1938-1ff4-4e4a-88f3-9a08ddd82221' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'da1f9122-bf56-48e6-9ebf-2e69d9b7a1c7';
UPDATE "customers_customer" SET "current_balance" = 450.00 WHERE "id" = '3022c00b-28ae-41c6-af0e-ae2e501aa3c4';
-- raheem shop mediaone: Oct 2 Credit Sale (amount: 590.00, balance_after: 4720.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 4720.00 WHERE "reference_order_id" = '1241799a-2943-4d22-b749-3071c7e9f24f' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 4720.00 WHERE "id" = '7509f98b-5380-4e96-bd88-3c861d7acce7';
-- raheem shop mundikkal: Oct 2 Credit Sale (amount: 490.00, balance_after: 490.00)
UPDATE "credits_credittransaction" SET "amount" = 490.00, "balance_after" = 490.00 WHERE "reference_order_id" = '19f5e3eb-5033-41b8-a839-07ec9c9a397b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 490.00 WHERE "id" = 'daaf2b27-7449-464a-95bb-1baae98f4490';
-- raidan kallanthode: Oct 2 Credit Sale (amount: 690.00, balance_after: 510.00)
UPDATE "credits_credittransaction" SET "amount" = 690.00, "balance_after" = 510.00 WHERE "reference_order_id" = 'd0db478d-41ce-4b80-8c24-1f9ed5b7f8cd' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 7386.00 WHERE "id" = '0d653df0-863e-4afe-a906-5ccbf494679b';
-- raidan mandi: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '2d733e80-76d8-42b6-8494-0192af447819' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'f257d44b-bd0d-453c-a990-ec2ad9828ee9';
-- rajitha chappathi company: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '3ee1c481-6315-434b-94b5-459c378ff3cc' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'b6643869-e550-4846-8fdf-aa7fa817977e';
-- razak shop narikkuni: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = 'ec6dee09-565c-4a05-a284-9bcee1706e9a' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = 'e05002de-155c-4686-a3b6-9474e914edbd';
-- red salad: Oct 2 Credit Sale (amount: 540.00, balance_after: 1810.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 1810.00 WHERE "reference_order_id" = 'd755d41c-d64c-4cf6-afa0-f7983c7d3dd0' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1810.00 WHERE "id" = 'f22a8cd6-8877-4826-a378-30c768753a1a';
-- royal feast padanilam: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'ec8e2c3a-dff9-4e42-8df4-fc816d90c81c' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'f3232a50-6428-41ec-bbd0-f5ecbd7e20c2';
-- royal koduvally: Oct 2 Credit Sale (amount: 580.00, balance_after: 580.00)
UPDATE "credits_credittransaction" SET "amount" = 580.00, "balance_after" = 580.00 WHERE "reference_order_id" = '9319a769-1e80-4302-8d16-21d4b19305fc' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 580.00 WHERE "id" = 'f6a3ed79-136a-4a8b-be11-cb48bbb9fcc0';
-- saps mundikkal thazham: Oct 2 Credit Sale (amount: 590.00, balance_after: 1930.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1930.00 WHERE "reference_order_id" = 'd84e7be9-7d22-41fe-8bf3-f91bac163666' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1930.00 WHERE "id" = '85d0f7a3-fb03-4443-a475-1a8f6790fa12';
UPDATE "customers_customer" SET "current_balance" = 840.00 WHERE "id" = '1ccbbedd-f08d-4c99-9916-f0fdda1d408e';
-- shaz live alfahm: Oct 2 Credit Sale (amount: 540.00, balance_after: 840.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 840.00 WHERE "reference_order_id" = '525d2409-14a6-4c35-91c0-ca00421f5ee1' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 840.00 WHERE "id" = '8b1162b2-53e6-471d-9f22-07cc459b4c88';
-- smokies: Oct 2 Credit Sale (amount: 590.00, balance_after: 3565.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 3565.00 WHERE "reference_order_id" = '943907dc-7d43-4174-9deb-3eb86536e2b2' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 3565.00 WHERE "id" = 'a0421574-6334-4b84-a5e5-46243cff2d4a';
-- sp: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '48b3391b-192a-465c-8c48-b92ff66c0826' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = 'b7e62a2f-9aa8-4d9e-aaaa-2d7c630fe7cf';
-- sugar bekery: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = 'c7fe2e26-60ce-47ae-a989-e1124d7114e0' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = '397d5e3e-4202-471e-8e4e-21ff00728f14';
-- sulthan mandi: Oct 2 Credit Sale (amount: 540.00, balance_after: 765.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 765.00 WHERE "reference_order_id" = 'dcca0b41-17ea-4a29-8413-8954be25f2a8' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 765.00 WHERE "id" = '1d35e983-f0fe-4759-b38b-058b546be03e';
-- sweet valley: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '989b5862-e821-4110-af21-c58e98b03337' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1400.00 WHERE "id" = '500e6118-e0ff-4000-985c-5fb0c291a591';
-- tasty bekery: Oct 2 Credit Sale (amount: 590.00, balance_after: 594.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 594.00 WHERE "reference_order_id" = '39e48052-0ab6-44a0-90db-6dd23fe895a2' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 594.00 WHERE "id" = 'de6356c9-0ddb-49dc-bc03-d7cee3b9dec0';
-- tasty bekery: Oct 2 Credit Sale (amount: 540.00, balance_after: 510.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 510.00 WHERE "reference_order_id" = 'ebd5db11-0bf3-4887-ae3b-b22ebda1783d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 510.00 WHERE "id" = '159927bc-d59c-42bd-b4e7-2c4c15f7aef6';
-- tasty hut restaurent: Oct 2 Credit Sale (amount: 530.00, balance_after: 530.00)
UPDATE "credits_credittransaction" SET "amount" = 530.00, "balance_after" = 530.00 WHERE "reference_order_id" = '72330682-d2d3-4a9b-8fef-dfcdb33f0cc8' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 530.00 WHERE "id" = '1d537e3a-af1a-447b-8e86-915b398cdca0';
-- tea topia kunnamangalam: Oct 2 Credit Sale (amount: 540.00, balance_after: 2925.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 2925.00 WHERE "reference_order_id" = 'b5278943-1024-496a-af72-f11f593cac1a' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 2925.00 WHERE "id" = '33de219c-9f40-46d7-b047-9293ca2bd261';
-- thuba bakery: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'b8c5c4c8-e1b0-479c-93f6-59a3e2eeadad' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '4f570478-e33e-47e8-930f-6607b8db78c0';
-- thuba kuttikattoor: Oct 2 Credit Sale (amount: 590.00, balance_after: 640.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 640.00 WHERE "reference_order_id" = '7b7d4b72-1c10-48d2-b708-25ff39d5f5de' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 640.00 WHERE "id" = 'cdd8d1b3-7f8c-4f3f-a894-a4c712a236b6';
-- thukish kunnamgalam: Oct 2 Credit Sale (amount: 540.00, balance_after: 12240.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 12240.00 WHERE "reference_order_id" = 'b1d18108-0025-4ff6-a31a-c932cdb349fc' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 12240.00 WHERE "id" = '5eb48c17-b04b-406f-8343-d1e79e85fc1f';
-- thurkish kattangal: Oct 2 Credit Sale (amount: 540.00, balance_after: 20730.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 20730.00 WHERE "reference_order_id" = '5c24cef1-efa4-4378-adc9-d498e53bd472' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 20730.00 WHERE "id" = '6760d06b-2b90-4487-936d-38b4fe162eb7';
-- thurkish kuttikattoor: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = '711113ba-490d-4ae6-a5ce-b1a977c0283b' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = '6695c1f7-9c61-478c-b8b6-c1c7471c0e43';
-- top in balusseri: Oct 2 Credit Sale (amount: 540.00, balance_after: 540.00)
UPDATE "credits_credittransaction" SET "amount" = 540.00, "balance_after" = 540.00 WHERE "reference_order_id" = 'f31639e7-6482-4f26-ae1e-9ea7c66dabd9' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 540.00 WHERE "id" = 'a2d37b43-d21d-4df9-83fb-b3e618f8ca3f';
-- usna bakes: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = 'ac97217c-2d44-49e5-8d08-72e3908e6f00' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '95d45d15-3c4c-4f30-a05f-9201a29dd6bf';
-- vavad felafil: Oct 2 Credit Sale (amount: 590.00, balance_after: 920.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 920.00 WHERE "reference_order_id" = '87f18a6b-81f2-4391-98aa-96ea3492d867' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 920.00 WHERE "id" = 'e914b0ca-38ea-4022-b445-c3401bc22276';
-- velliparamba chappathi yettan: Oct 2 Credit Sale (amount: 590.00, balance_after: 4865.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 4865.00 WHERE "reference_order_id" = 'bec78520-87cb-4e78-8675-e1e548007eb1' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 4865.00 WHERE "id" = '07be323f-97b2-4933-9617-eae60806aca7';
-- vinod bekery peruvayal: Oct 2 Credit Sale (amount: 590.00, balance_after: 590.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 590.00 WHERE "reference_order_id" = '34810cae-82fb-48d8-b2c9-a26756588747' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 590.00 WHERE "id" = '8cf802b3-67df-40ed-ba1c-fd39ad0e95fe';
-- xylem kitchen pvt ltd: Oct 2 Credit Sale (amount: 590.00, balance_after: 47990.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 47990.00 WHERE "reference_order_id" = 'd61eeb0f-fe44-41ae-9e9c-df866c5d2e80' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 47990.00 WHERE "id" = '5fd79c4c-357b-426e-9d76-5fd0538bfb3e';
-- zain kubboos: Oct 2 Credit Sale (amount: 475.00, balance_after: 475.00)
UPDATE "credits_credittransaction" SET "amount" = 475.00, "balance_after" = 475.00 WHERE "reference_order_id" = 'f6c48a49-5050-4e6a-9838-a82a85beb44d' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 479.00 WHERE "id" = '8e57d2e3-1a71-40eb-9324-31888c1aba9c';
-- zeezo mims: Oct 2 Credit Sale (amount: 590.00, balance_after: 1290.00)
UPDATE "credits_credittransaction" SET "amount" = 590.00, "balance_after" = 1290.00 WHERE "reference_order_id" = 'ec9efb8d-82c1-4633-a67d-b442b978f891' AND "transaction_type" = 'CREDIT_SALE';
UPDATE "customers_customer" SET "current_balance" = 1290.00 WHERE "id" = '4d35c0eb-240e-4638-89c0-e2f283858605';

COMMIT;