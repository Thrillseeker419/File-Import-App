import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pdfplumber  # For text extraction
import os
import re
from datetime import datetime, date
import psycopg
from psycopg import sql
from uuid import UUID
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})  # Adjust the origin as needed

# Directory to save uploaded PDFs
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Pretend the user is signed in
session_user_id = "77118899-1111-1111-1111-111111111111"  # Replace with the actual user_id
# Database connection configuration
DB_CONFIG = {
    "dbname": "my_database",
    "user": "app_user",
    "password": "securepassword",
    "host": "localhost",
    "port": "5432",
}

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the PDF Processor API"})

@app.route('/import-types', methods=['GET'])
def get_import_types():
    """
    Fetch all import types from the ImportType table.
    """
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT import_type_id, type_name FROM ImportType;")
                import_types = cursor.fetchall()
                return jsonify([{"id": row[0], "name": row[1]} for row in import_types])
    except Exception as e:
        logger.error(f"Error fetching import types: {e}")
        return jsonify({'error': 'Failed to fetch import types'}), 500


@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    import_type_id = request.form.get('import_type_id')
    if not import_type_id:
        return jsonify({'error': 'No import type selected'}), 400

    # Save the file securely
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    raw_data_id = None  # Initialize to track the raw_data_id
    
    try:
        # Insert raw PDF content into RawDataIngested table
        logger.info("Trying to insert file into RawDataIngested table.")
        raw_data_id = insert_raw_pdf(file_path, filename, import_type_id)

        # Process the PDF and extract data
        extracted_data = process_pdf(file_path)

        # Insert extracted data into TemporaryDischarge table
        insert_into_temporary_discharge(extracted_data, raw_data_id)

        return jsonify({
            'message': 'File uploaded and processed successfully',
            'data': extracted_data,
            'raw_data_id': raw_data_id 
        }), 200

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        
        return jsonify({'error': f'Failed to process file: {e}'}), 500



