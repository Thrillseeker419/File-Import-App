
# **File-Import-App**

This full-stack application allows healthcare providers to import discharge documents, review and edit the extracted data, and manage these records efficiently. The system supports data validation, enrichment, and auditing to ensure data integrity and compliance.

---

## **Features**

- **PDF Upload and Processing**: Import healthcare discharge lists in PDF format.
- **Manual Review and Editing**: Review extracted data, make corrections, and validate fields.
- **Data Enrichment**: Validate and decorate data fields using external services (e.g., phone number validation via APIs).
- **Audit Trails**: Track changes to data during the review process, including who made changes and when.
- **Future-Ready Design**: Designed to scale with additional file types, external integrations, and advanced healthcare protocols like HL7 and FHIR.

---

## **Prerequisites**

Before running the application, ensure the following software is installed on your machine:
- **Node.js**: Version `v22.11.0` (or the latest compatible version)
- **Python**: Version `3.13.0` (or the latest compatible version)
- **PostgreSQL**: The latest version (ensure the PostgreSQL service is running)

---

## **Setup Instructions**

### **1. Clone the Repository**

```bash
git clone https://github.com/Thrillseeker419/File-Import-App.git
cd File-Import-App
```

---

### **2. Install Dependencies**

#### **Backend**
Navigate to the backend folder:
```bash
cd backend
```

Install Python dependencies:
```bash
pip install flask flask-cors pdfplumber psycopg[binary]
```

Modify the database connection information inside `app.py` to match your local PostgreSQL configuration:
```python
DB_CONFIG = {
    "dbname": "my_database",
    "user": "app_user",
    "password": "securepassword",
    "host": "localhost",
    "port": "5432",
}
```

#### **Frontend**
Navigate to the React client folder:
```bash
cd react-api-client
```

Install Node.js dependencies:
```bash
npm install
```

---

### **3. Run the Application**

#### **Start the Frontend**
From the `react-api-client` folder:
```bash
npm run dev
```

#### **Start the Backend**
In a separate terminal, navigate to the backend folder:
```bash
cd backend
python app.py
```

---

### **4. Application Walkthrough**

For a guided tutorial on using the application, watch the video in this directory:  
[**Application Tutorial**](./Application-Tutorial.mkv)

---

## **Technology Stack**

- **Frontend**: React.js
- **Backend**: Flask (Python)
- **Database**: PostgreSQL

---

## **Design Highlights**

### **Data Model**
- **Normalization**: Avoids redundancy by separating data into logical tables (e.g., `Patient`, `Insurance`, `Provider`).
- **Scalability**: Supports many-to-many relationships with junction tables like `DischargeProvider` and `EpicHospital`.
- **Data Enrichment**: Designed to integrate external APIs for validation and decoration of data fields.

### **Scalability**
- Supports horizontal scaling with asynchronous job queues for large PDF processing workloads.
- Modular architecture for adding new data ingestion methods (e.g., HL7, FHIR).

---

## **Future Roadmap**

1. **Enhanced Validation**:
   - More business-specific rules for improved data accuracy.
   - Cross-referencing provider names with hospital directories.

2. **Additional Features**:
   - Dynamic validation rules isolated from core logic for flexibility.
   - Expanded auditing capabilities to monitor all table changes.

3. **Improved User Experience**:
   - Optimized React components for reduced re-renders and faster performance.
   - Contextual suggestions for enrichment fields.

---

## **License**

This project is licensed under the MIT License. See the LICENSE file for details.

