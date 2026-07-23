-- EUDAMED MDR UDI/Device Registration PostgreSQL DDL - Consolidated Baseline
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$ BEGIN CREATE TYPE issuing_entity_code_enum AS ENUM ('GS1','HIBCC','ICCBBA','IFA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE risk_class_enum AS ENUM ('CLASS_I','CLASS_IR','CLASS_IM','CLASS_IS','CLASS_IIA','CLASS_IIB','CLASS_III'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE device_type_enum AS ENUM ('DEVICE','SYSTEM_OR_PROCEDURE_PACK'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE device_status_enum AS ENUM ('ON_THE_MARKET','NOT_INTENDED_FOR_EU_MARKET','NO_LONGER_PLACED_ON_THE_MARKET'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE production_identifier_type_enum AS ENUM ('SERIALISATION_NUMBER','LOT_NUMBER','MANUFACTURING_DATE','EXPIRATION_DATE','SOFTWARE_VERSION'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE validation_severity_enum AS ENUM ('INFO','WARNING','ERROR'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE validation_rule_type_enum AS ENUM ('MANDATORY','ENUM','FORMAT','RANGE','CARDINALITY','REFERENCE','CONDITIONAL','XSD'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE xml_generation_status_enum AS ENUM ('DRAFT','VALIDATION_FAILED','XML_GENERATED','XSD_VALIDATION_FAILED','READY_FOR_UPLOAD','SUPERSEDED'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS basic_udi_di (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), basic_udi_di VARCHAR(100) NOT NULL UNIQUE,
 issuing_entity_code issuing_entity_code_enum NOT NULL, manufacturer_srn VARCHAR(50) NOT NULL,
 risk_class risk_class_enum NOT NULL, model_name VARCHAR(250) NOT NULL, device_type device_type_enum NOT NULL DEFAULT 'DEVICE',
 animal_tissues_cells BOOLEAN NOT NULL DEFAULT FALSE, human_tissues_cells BOOLEAN NOT NULL DEFAULT FALSE,
 human_product_check BOOLEAN NOT NULL DEFAULT FALSE, medicinal_product_check BOOLEAN NOT NULL DEFAULT FALSE,
 administering_medicine BOOLEAN NOT NULL DEFAULT FALSE, active BOOLEAN NOT NULL DEFAULT FALSE,
 implantable BOOLEAN NOT NULL DEFAULT FALSE, measuring_function BOOLEAN NOT NULL DEFAULT FALSE, reusable BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by VARCHAR(255), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by VARCHAR(255),
 CONSTRAINT chk_basic_udi_di_not_blank CHECK (btrim(basic_udi_di) <> '')
);

CREATE TABLE IF NOT EXISTS device (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), udi_di VARCHAR(100) NOT NULL UNIQUE,
 issuing_entity_code issuing_entity_code_enum NOT NULL, basic_udi_di_id UUID NOT NULL REFERENCES basic_udi_di(id) ON DELETE RESTRICT,
 reference_number VARCHAR(100) NOT NULL, device_status device_status_enum NOT NULL DEFAULT 'ON_THE_MARKET',
 sterile BOOLEAN NOT NULL DEFAULT FALSE, sterilization BOOLEAN NOT NULL DEFAULT FALSE, number_of_reuses INTEGER NOT NULL,
 base_quantity INTEGER NOT NULL CHECK (base_quantity > 0), latex BOOLEAN NOT NULL DEFAULT FALSE, reprocessed BOOLEAN NOT NULL DEFAULT FALSE,
 intended_purpose TEXT, single_use BOOLEAN, software_version VARCHAR(100), direct_marking_di VARCHAR(100),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by VARCHAR(255), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_by VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS device_emdn (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id UUID NOT NULL REFERENCES device(id) ON DELETE CASCADE, emdn_code VARCHAR(50) NOT NULL, emdn_description VARCHAR(500), emdn_version VARCHAR(50));
