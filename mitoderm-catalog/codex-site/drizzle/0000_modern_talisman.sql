CREATE TABLE `mitoderm_lead_rate_config` (
	`singleton` integer PRIMARY KEY NOT NULL,
	`salt` text NOT NULL,
	CONSTRAINT "mitoderm_lead_rate_config_singleton" CHECK("mitoderm_lead_rate_config"."singleton" = 1),
	CONSTRAINT "mitoderm_lead_rate_config_salt_length" CHECK(length("mitoderm_lead_rate_config"."salt") = 64)
);
--> statement-breakpoint
CREATE TABLE `mitoderm_lead_rate_limits` (
	`bucket_key` text PRIMARY KEY NOT NULL,
	`hits` integer NOT NULL,
	`expires_at` integer NOT NULL,
	CONSTRAINT "mitoderm_lead_rate_limits_hits" CHECK("mitoderm_lead_rate_limits"."hits" > 0)
);
--> statement-breakpoint
CREATE INDEX `mitoderm_lead_rate_limits_expiry` ON `mitoderm_lead_rate_limits` (`expires_at`);--> statement-breakpoint
CREATE TABLE `mitoderm_leads` (
	`id` text PRIMARY KEY NOT NULL,
	`request_id` text NOT NULL,
	`payload_hash` text NOT NULL,
	`name` text NOT NULL,
	`phone` text NOT NULL,
	`profession` text NOT NULL,
	`product_slug` text NOT NULL,
	`comment` text,
	`locale` text DEFAULT 'he' NOT NULL,
	`source_block` text NOT NULL,
	`privacy_consent` integer NOT NULL,
	`privacy_version` text NOT NULL,
	`status` text DEFAULT 'new' NOT NULL,
	`created_at` text NOT NULL,
	CONSTRAINT "mitoderm_leads_payload_hash_length" CHECK(length("mitoderm_leads"."payload_hash") = 64),
	CONSTRAINT "mitoderm_leads_name_length" CHECK(length("mitoderm_leads"."name") BETWEEN 2 AND 100),
	CONSTRAINT "mitoderm_leads_phone_length" CHECK(length("mitoderm_leads"."phone") BETWEEN 9 AND 16),
	CONSTRAINT "mitoderm_leads_profession" CHECK("mitoderm_leads"."profession" IN ('cosmetologist', 'doctor', 'nurse', 'clinic_owner', 'other')),
	CONSTRAINT "mitoderm_leads_product_slug_length" CHECK(length("mitoderm_leads"."product_slug") BETWEEN 1 AND 64),
	CONSTRAINT "mitoderm_leads_comment_length" CHECK("mitoderm_leads"."comment" IS NULL OR length("mitoderm_leads"."comment") <= 1000),
	CONSTRAINT "mitoderm_leads_locale" CHECK("mitoderm_leads"."locale" IN ('he', 'ru', 'en')),
	CONSTRAINT "mitoderm_leads_source_block_length" CHECK(length("mitoderm_leads"."source_block") BETWEEN 1 AND 64),
	CONSTRAINT "mitoderm_leads_privacy_consent" CHECK("mitoderm_leads"."privacy_consent" = 1)
);
--> statement-breakpoint
CREATE UNIQUE INDEX `mitoderm_leads_request_id_unique` ON `mitoderm_leads` (`request_id`);--> statement-breakpoint
CREATE INDEX `mitoderm_leads_created_at` ON `mitoderm_leads` ("created_at" desc);--> statement-breakpoint
CREATE INDEX `mitoderm_leads_status_created_at` ON `mitoderm_leads` (`status`,"created_at" desc);