def insert_raw_pdf(file_path, filename, import_type_id):
    """
    Inserts raw PDF content into the RawDataIngested table and returns the raw_data_id.
    """
    try:
        # Read the raw PDF content
        with open(file_path, 'rb') as pdf_file:
            raw_content = pdf_file.read()

        
        # Connect to the database
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO RawDataIngested (source_file_name, raw_content, import_type_id, created_by, updated_by)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING raw_data_id;
                    """,
                    (filename, raw_content, import_type_id, session_user_id, session_user_id)
                )
                raw_data_id = cursor.fetchone()[0]
                conn.commit()
                logger.info("Raw PDF data inserted into RawDataIngested table.")
                return raw_data_id
    except Exception as e:
        logger.error(f"Error inserting raw PDF data: {e}")
        raise


def insert_into_temporary_discharge(parsed_data, raw_data_id):
    """
    Inserts parsed data into the TemporaryDischarge table.
    """
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                for record in parsed_data:
                    # Assuming `epic_id` is part of the parsed data and should be used instead of patient_id
                    epic_id = record.get("epic_id")  # Ensure the parsed data includes epic_id
                    cursor.execute(
                        """
                        INSERT INTO TemporaryDischarge (
                            name,
                            epic_id,  -- Replaced patient_id with epic_id
                            phone_number,
                            attending_physician,
                            date,
                            primary_care_provider,
                            insurance,
                            disposition,
                            raw_data_id,
                            status,
                            created_by,
                            updated_by,
                            hospital_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', %s, %s, %s);
                        """,
                        (
                            record["name"],
                            epic_id,  
                            record["phone_number"],
                            record["attending_physician"],
                            record["date"],
                            record["primary_care_provider"],
                            record["insurance"],
                            record["disposition"],
                            raw_data_id,
                            session_user_id,
                            session_user_id,
                            record["hospital"]
                        ),
                    )
                conn.commit()
                logger.info("Extracted data inserted into TemporaryDischarge table.")
    except Exception as e:
        logger.error(f"Error inserting into TemporaryDischarge: {e}")
        raise

def process_pdf(file_path):
    """
    Process the PDF file to extract text and return structured data.
    """
    try:
        # Extract text using pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = ''
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text + '\n'

        # Debug: Log the extracted text
        logger.info("Extracted Text:\n%s", text)

        # Parse text into structured data
        structured_data = parse_text_to_structured_data(text)
        logger.info("Extracted Structured Data:\n%s", structured_data)
        return structured_data

    except Exception as e:
        logger.error("Failed to process PDF: %s", e)
        return {'error': f'Failed to process PDF: {str(e)}'}
    
def remove_phone_number(text):
    """
    Remove any phone number from a given string.
    Matches phone numbers in formats like:
    - 404-727-1234
    - (404) 727-1234
    - 404 727 1234
    - 4047271234
    """
    # Regular expression to match various phone number formats
    phone_number_pattern = r"\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}"
    
    # Replace phone number with an empty string
    return re.sub(phone_number_pattern, "", text).strip()

def parse_text_to_structured_data(text):
    """
    Parse extracted text into structured JSON data based on the table format.
    """
    # Predefined lists for insurance and disposition types
    disposition_list = [
        "Home", "HHS", "SNF", "Home with Follow-up", "Home Health Care (HHC)", "Rehabilitation Facility (Rehab)", 
        "Hospice", "Acute Care Hospital", "Observation", "ICU", "ICU Stepdown", "Psychiatric Facility", 
        "Transfer to Another Hospital", "Emergency Department (ED)", "No Follow-Up Needed", "AMA (Against Medical Advice)"
    ]
    
    insurance_list = [
        "BCBS", "Aetna Health", "Self Pay", "Humana Health", "Medicare", "Medicaid", "United Healthcare", 
        "Cigna", "Anthem", "Tricare", "Blue Shield", "Kaiser Permanente", "No Insurance"
    ]
    
    logger.info(f"Text To Parse: {text}")

    # Split the input text into lines
    lines = text.strip().split("\n")
    
    # The first line is the title
    title = lines[0].strip()

    #Get hospital name
    hospital_name = title.split("Discharges")[0].strip()
    
    # The second line is the header; we don't need to parse it directly
    headers = lines[1].strip().split()
    
    # Initialize the list to hold the structured data
    data = []
    
    # Process each row of the table (starting from the 3rd line)
    for line in lines[2:]:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Extract Epic Id (EP followed by numbers)
        epic_id_match = re.search(r"EP\d+", line)
        date_match = re.search(r"\d{2}-\d{2}-\d{4}", line)
        
        # Match for phone numbers (make dashes and parentheses optional)
        phone_match = re.search(r"EP\d+\s+(\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}|\d{10})", line)  # Match phone number with or without dashes/parentheses
        
        if epic_id_match and date_match:
            epic_id = epic_id_match.group(0)
            date = date_match.group(0)
            phone_number = phone_match.group(1) if phone_match else ""
            
            # Extract the part before the epic id as the name
            name_and_provider = line.split(epic_id)[0].strip()
            name = name_and_provider.strip()
            
            # Extract the part after the date as the remaining details
            remaining_details = line.split(date)[1].strip()
            
            # Remove the phone number from the remaining details (if it's there)
            if phone_number:
                remaining_details = remaining_details.replace(phone_number, "").strip()
            
            # Extract the insurance and disposition
            insurance = "Unknown"
            disposition = "Unknown"
            
            for ins in insurance_list:
                if ins in remaining_details:
                    insurance = ins
                    remaining_details = remaining_details.replace(insurance, "").strip()
                    break
            
            for disp in disposition_list:
                if disp in remaining_details:
                    disposition = disp
                    remaining_details = remaining_details.replace(disposition, "").strip()
                    break
            
            # Extract Attending Physician and Primary Care Provider from the remaining details
            attending_physician = ""
            primary_care_provider = remaining_details.strip()
            
            # Extract the attending physician from the middle part (between epic_id and date), excluding the phone number
            attending_physician_match = re.search(r"(?<=\b" + re.escape(epic_id) + r"\s)(.*?)(?=\s" + re.escape(date) + r")", line)
            if attending_physician_match:
                attending_physician = remove_phone_number(attending_physician_match.group(0).strip())

            # Append the structured data to the list
            entry = {
                "name": name,
                "epic_id": epic_id,
                "phone_number": phone_number,
                "attending_physician": attending_physician,
                "date": date,
                "primary_care_provider": primary_care_provider,
                "insurance": insurance,
                "disposition": disposition,
                "hospital": hospital_name
            }
            
            # Add the entry to the list
            data.append(entry)
            
    logger.info(f"Total records parsed: {len(data)}")

    return data

def safe_isoformat(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    else:
        logger.debug(f"Value '{value}' is of type {type(value)} and does not have 'isoformat'")
        return value

@app.route('/review/<raw_data_id>', methods=['GET'])
def get_review_data(raw_data_id):
    """
    Fetch raw data, temporary Discharge, and enrichment data associated with a raw_data_id.
    """
    try:
        logger.info(f"Starting to fetch review data for raw_data_id: {raw_data_id}")
        
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Fetch raw data
                logger.info("Executing query to fetch raw data.")
                cursor.execute("""
                    SELECT 
                        r.source_file_name, 
                        u.name AS uploaded_by, 
                        r.created_at, 
                        r.raw_content, 
                        it.type_name AS import_type
                    FROM RawDataIngested r
                    LEFT JOIN AppUser u ON r.updated_by = u.app_user_id
                    LEFT JOIN ImportType it ON r.import_type_id = it.import_type_id
                    WHERE r.raw_data_id = %s
                """, (raw_data_id,))
                raw_data = cursor.fetchone()
                
                if cursor.description is None or raw_data is None:
                    logger.warning(f"No data found for raw_data_id: {raw_data_id}")
                    return jsonify({'error': 'No data found for the given raw_data_id'}), 404
                
                logger.info("Raw data fetched successfully.")

                # Safely map raw data to dictionary
                raw_data_dict = {
                    "fileName": raw_data[0],
                    "uploadedBy": raw_data[1],
                    "ingestTimestamp": safe_isoformat(raw_data[2]),
                    "rawContent": raw_data[3],
                    "importType": raw_data[4],
                }

                # Fetch temporary Discharge data
                logger.info("Executing query to fetch temporary discharge data.")
                cursor.execute("""
                    SELECT 
                        td.temp_discharge_id,
                        td.name,
                        td.epic_id,
                        td.phone_number,
                        td.attending_physician,
                        td.date,
                        td.primary_care_provider,
                        td.insurance,
                        td.disposition,
                        td.status,
                        td.hospital_name
                    FROM TemporaryDischarge td
                    WHERE td.raw_data_id = %s
                """, (raw_data_id,))
                temporary_discharge_rows = cursor.fetchall()

                if not temporary_discharge_rows:
                    logger.warning(f"No temporary discharge data found for raw_data_id: {raw_data_id}")
                    return jsonify({'error': 'No temporary discharge data found'}), 404
                
                logger.info("Temporary discharge data fetched successfully.")

                # Safely map temporaryDischarge to list of dicts
                temporary_discharge = [
                    {
                        "temp_discharge_id": row[0],
                        "name": row[1],
                        "epic_id": row[2],
                        "phone_number": row[3],
                        "attending_physician": row[4],
                        "date": safe_isoformat(row[5]),
                        "primary_care_provider": row[6],
                        "insurance": row[7],
                        "disposition": row[8],
                        "status": row[9],
                        "hospital_name": row[10] if len(row) > 10 else None,
                    }
                    for row in temporary_discharge_rows
                ]

                # Fetch enrichment data
                logger.info("Executing query to fetch enrichment data.")
                cursor.execute("""
                    SELECT 
                        ed.enrichment_data_id,
                        ed.temp_discharge_id,
                        ed.enrichment_type_id,
                        ed.enrichment_value,
                        ed.approved_at,
                        ed.approved_by,
                        ed.created_by,
                        ed.updated_by,
                        ed.created_at,
                        ed.updated_at,
                        et.type_name AS enrichment_type_name
                    FROM TemporaryEnrichmentData ed
                    LEFT JOIN EnrichmentType et ON et.enrichment_type_id = ed.enrichment_type_id
                    WHERE ed.temp_discharge_id IN (
                        SELECT temp_discharge_id 
                        FROM TemporaryDischarge 
                        WHERE raw_data_id = %s
                    )
                """, (raw_data_id,))
                enrichment_data_rows = cursor.fetchall()

                logger.info(f"Enrichment Data Rows Fetched: {len(enrichment_data_rows)}")
                
                # Safely map enrichmentData to list of dicts
                if enrichment_data_rows:
                    enrichment_data = [
                        {
                            "enrichment_data_id": row[0],
                            "temp_discharge_id": row[1],
                            "enrichment_type_id": row[2],
                            "enrichment_value": row[3],
                            "approved_at": safe_isoformat(row[4]),
                            "approved_by": row[5],
                            "created_by": row[6],
                            "updated_by": row[7],
                            "created_at": safe_isoformat(row[8]),
                            "updated_at": safe_isoformat(row[9]),
                            "enrichment_type_name": row[10],
                        }
                        for row in enrichment_data_rows
                    ]
                else:
                    enrichment_data = []
                    logger.info(f"No enrichment data found for raw_data_id: {raw_data_id}. Returning empty list.")
        
                logger.info("Data fetched and formatted successfully.")

                return jsonify({
                    "rawData": raw_data_dict,
                    "temporaryDischarge": temporary_discharge,
                    "enrichmentData": enrichment_data,
                })

    except Exception as e:
        logger.error(f"Error fetching review data for raw_data_id {raw_data_id}: {str(e)}")
        return jsonify({'error': f'Failed to fetch review data: {str(e)}'}), 500



# Route for approving discharge
def validate_phone_number(phone_number):
    """
    Validates a phone number by ensuring it contains at least 6 digits if provided.
    """
    if not phone_number:  # If the phone number is not provided, it's valid (optional field)
        return True

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone_number)

    # Check if there are at least 6 digits
    return len(digits) >= 6

def fetch_discharge_record(cursor, temp_discharge_id):
    """
    Fetches the discharge record from the TemporaryDischarge table.
    """
    cursor.execute("""
        SELECT name, epic_id, phone_number, attending_physician, date, primary_care_provider, insurance, disposition, status, hospital_name
        FROM TemporaryDischarge
        WHERE temp_discharge_id = %s
    """, (temp_discharge_id,))
    return cursor.fetchone()

@app.route('/api/approve/<temp_discharge_id>', methods=['POST'])
def approve_discharge(temp_discharge_id):
    """
    Approves a discharge record after validating its fields.
    """
    try:
        # Validate the temp_discharge_id
        if not is_valid_uuid(temp_discharge_id):
            logger.warning(f"Invalid UUID format: {temp_discharge_id}")
            return jsonify({"error": "Invalid discharge ID format."}), 400

        # Connect to the database using DB_CONFIG
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Fetch the discharge record
                discharge_record = fetch_discharge_record(cursor, temp_discharge_id)
                if not discharge_record:
                    logger.warning(f"No discharge record found for ID: {temp_discharge_id}")
                    return jsonify({"error": "Discharge record not found."}), 404

                # Extract fields
                (name, epic_id, phone_number, attending_physician, date, 
                 primary_care_provider, insurance, disposition, status, hospital_name) = discharge_record

                # Initialize errors dictionary
                errors = {}

                # Validate "required" fields
                if not name:
                    errors['name'] = "Name is required."
                if not epic_id:
                    errors['epic_id'] = "Epic ID is required."
                if not validate_phone_number(phone_number):
                    errors['phone_number'] = "Invalid phone number format." 
                if not date:
                    errors['date'] = "Date is required."
                elif not is_valid_date_format(date):
                    errors['date'] = "Date must be in MM-DD-YYYY format and valid."

                # If there are validation errors, return them
                if errors:
                    logger.warning(f"Validation errors for discharge ID {temp_discharge_id}: {errors}")
                    return jsonify({"errors": errors}), 400

                # All validations passed, proceed to approve
                # Log the action (Assuming session_user_id is obtained from session/authentication)
                session_user_id = "current_user_id"  # Replace with actual user ID from session
                logger.info(f"Approving discharge with ID: {temp_discharge_id} by user: {session_user_id}")

                # Execute the stored procedure with the provided temp_discharge_id
                cursor.execute(sql.SQL("SELECT f_approve_discharge(%s);"), [temp_discharge_id])

                # Commit the transaction
                conn.commit()

                # Log success
                logger.info(f"Successfully approved discharge with ID: {temp_discharge_id}")

        # Return a success response
        return jsonify({"message": "Discharge approved successfully."}), 200

    except psycopg.OperationalError as e:
        # Log database connection issues
        logger.error(f"Database connection error: {str(e)}")
        return jsonify({"error": f"Database connection error: {str(e)}"}), 500
    except Exception as e:
        # Log any other exceptions
        logger.error(f"An error occurred while approving discharge: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/reject/<temp_discharge_id>', methods=['POST'])
def reject_discharge(temp_discharge_id):
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE TemporaryDischarge 
                    SET status = 'Rejected', approved_at = CURRENT_TIMESTAMP, approved_by = %s
                    WHERE temp_discharge_id = %s
                    """,
                    ("11111111-1111-1111-1111-111111111111", temp_discharge_id),  # Assuming a static user ID for now
                )
                conn.commit()
        return jsonify({"message": "Record rejected successfully"}), 200
    except Exception as e:
        logger.error(f"Error rejecting record: {e}")
        return jsonify({"error": "Failed to reject record"}), 500


