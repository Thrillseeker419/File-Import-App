import psycopg
from psycopg import sql
import sys

# Configuration
SUPERUSER_DB = "postgres"
SUPERUSER_USER = "postgres" # Your PostgreSQL superuser username.
SUPERUSER_PASSWORD = "your_superuser_password"  # Ensure this matches your actual password (and don't commit a real one!)
SUPERUSER_HOST = "localhost" # Update if PostgreSQL is hosted elsewhere.
SUPERUSER_PORT = "5432" # Update if PostgreSQL is running on a different port.

DB_NAME = "my_database" # The name of the database to create.
DB_USER = "app_user" # The application user name.
DB_PASSWORD = "securepassword" #The application user's password.

# SQL for granting permissions
GRANT_PERMISSIONS_SQL = """
-- Grant permissions on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;

-- Grant permissions on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Ensure default privileges for future tables and sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;
"""

# SQL for schema and table creation with UUID defaults
SCHEMA_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- AppUser Table
CREATE TABLE IF NOT EXISTS AppUser (
    app_user_id UUID DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    role VARCHAR,
    password_hash VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_appuser PRIMARY KEY (app_user_id),
    CONSTRAINT uq_appuser_email UNIQUE (email)
);

-- Patient Table
CREATE TABLE IF NOT EXISTS Patient (
    patient_id UUID DEFAULT uuid_generate_v4(),
    full_name VARCHAR NOT NULL,
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_patient PRIMARY KEY (patient_id)
);

-- PatientPhone Table
CREATE TABLE IF NOT EXISTS PatientPhone (
    phone_id UUID DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL,
    phone_number VARCHAR NOT NULL,
    phone_validation_status VARCHAR,
    phone_type VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_patientphone PRIMARY KEY (phone_id),
    CONSTRAINT fk_patientphone_patient FOREIGN KEY (patient_id) 
        REFERENCES Patient(patient_id) 
        ON DELETE CASCADE
);

-- PatientAddress Table
CREATE TABLE IF NOT EXISTS PatientAddress (
    address_id UUID DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL,
    address VARCHAR NOT NULL,
    address_type VARCHAR,  -- Home, work, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_patientaddress PRIMARY KEY (address_id),
    CONSTRAINT fk_patientaddress_patient FOREIGN KEY (patient_id) 
        REFERENCES Patient(patient_id) 
        ON DELETE CASCADE
);

-- PatientEmail Table
CREATE TABLE IF NOT EXISTS PatientEmail (
    email_id UUID DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL,
    email VARCHAR NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_patientemail PRIMARY KEY (email_id),
    CONSTRAINT fk_patientemail_patient FOREIGN KEY (patient_id) 
        REFERENCES Patient(patient_id) 
        ON DELETE CASCADE
);

-- ImportType Table
CREATE TABLE IF NOT EXISTS ImportType (
    import_type_id UUID DEFAULT uuid_generate_v4(),
    type_name VARCHAR,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_importtype PRIMARY KEY (import_type_id)
);