CREATE TABLE IF NOT EXISTS trade_name (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id UUID NOT NULL REFERENCES device(id) ON DELETE CASCADE, language_code VARCHAR(10) NOT NULL DEFAULT 'ANY', trade_name VARCHAR(500) NOT NULL);
CREATE TABLE IF NOT EXISTS production_identifier (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id UUID NOT NULL REFERENCES device(id) ON DELETE CASCADE, identifier_type production_identifier_type_enum NOT NULL, UNIQUE(device_id, identifier_type));
CREATE TABLE IF NOT EXISTS market_country (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id UUID NOT NULL REFERENCES device(id) ON DELETE CASCADE, country_code CHAR(2) NOT NULL CHECK(country_code ~ '^[A-Z]{2}$'), original_placed_on_market BOOLEAN NOT NULL DEFAULT FALSE, first_market_date DATE, withdrawal_date DATE, UNIQUE(device_id, country_code));
CREATE TABLE IF NOT EXISTS packaging_level (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), parent_device_id UUID NOT NULL REFERENCES device(id) ON DELETE CASCADE, packaging_udi_di VARCHAR(100) NOT NULL UNIQUE, issuing_entity_code issuing_entity_code_enum NOT NULL, packaging_level INTEGER NOT NULL CHECK(packaging_level > 0), quantity_contained INTEGER NOT NULL CHECK(quantity_contained > 0), status device_status_enum NOT NULL DEFAULT 'ON_THE_MARKET');
CREATE TABLE IF NOT EXISTS xml_mapping (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), source_entity VARCHAR(100) NOT NULL, source_field VARCHAR(150) NOT NULL, xml_path TEXT NOT NULL, cardinality VARCHAR(20) NOT NULL, is_required BOOLEAN NOT NULL DEFAULT FALSE, is_repeating BOOLEAN NOT NULL DEFAULT FALSE, active BOOLEAN NOT NULL DEFAULT TRUE, UNIQUE(source_entity, source_field, xml_path));
CREATE TABLE IF NOT EXISTS validation_rule (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), rule_code VARCHAR(50) NOT NULL UNIQUE, rule_name VARCHAR(255) NOT NULL, rule_type validation_rule_type_enum NOT NULL, severity validation_severity_enum NOT NULL DEFAULT 'ERROR', entity_name VARCHAR(100) NOT NULL, field_name VARCHAR(150), xml_path TEXT, rule_expression TEXT, error_message TEXT NOT NULL, recommended_correction TEXT, active BOOLEAN NOT NULL DEFAULT TRUE);
CREATE TABLE IF NOT EXISTS validation_result (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), validation_run_id UUID NOT NULL, device_id UUID REFERENCES device(id) ON DELETE SET NULL, rule_id UUID REFERENCES validation_rule(id) ON DELETE SET NULL, field_path TEXT, xml_path TEXT, severity validation_severity_enum NOT NULL, error_code VARCHAR(100), message TEXT NOT NULL, recommended_correction TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS xml_generation_job (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), device_id UUID REFERENCES device(id) ON DELETE SET NULL, requested_by VARCHAR(255), requested_at TIMESTAMPTZ NOT NULL DEFAULT now(), generation_status xml_generation_status_enum NOT NULL DEFAULT 'DRAFT', source_data_hash VARCHAR(128), generated_xml_hash VARCHAR(128));
CREATE TABLE IF NOT EXISTS xml_generation_log (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), generation_job_id UUID REFERENCES xml_generation_job(id) ON DELETE CASCADE, device_id UUID REFERENCES device(id) ON DELETE SET NULL, generated_at TIMESTAMPTZ NOT NULL DEFAULT now(), generated_by VARCHAR(255), application_version VARCHAR(50) NOT NULL, source_data_hash VARCHAR(128) NOT NULL, generated_xml_hash VARCHAR(128), validation_passed BOOLEAN NOT NULL, validation_summary JSONB);
COMMIT;