@app.route('/api/enrichment-types', methods=['GET'])
def get_enrichment_types():
    """
    Fetch all enrichment types from the database.
    """
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT enrichment_type_id, type_name, description
                    FROM EnrichmentType
                """)
                rows = cursor.fetchall()
                enrichment_types = [
                    {
                        "enrichment_type_id": str(row[0]),
                        "type_name": row[1],
                        "description": row[2],
                    }
                    for row in rows
                ]
        return jsonify({"enrichmentTypes": enrichment_types}), 200
    except Exception as e:
        logger.error(f"Error fetching enrichment types: {e}")
        return jsonify({"error": "Failed to fetch enrichment types"}), 500

@app.route('/api/temp-discharge/<temp_discharge_id>', methods=['GET'])
def get_discharge(temp_discharge_id):
    """
    Fetch discharge data along with its enrichment data.
    """
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(temp_discharge_id)
        except ValueError:
            logger.warning(f"Invalid UUID format: {temp_discharge_id}")
            return jsonify({"error": "Invalid discharge ID format"}), 400

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Fetch discharge data
                logger.info("Executing query to fetch discharge data.")
                cursor.execute("""
                    SELECT * 
                    FROM TemporaryDischarge 
                    WHERE temp_discharge_id = %s
                """, (temp_discharge_id,))
                discharge = cursor.fetchone()

                if not discharge:
                    logger.warning(f"Discharge record not found for ID: {temp_discharge_id}")
                    return jsonify({"error": "Discharge record not found"}), 404

                discharge_columns = [desc[0].lower() for desc in cursor.description]
                discharge_data = dict(zip(discharge_columns, discharge))

                # Fetch enrichment data
                logger.info("Executing query to fetch enrichment data.")
                cursor.execute("""
                    SELECT 
                        e.enrichment_data_id,
                        e.temp_discharge_id,
                        e.enrichment_type_id,
                        e.enrichment_value,
                        e.approved_at,
                        e.approved_by,
                        e.created_by,
                        e.updated_by,
                        e.created_at,
                        e.updated_at,
                        et.type_name,
                        et.description
                    FROM TemporaryEnrichmentData e
                    LEFT JOIN EnrichmentType et 
                        ON e.enrichment_type_id = et.enrichment_type_id
                    WHERE e.temp_discharge_id = %s
                """, (temp_discharge_id,))
                enrichment_rows = cursor.fetchall()

                enrichment_columns = [desc[0].lower() for desc in cursor.description]
                enrichment_data = [
                    {
                        "enrichment_data_id": str(row[0]),
                        "temp_discharge_id": str(row[1]),
                        "enrichment_type_id": str(row[2]),
                        "enrichment_value": row[3],
                        "approved_at": row[4].isoformat() if row[4] else None,
                        "approved_by": str(row[5]) if row[5] else None,
                        "created_by": str(row[6]) if row[6] else None,
                        "updated_by": str(row[7]) if row[7] else None,
                        "created_at": row[8].isoformat() if row[8] else None,
                        "updated_at": row[9].isoformat() if row[9] else None,
                        "type_name": row[10],
                        "description": row[11],
                    }
                    for row in enrichment_rows
                ]

                return jsonify({
                    "dischargeData": discharge_data,
                    "enrichmentData": enrichment_data
                }), 200
    except Exception as e:
        logger.error(f"Error fetching discharge record: {e}")
        return jsonify({"error": "Failed to fetch discharge record"}), 500

def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False

def is_valid_date_format(date_str):
    """
    Validates if the date string matches MM-DD-YYYY format and represents a real date.
    """
    date_regex = re.compile(r'^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])-\d{4}$')
    if not date_regex.match(date_str):
        return False
    try:
        month, day, year = map(int, date_str.split('-'))
        datetime(year, month, day)
    except ValueError:
        return False
    return True
@app.route('/api/temp-discharge/<temp_discharge_id>', methods=['PUT'])
def update_discharge(temp_discharge_id):
    """
    Update discharge data along with its enrichment data.
    """
    try:
        # Validate UUID format
        if not is_valid_uuid(temp_discharge_id):
            logger.warning(f"Invalid UUID format: {temp_discharge_id}")
            return jsonify({"error": "Invalid discharge ID format"}), 400

        data = request.get_json()
        if not data:
            logger.warning("No data provided in PUT request.")
            return jsonify({"error": "No data provided"}), 400

        discharge_data = data.get("dischargeData", {})
        enrichment_data = data.get("enrichmentData", [])

        logger.info(f"Received discharge_data: {discharge_data}")
        logger.info(f"Received enrichment_data: {enrichment_data}")

        # Validate discharge_data fields
        required_discharge_fields = ["name", "epic_id","date"]
        for field in required_discharge_fields:
            if not discharge_data.get(field):
                logger.warning(f"Missing required field in discharge_data: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate 'date' field format (MM-DD-YYYY)
        date_value = discharge_data.get('date')
        if not is_valid_date_format(date_value):
            logger.warning(f"Invalid date format or invalid date: {date_value}")
            return jsonify({"error": "Invalid date format or invalid date. Expected MM-DD-YYYY."}), 400

        # Validate phone number
        phone_number = discharge_data.get('phone_number')
        if not validate_phone_number(phone_number):
            logger.warning(f"Invalid phone number format: {phone_number}")
            return jsonify({"error": "Invalid phone number format."}), 400

        # Process enrichment_data
        valid_enrichment_data = []
        for enrichment in enrichment_data:
            enrichment_type_id = enrichment.get("enrichment_type_id")
            enrichment_value = enrichment.get("enrichment_value")

            if not enrichment_type_id:
                logger.warning("Enrichment data missing 'enrichment_type_id'.")
                continue  # Skip invalid enrichment entries

            if not enrichment_value or enrichment_value == "--select--":
                logger.info(f"Skipping enrichment_type_id {enrichment_type_id} due to empty or default value.")
                continue  # Skip if no valid value is provided

            if enrichment_type_id in ["c8f7629d-38ec-4506-93b8-c2a9a08b3b65", "2a8760cb-505b-4c6f-a0b0-2a4d87fe8850"]:
                if enrichment_value.lower() not in ["true", "false"]:
                    logger.warning(f"Invalid enrichment_value for type ID {enrichment_type_id}: {enrichment_value}")
                    return jsonify({"error": f"Enrichment value for type ID {enrichment_type_id} must be 'true' or 'false'."}), 400

            if len(enrichment_value) > 255:
                logger.warning(f"Enrichment value too long for type ID {enrichment_type_id}: {len(enrichment_value)} characters.")
                return jsonify({"error": f"Enrichment value for type ID {enrichment_type_id} exceeds 255 characters."}), 400

            valid_enrichment_data.append(enrichment)

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                conn.autocommit = False

                update_fields = []
                update_values = []
                excluded_keys = ["temp_discharge_id", "raw_data_id", "approved_by", "created_by", "updated_by", "updated_at"]
                for key, value in discharge_data.items():
                    if key in excluded_keys:
                        continue
                    update_fields.append(f"{key} = %s")
                    update_values.append(value)
                if update_fields:
                    update_query = f"""
                        UPDATE TemporaryDischarge
                        SET {', '.join(update_fields)},
                            updated_at = CURRENT_TIMESTAMP
                        WHERE temp_discharge_id = %s
                    """
                    update_values.append(temp_discharge_id)
                    cursor.execute(update_query, update_values)

                for enrichment in valid_enrichment_data:
                    enrichment_type_id = enrichment.get("enrichment_type_id")
                    enrichment_value = enrichment.get("enrichment_value")

                    cursor.execute("""
                        SELECT enrichment_data_id FROM TemporaryEnrichmentData
                        WHERE temp_discharge_id = %s AND enrichment_type_id = %s
                    """, (temp_discharge_id, enrichment_type_id))
                    result = cursor.fetchone()

                    if result:
                        enrichment_data_id = result[0]
                        cursor.execute("""
                            UPDATE TemporaryEnrichmentData
                            SET enrichment_value = %s,
                                updated_at = CURRENT_TIMESTAMP,
                                updated_by = %s
                            WHERE enrichment_data_id = %s
                        """, (enrichment_value, discharge_data.get("updated_by"), enrichment_data_id))
                    else:
                        cursor.execute("""
                            INSERT INTO TemporaryEnrichmentData (
                                temp_discharge_id, enrichment_type_id, enrichment_value, 
                                created_at, updated_at, created_by, updated_by
                            ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s)
                        """, (temp_discharge_id, enrichment_type_id, enrichment_value, discharge_data.get("created_by"), discharge_data.get("updated_by")))

                conn.commit()

        return jsonify({"message": "Discharge and enrichment data updated successfully"}), 200

    except Exception as e:
        logger.error(f"Error updating discharge record: {e}")
        return jsonify({"error": "Failed to update discharge record"}), 500


@app.route('/raw-data', methods=['GET'])
def get_raw_data():
    """
    Fetch all RawDataIngested entries along with their ImportType and Status.
    Supports optional filtering by created_at date range.

    Query Parameters:
        - start_date (optional): ISO 8601 formatted date string in UTC.
        - end_date (optional): ISO 8601 formatted date string in UTC.

    Status can be:
        - "No discharge records found"
        - "All records reviewed"
        - "Records still pending review"
    """
    try:
        logger.info("Fetching all raw data ingested entries.")

        # Extract query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Initialize filter conditions
        filters = []
        params = {}

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                filters.append("r.created_at >= %(start_date)s")
                params['start_date'] = start_date
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use ISO 8601 format.'}), 400

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                filters.append("r.created_at < %(end_date)s")
                params['end_date'] = end_date
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use ISO 8601 format.'}), 400

        # Build the WHERE clause
        where_clause = ""
        if filters:
            where_clause = "WHERE " + " AND ".join(filters)

        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # SQL Query to fetch required data with optional date filtering
                query = f"""
                    SELECT
                        r.raw_data_id,
                        r.source_file_name,
                        r.created_at,
                        it.type_name,
                        CASE
                            WHEN NOT EXISTS (
                                SELECT 1 FROM TemporaryDischarge td
                                WHERE td.raw_data_id = r.raw_data_id
                            ) THEN 'No discharge records found'
                            WHEN NOT EXISTS (
                                SELECT 1 FROM TemporaryDischarge td
                                WHERE td.raw_data_id = r.raw_data_id AND (td.status IS NULL OR td.status <> 'Approved')
                            ) THEN 'All records reviewed'
                            ELSE 'Records still pending review'
                        END AS status
                    FROM
                        RawDataIngested r
                    JOIN
                        ImportType it ON r.import_type_id = it.import_type_id
                    {where_clause}
                    ORDER BY
                        r.created_at DESC;
                """

                logger.info(f"Executing query: {query} with params: {params}")
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Define column names
                col_names = [desc[0] for desc in cursor.description]

                # Convert rows to list of dictionaries
                raw_data_list = [
                    {col_names[i]: row[i] for i in range(len(col_names))}
                    for row in rows
                ]

                logger.info(f"Fetched {len(raw_data_list)} raw data entries.")

                # Convert UUIDs to strings for JSON serialization
                for entry in raw_data_list:
                    entry['raw_data_id'] = str(entry['raw_data_id'])

                return jsonify(raw_data_list), 200

    except Exception as e:
        logger.error(f"Error fetching raw data: {e}")
        return jsonify({'error': 'Failed to fetch raw data'}), 500




if __name__ == '__main__':
    app.run(debug=True)