-- RawDataIngested Table
CREATE TABLE IF NOT EXISTS RawDataIngested (
    raw_data_id UUID DEFAULT uuid_generate_v4(),
    source_file_name VARCHAR NOT NULL,
    raw_content TEXT,
    import_type_id UUID,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_rawdataingested PRIMARY KEY (raw_data_id),
    CONSTRAINT fk_rawdataingested_importtype FOREIGN KEY (import_type_id) 
        REFERENCES ImportType(import_type_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_rawdataingested_createdby FOREIGN KEY (created_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_rawdataingested_updatedby FOREIGN KEY (updated_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL
);

-- Epic Table
CREATE TABLE IF NOT EXISTS Epic (
    epic_id UUID DEFAULT uuid_generate_v4(),
    epic_identifier VARCHAR NOT NULL,
    patient_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_epic PRIMARY KEY (epic_id),
    CONSTRAINT uq_epic_epic_identifier UNIQUE (epic_identifier),
    CONSTRAINT fk_epic_patient FOREIGN KEY (patient_id) 
        REFERENCES Patient(patient_id) 
        ON DELETE SET NULL
);

-- Discharge Table
CREATE TABLE IF NOT EXISTS Discharge (
    discharge_id UUID DEFAULT uuid_generate_v4(),
    epic_id UUID NOT NULL,
    discharge_date DATE NOT NULL,
    disposition VARCHAR NOT NULL,
    discharge_reason VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_discharge PRIMARY KEY (discharge_id),
    CONSTRAINT fk_discharge_epic FOREIGN KEY (epic_id) 
        REFERENCES Epic(epic_id) 
        ON DELETE CASCADE
);

-- Provider Table
CREATE TABLE IF NOT EXISTS Provider (
    provider_id UUID DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_provider PRIMARY KEY (provider_id)
);

-- ProviderType Table
CREATE TABLE IF NOT EXISTS ProviderType (
    provider_type_id UUID DEFAULT uuid_generate_v4(),
    type_name VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_providertype PRIMARY KEY (provider_type_id)
);

-- ProviderProviderType Table
CREATE TABLE IF NOT EXISTS ProviderProviderType (
    provider_provider_type_id UUID DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL,
    provider_type_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_providerprovidertype PRIMARY KEY (provider_provider_type_id),
    CONSTRAINT fk_providerprovidertype_provider FOREIGN KEY (provider_id) 
        REFERENCES Provider(provider_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_providerprovidertype_providertype FOREIGN KEY (provider_type_id) 
        REFERENCES ProviderType(provider_type_id) 
        ON DELETE CASCADE
);

-- DischargeProvider Table
CREATE TABLE IF NOT EXISTS DischargeProvider (
    discharge_provider_id UUID DEFAULT uuid_generate_v4(),
    discharge_id UUID NOT NULL,
    provider_provider_type_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_dischargeprovider PRIMARY KEY (discharge_provider_id),
    CONSTRAINT fk_dischargeprovider_discharge FOREIGN KEY (discharge_id) 
        REFERENCES Discharge(discharge_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_dischargeprovider_providerprovidertype FOREIGN KEY (provider_provider_type_id) 
        REFERENCES ProviderProviderType(provider_provider_type_id) 
        ON DELETE CASCADE
);

-- Insurance Table
CREATE TABLE IF NOT EXISTS Insurance (
    insurance_id UUID DEFAULT uuid_generate_v4(),
    insurance_name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_insurance PRIMARY KEY (insurance_id)
);

-- EpicInsurance Table
CREATE TABLE IF NOT EXISTS EpicInsurance (
    epic_insurance_id UUID DEFAULT uuid_generate_v4(),
    epic_id UUID NOT NULL,
    insurance_id UUID NOT NULL,
    policy_number VARCHAR,
    coverage_details TEXT,
    insurance_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_epicinsurance PRIMARY KEY (epic_insurance_id),
    CONSTRAINT fk_epicinsurance_epic FOREIGN KEY (epic_id) 
        REFERENCES Epic(epic_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_epicinsurance_insurance FOREIGN KEY (insurance_id) 
        REFERENCES Insurance(insurance_id) 
        ON DELETE CASCADE
);

-- ProviderEpic Table
CREATE TABLE IF NOT EXISTS ProviderEpic (
    epic_provider_id UUID DEFAULT uuid_generate_v4(),
    epic_id UUID NOT NULL,
    provider_provider_type_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_providerepic PRIMARY KEY (epic_provider_id),
    CONSTRAINT fk_providerepic_epic FOREIGN KEY (epic_id) 
        REFERENCES Epic(epic_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_providerepic_providerprovidertype FOREIGN KEY (provider_provider_type_id) 
        REFERENCES ProviderProviderType(provider_provider_type_id) 
        ON DELETE CASCADE
);

-- Hospital Table
CREATE TABLE IF NOT EXISTS Hospital (
    hospital_id UUID DEFAULT uuid_generate_v4(),
    hospital_name VARCHAR NOT NULL,
    hospital_address VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_hospital PRIMARY KEY (hospital_id)
);

-- EpicHospital Table
CREATE TABLE IF NOT EXISTS EpicHospital (
    epic_hospital_id UUID DEFAULT uuid_generate_v4(),
    epic_id UUID NOT NULL,
    hospital_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_epichospital PRIMARY KEY (epic_hospital_id),
    CONSTRAINT fk_epichospital_epic FOREIGN KEY (epic_id) 
        REFERENCES Epic(epic_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_epichospital_hospital FOREIGN KEY (hospital_id) 
        REFERENCES Hospital(hospital_id) 
        ON DELETE CASCADE
);

-- TemporaryDischarge Table
CREATE TABLE IF NOT EXISTS TemporaryDischarge (
    temp_discharge_id UUID DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    epic_id TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    attending_physician TEXT NOT NULL,
    date TEXT NOT NULL,
    primary_care_provider TEXT NOT NULL,
    insurance TEXT NOT NULL,
    disposition TEXT NOT NULL,
    raw_data_id UUID,
    status VARCHAR,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by UUID,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hospital_name TEXT,
    CONSTRAINT pk_temporarydischarge PRIMARY KEY (temp_discharge_id),
    CONSTRAINT fk_temporarydischarge_rawdata FOREIGN KEY (raw_data_id) 
        REFERENCES RawDataIngested(raw_data_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_temporarydischarge_approvedby FOREIGN KEY (approved_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_temporarydischarge_createdby FOREIGN KEY (created_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_temporarydischarge_updatedby FOREIGN KEY (updated_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL
);

-- EnrichmentType Table
CREATE TABLE IF NOT EXISTS EnrichmentType (
    enrichment_type_id UUID DEFAULT uuid_generate_v4(),
    type_name VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_enrichmenttype PRIMARY KEY (enrichment_type_id)
);

-- TemporaryEnrichmentData Table
CREATE TABLE IF NOT EXISTS TemporaryEnrichmentData (
    enrichment_data_id UUID DEFAULT uuid_generate_v4(),
    temp_discharge_id UUID NOT NULL,
    enrichment_type_id UUID NOT NULL,
    enrichment_value TEXT,
    approved_at TIMESTAMP,
    approved_by UUID,
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_temporaryenrichmentdata PRIMARY KEY (enrichment_data_id),
    CONSTRAINT fk_temporaryenrichmentdata_tempdischarge FOREIGN KEY (temp_discharge_id) 
        REFERENCES TemporaryDischarge(temp_discharge_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_temporaryenrichmentdata_enrichmenttype FOREIGN KEY (enrichment_type_id) 
        REFERENCES EnrichmentType(enrichment_type_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_temporaryenrichmentdata_approvedby FOREIGN KEY (approved_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_temporaryenrichmentdata_createdby FOREIGN KEY (created_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_temporaryenrichmentdata_updatedby FOREIGN KEY (updated_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE SET NULL
);

-- TemporaryDischargeAudit Table
CREATE TABLE IF NOT EXISTS TemporaryDischargeAudit (
    temporary_discharge_audit_id UUID DEFAULT uuid_generate_v4(),
    temp_discharge_id UUID NOT NULL,
    action VARCHAR NOT NULL,  -- e.g., INSERT, UPDATE, DELETE
    changed_by UUID NOT NULL,
    change_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_value JSONB,
    new_value JSONB,
    CONSTRAINT pk_temporarydischargeaudit PRIMARY KEY (temporary_discharge_audit_id),
    CONSTRAINT fk_temporarydischargeaudit_tempdischarge FOREIGN KEY (temp_discharge_id) 
        REFERENCES TemporaryDischarge(temp_discharge_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_temporarydischargeaudit_changedby FOREIGN KEY (changed_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE RESTRICT
);

-- TemporaryEnrichmentDataAudit Table
CREATE TABLE IF NOT EXISTS TemporaryEnrichmentDataAudit (
    temporary_enrichment_data_audit_id UUID DEFAULT uuid_generate_v4(),
    enrichment_data_id UUID NOT NULL,
    action VARCHAR NOT NULL,  -- e.g., INSERT, UPDATE, DELETE
    changed_by UUID NOT NULL,
    change_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    previous_value JSONB,
    new_value JSONB,
    CONSTRAINT pk_temporaryenrichmentdataaudit PRIMARY KEY (temporary_enrichment_data_audit_id),
    CONSTRAINT fk_temporaryenrichmentdataaudit_enrichmentdata FOREIGN KEY (enrichment_data_id) 
        REFERENCES TemporaryEnrichmentData(enrichment_data_id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_temporaryenrichmentdataaudit_changedby FOREIGN KEY (changed_by) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE RESTRICT
);

-- RawDataIngestedAudit Table
CREATE TABLE IF NOT EXISTS RawDataIngestedAudit (
    raw_data_ingested_audit_id UUID DEFAULT uuid_generate_v4(),
    raw_data_id UUID,  -- Reference to the raw data
    action_type VARCHAR(10),  -- 'INSERT', 'UPDATE', 'DELETE'
    action_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Timestamp of action
    action_user UUID NOT NULL,  -- User who made the change
    original_data JSONB,  -- Original data (if it's an update or delete)
    new_data JSONB,  -- New data (if it's an insert or update)
    CONSTRAINT pk_rawdataingestedaudit PRIMARY KEY (raw_data_ingested_audit_id),
    CONSTRAINT fk_rawdataingestedaudit_rawdata FOREIGN KEY (raw_data_id) 
        REFERENCES RawDataIngested(raw_data_id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_rawdataingestedaudit_actionuser FOREIGN KEY (action_user) 
        REFERENCES AppUser(app_user_id) 
        ON DELETE RESTRICT
);


"""


# Optional seed data (you can expand this as needed)
SEED_SQL = """
-- Seed data for Users
INSERT INTO AppUser (app_user_id, name, email, role, password_hash) VALUES 
    ('77118899-1111-1111-1111-111111111111', 'Admin User John Doe', 'admin@example.com', 'Admin', 'hashed_password')
ON CONFLICT (email) DO NOTHING;

-- Seed data for ImportType
INSERT INTO ImportType (import_type_id, type_name, description)
VALUES 
    ('11111111-1111-1111-1111-111111111111', 
     'Sacred Heart Hospital Discharges Text-Based Import', 
     'Imports the following fields: Name Epic Id Phone number Attending Physician Date Primary Care Provider Insurance Disposition');

-- Seed data for EnrichmentType
-- Seed script to populate EnrichmentType table with explicit UUIDs
INSERT INTO EnrichmentType (enrichment_type_id, type_name, description)
VALUES 
    ('eeb9f5b4-15e3-4ac2-a4b4-5c7c7f92b717', 'Phone Validation Status', 'Indicates the status of phone validation for a given record.'),
    ('add1ed02-dc4e-460a-b3e1-9b9a160ab2b2', 'Phone Type', 'Specifies the type of phone number (e.g., mobile, landline, etc.).'),
    ('c8f7629d-38ec-4506-93b8-c2a9a08b3b65', 'Insurance Verified', 'Indicates whether the insurance status has been verified.'),
    ('2a8760cb-505b-4c6f-a0b0-2a4d87fe8850', 'Provider Verified', 'Indicates whether the provider has been verified.');

-- Seed data for ProviderType
INSERT INTO ProviderType (provider_type_id, type_name, created_at, updated_at)
VALUES
    ('7a21f43a-df8e-4f7e-9c4a-c3f8f9e28fe2', 'Primary Care', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('47b4d1f9-60fc-4ec4-aab4-7c94b9cd5290', 'Attending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

"""

TRIGGERS_SQL = """
-- Create Trigger Function for TemporaryDischargeAudit
CREATE OR REPLACE FUNCTION log_temporary_discharge_audit() 
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO TemporaryDischargeAudit (temp_discharge_id, action, changed_by, change_timestamp, previous_value)
        VALUES (OLD.temp_discharge_id, 'DELETE', OLD.updated_by, CURRENT_TIMESTAMP, row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO TemporaryDischargeAudit (temp_discharge_id, action, changed_by, change_timestamp, new_value)
        VALUES (NEW.temp_discharge_id, 'INSERT', NEW.updated_by, CURRENT_TIMESTAMP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO TemporaryDischargeAudit (temp_discharge_id, action, changed_by, change_timestamp, previous_value, new_value)
        VALUES (NEW.temp_discharge_id, 'UPDATE', NEW.updated_by, CURRENT_TIMESTAMP, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create Trigger for TemporaryDischarge Table
CREATE TRIGGER trigger_temporary_discharge_audit
AFTER INSERT OR UPDATE OR DELETE ON TemporaryDischarge
FOR EACH ROW EXECUTE FUNCTION log_temporary_discharge_audit();

-- Create Trigger Function for TemporaryEnrichmentDataAudit
CREATE OR REPLACE FUNCTION log_temporary_enrichment_data_audit() 
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO TemporaryEnrichmentDataAudit (enrichment_data_id, action, changed_by, change_timestamp, previous_value)
        VALUES (OLD.enrichment_data_id, 'DELETE', OLD.updated_by, CURRENT_TIMESTAMP, row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO TemporaryEnrichmentDataAudit (enrichment_data_id, action, changed_by, change_timestamp, new_value)
        VALUES (NEW.enrichment_data_id, 'INSERT', NEW.updated_by, CURRENT_TIMESTAMP, row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO TemporaryEnrichmentDataAudit (enrichment_data_id, action, changed_by, change_timestamp, previous_value, new_value)
        VALUES (NEW.enrichment_data_id, 'UPDATE', NEW.updated_by, CURRENT_TIMESTAMP, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create Trigger for TemporaryEnrichmentData Table
CREATE TRIGGER trigger_temporary_enrichment_data_audit
AFTER INSERT OR UPDATE OR DELETE ON TemporaryEnrichmentData
FOR EACH ROW EXECUTE FUNCTION log_temporary_enrichment_data_audit();

-- Create Trigger Function for RawDataIngestedAudit
CREATE OR REPLACE FUNCTION log_raw_data_ingested_audit() 
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO RawDataIngestedAudit (raw_data_ingested_audit_id, raw_data_id, action_type, action_timestamp, action_user, original_data)
        VALUES (uuid_generate_v4(), OLD.raw_data_id, 'DELETE', CURRENT_TIMESTAMP, OLD.updated_by, row_to_json(OLD)::jsonb);
        RETURN OLD;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO RawDataIngestedAudit (raw_data_ingested_audit_id, raw_data_id, action_type, action_timestamp, action_user, new_data)
        VALUES (uuid_generate_v4(), NEW.raw_data_id, 'INSERT', CURRENT_TIMESTAMP, NEW.updated_by, row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO RawDataIngestedAudit (raw_data_ingested_audit_id, raw_data_id, action_type, action_timestamp, action_user, original_data, new_data)
        VALUES (uuid_generate_v4(), NEW.raw_data_id, 'UPDATE', CURRENT_TIMESTAMP, NEW.updated_by, row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create Trigger for RawDataIngested Table
CREATE TRIGGER trigger_raw_data_ingested_audit
AFTER INSERT OR UPDATE OR DELETE ON RawDataIngested
FOR EACH ROW EXECUTE FUNCTION log_raw_data_ingested_audit();

"""

PROCEDURE_SQL = """
CREATE OR REPLACE FUNCTION f_approve_discharge(i_temp_discharge_id UUID)
RETURNS VOID AS $$
DECLARE
    tv_patient_id UUID;
    tv_epic_id UUID; -- To store the generated UUID from Epic
    tv_raw_epic_id VARCHAR; -- To store the raw epic_id from TemporaryDischarge
    tv_phone_number VARCHAR;
    tv_phone_validation_status VARCHAR;
    tv_phone_type VARCHAR;
    tv_insurance_name VARCHAR;
    tv_insurance_verified BOOLEAN;
    tv_attending_physician VARCHAR;
    tv_primary_care_provider VARCHAR;
    tv_provider_verified BOOLEAN;
    tv_hospital_name VARCHAR;
    tv_discharge_id UUID;
    tv_provider_id UUID;
    tv_provider_provider_type_id UUID;
    tv_insurance_id UUID;
    tv_hospital_id UUID;
    tv_provider_type_id UUID;
    tv_full_name VARCHAR;
    tv_disposition VARCHAR;
    tv_discharge_date DATE;
    tv_provider_name VARCHAR; -- To use in the loop
    tv_enrichment_record RECORD; -- To hold enrichment data
BEGIN
    -- Fetch discharge data from TemporaryDischarge
    SELECT td.name, td.epic_id, td.date, td.phone_number,
           td.insurance, td.attending_physician, td.primary_care_provider,
           td.hospital_name, td.disposition
    INTO tv_full_name, tv_raw_epic_id, tv_discharge_date, tv_phone_number,
         tv_insurance_name, tv_attending_physician, tv_primary_care_provider, tv_hospital_name, tv_disposition
    FROM TemporaryDischarge td
    WHERE td.temp_discharge_id = i_temp_discharge_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Discharge not found for ID: %', i_temp_discharge_id;
    END IF;

    -- Fetch enrichment data from TemporaryEnrichmentData
    FOR tv_enrichment_record IN
        SELECT ted.enrichment_type_id, ted.enrichment_value
        FROM TemporaryEnrichmentData ted
        WHERE ted.temp_discharge_id = i_temp_discharge_id
    LOOP
        IF tv_enrichment_record.enrichment_type_id = 'eeb9f5b4-15e3-4ac2-a4b4-5c7c7f92b717' THEN
            -- Phone Validation Status
            tv_phone_validation_status := tv_enrichment_record.enrichment_value;
        ELSIF tv_enrichment_record.enrichment_type_id = 'add1ed02-dc4e-460a-b3e1-9b9a160ab2b2' THEN
            -- Phone Type
            tv_phone_type := tv_enrichment_record.enrichment_value;
        ELSIF tv_enrichment_record.enrichment_type_id = 'c8f7629d-38ec-4506-93b8-c2a9a08b3b65' THEN
            -- Insurance Verified
            tv_insurance_verified := tv_enrichment_record.enrichment_value::BOOLEAN;
        ELSIF tv_enrichment_record.enrichment_type_id = '2a8760cb-505b-4c6f-a0b0-2a4d87fe8850' THEN
            -- Provider Verified
            tv_provider_verified := tv_enrichment_record.enrichment_value::BOOLEAN;
        END IF;
    END LOOP;

    -- Check for existing Patient
    SELECT p.patient_id INTO tv_patient_id
    FROM Patient p
    WHERE p.full_name = tv_full_name;

    IF NOT FOUND THEN
        -- Insert new Patient
        INSERT INTO Patient (full_name, created_at, updated_at)
        VALUES (tv_full_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING patient_id INTO tv_patient_id;
    END IF;

    -- Check if epic_identifier already exists
    SELECT epic_id INTO tv_epic_id
    FROM Epic
    WHERE epic_identifier = tv_raw_epic_id;

    IF NOT FOUND THEN
        -- Insert into Epic table with raw_epic_id and retrieve generated epic_id
        INSERT INTO Epic (epic_identifier, patient_id, created_at, updated_at)
        VALUES (tv_raw_epic_id, tv_patient_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING epic_id INTO tv_epic_id;
    END IF;

    -- Insert into Discharge table using the generated epic_id
    INSERT INTO Discharge (epic_id, discharge_date, disposition, created_at, updated_at)
    VALUES (tv_epic_id, tv_discharge_date, tv_disposition, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    RETURNING discharge_id INTO tv_discharge_id;

    -- Handle Providers (Attending Physician and Primary Care Provider)
    -- Only proceed if at least one provider is present
    IF (tv_attending_physician IS NOT NULL AND TRIM(tv_attending_physician) <> '') OR
       (tv_primary_care_provider IS NOT NULL AND TRIM(tv_primary_care_provider) <> '') THEN

        FOR tv_provider_name IN SELECT unnest(ARRAY[
            CASE WHEN tv_attending_physician IS NOT NULL AND TRIM(tv_attending_physician) <> '' THEN tv_attending_physician ELSE NULL END,
            CASE WHEN tv_primary_care_provider IS NOT NULL AND TRIM(tv_primary_care_provider) <> '' THEN tv_primary_care_provider ELSE NULL END
        ])
        LOOP
            -- Skip if provider name is NULL or empty
            IF tv_provider_name IS NULL THEN
                CONTINUE;
            END IF;

            -- Check if provider exists
            SELECT pr.provider_id INTO tv_provider_id
            FROM Provider pr
            WHERE pr.name = tv_provider_name;

            IF NOT FOUND THEN
                -- Insert new Provider
                INSERT INTO Provider (name, created_at, updated_at)
                VALUES (tv_provider_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING provider_id INTO tv_provider_id;
            END IF;

            -- Handle Provider Type
            IF tv_provider_name = tv_attending_physician THEN
                tv_provider_type_id := '47b4d1f9-60fc-4ec4-aab4-7c94b9cd5290';
            ELSE
                tv_provider_type_id := '7a21f43a-df8e-4f7e-9c4a-c3f8f9e28fe2';
            END IF;

            -- Check or insert into ProviderProviderType
            SELECT ppt.provider_provider_type_id INTO tv_provider_provider_type_id
            FROM ProviderProviderType ppt
            WHERE ppt.provider_id = tv_provider_id AND ppt.provider_type_id = tv_provider_type_id;

            IF NOT FOUND THEN
                INSERT INTO ProviderProviderType (provider_id, provider_type_id, created_at, updated_at)
                VALUES (tv_provider_id, tv_provider_type_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING provider_provider_type_id INTO tv_provider_provider_type_id;
            END IF;

            -- Insert into DischargeProvider table 
            IF tv_discharge_id IS NOT NULL THEN
                -- Check if a matching record already exists in DischargeProvider
                PERFORM 1
                FROM DischargeProvider dp
                WHERE dp.discharge_id = tv_discharge_id AND dp.provider_provider_type_id = tv_provider_provider_type_id;

                IF NOT FOUND THEN
                    -- Insert into DischargeProvider table only if the record does not exist
                    INSERT INTO DischargeProvider (discharge_id, provider_provider_type_id, created_at, updated_at)
                    VALUES (tv_discharge_id, tv_provider_provider_type_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                END IF;
            END IF;
        END LOOP;
    END IF;

    -- Check and insert into PatientPhone only if tv_phone_number is not null or empty
    IF tv_phone_number IS NOT NULL AND TRIM(tv_phone_number) <> '' THEN
        PERFORM 1
        FROM PatientPhone pp
        WHERE pp.patient_id = tv_patient_id 
          AND pp.phone_number = tv_phone_number
          AND pp.phone_validation_status = tv_phone_validation_status
          AND pp.phone_type = tv_phone_type;

        IF NOT FOUND THEN
            INSERT INTO PatientPhone (patient_id, phone_number, phone_validation_status, phone_type, created_at, updated_at)
            VALUES (tv_patient_id, tv_phone_number, tv_phone_validation_status, tv_phone_type, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        END IF;
    END IF;

    -- Insert into Insurance and EpicInsurance only if tv_insurance_name is not null or empty
    IF tv_insurance_name IS NOT NULL AND TRIM(tv_insurance_name) <> '' THEN
        SELECT i.insurance_id INTO tv_insurance_id
        FROM Insurance i
        WHERE i.insurance_name = tv_insurance_name;

        IF NOT FOUND THEN
            INSERT INTO Insurance (insurance_name, created_at, updated_at)
            VALUES (tv_insurance_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING insurance_id INTO tv_insurance_id;
        END IF;

        -- Insert into EpicInsurance if not already present
        INSERT INTO EpicInsurance (epic_id, insurance_id, insurance_verified, created_at, updated_at)
        VALUES (tv_epic_id, tv_insurance_id, tv_insurance_verified, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    END IF;

    -- Insert data into Hospital and EpicHospital only if tv_hospital_name is not null or empty
    IF tv_hospital_name IS NOT NULL AND TRIM(tv_hospital_name) <> '' THEN
        SELECT h.hospital_id INTO tv_hospital_id
        FROM Hospital h
        WHERE h.hospital_name = tv_hospital_name;

        IF NOT FOUND THEN
            INSERT INTO Hospital (hospital_name, created_at, updated_at)
            VALUES (tv_hospital_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING hospital_id INTO tv_hospital_id;
        END IF;

        -- Insert into EpicHospital if not already present
        PERFORM 1
        FROM EpicHospital eh
        WHERE eh.epic_id = tv_epic_id AND eh.hospital_id = tv_hospital_id;

        IF NOT FOUND THEN
            INSERT INTO EpicHospital (epic_id, hospital_id, created_at, updated_at)
            VALUES (tv_epic_id, tv_hospital_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        END IF;
    END IF;

    -- Update the status of TemporaryDischarge
    UPDATE TemporaryDischarge
    SET status = 'Approved'
    WHERE temp_discharge_id = i_temp_discharge_id;

END;
$$ LANGUAGE plpgsql;

"""



def create_database():
    """Create the target database if it doesn't exist."""
    connection = None
    cursor = None
    try:
        connection = psycopg.connect(
            dbname=SUPERUSER_DB,
            user=SUPERUSER_USER,
            password=SUPERUSER_PASSWORD,
            host=SUPERUSER_HOST,
            port=SUPERUSER_PORT
        )
        connection.autocommit = True  # Enable autocommit mode
        cursor = connection.cursor()

        # Use psycopg's SQL composition to prevent SQL injection
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = {dbname}").format(
            dbname=sql.Literal(DB_NAME)
        ))
        if not cursor.fetchone():
            print(f"Database '{DB_NAME}' does not exist. Creating...")
            cursor.execute(sql.SQL("CREATE DATABASE {dbname}").format(
                dbname=sql.Identifier(DB_NAME)
            ))
        else:
            print(f"Database '{DB_NAME}' already exists.")
    except psycopg.OperationalError as e:
        print(f"Operational error creating database: {e}")
        sys.exit(1)  # Exit the script if connection fails
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def create_roles_and_schema():
    """Create roles, schema, and seed data."""
    connection = None
    cursor = None
    try:
        connection = psycopg.connect(
            dbname=DB_NAME,
            user=SUPERUSER_USER,
            password=SUPERUSER_PASSWORD,
            host=SUPERUSER_HOST,
            port=SUPERUSER_PORT
        )
        connection.autocommit = False  # Disable autocommit for transactional integrity
        cursor = connection.cursor()

        # Create application user
        cursor.execute(sql.SQL("SELECT 1 FROM pg_roles WHERE rolname = {role}").format(
            role=sql.Literal(DB_USER)
        ))
        if not cursor.fetchone():
            print(f"Role '{DB_USER}' does not exist. Creating...")
            cursor.execute(sql.SQL("CREATE ROLE {role} WITH LOGIN PASSWORD {password}").format(
                role=sql.Identifier(DB_USER),
                password=sql.Literal(DB_PASSWORD)
            ))
        else:
            print(f"Role '{DB_USER}' already exists.")

        # Grant permissions on the database
        cursor.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {dbname} TO {role}").format(
            dbname=sql.Identifier(DB_NAME),
            role=sql.Identifier(DB_USER)
        ))

        # Create schema and tables
        print("Creating schema and tables...")
        cursor.execute(SCHEMA_SQL)

        # Create triggers for auditing
        print("Creating triggers for auditing...")
        cursor.execute(TRIGGERS_SQL)

        # Seed data 
        print("Seeding initial data...")
        cursor.execute(SEED_SQL)

        # Grant additional permissions on tables and sequences
        print("Granting permissions on tables and sequences...")
        cursor.execute(GRANT_PERMISSIONS_SQL)

        # Create Procedures 
        print("Creating stored procedures...")
        cursor.execute(PROCEDURE_SQL)
        

        connection.commit()
        print("Roles, schema, and initial data created successfully.")
    except psycopg.OperationalError as e:
        print(f"Operational error creating roles or schema: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating roles or schema: {e}")
        if connection:
            connection.rollback()  # Rollback in case of error
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    print("Step 1: Creating database...")
    create_database()

    print("Step 2: Creating roles, schema, and seeding data...")
    create_roles_and_schema()

    print("Database setup complete!")
