import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

// Define TypeScript interfaces
interface ExtractedData {
  name?: string;
  epic_id?: string;
  phone_number?: string;
  attending_physician?: string;
  date?: string;
  primary_care_provider?: string;
  insurance?: string;
  disposition?: string;
  hospital?: string;
  [key: string]: string | undefined;
}

interface ImportType {
  id: string;
  name: string;
}

const UploadAndDisplayPDF: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string>("");
  const [extractedData, setExtractedData] = useState<ExtractedData[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [importTypes, setImportTypes] = useState<ImportType[]>([]);
  const [selectedImportType, setSelectedImportType] = useState<string>("");
  const [rawDataId, setRawDataId] = useState<string | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    // Fetch import types from the backend
    const fetchImportType = async () => {
      try {
        const response = await axios.get<ImportType[]>("http://127.0.0.1:5000/import-types");
        console.log("import types", response.data);
        setImportTypes(response.data);
        if (response.data.length > 0) {
          setSelectedImportType(response.data[0].id); // Default to the first import type
        }
      } catch (error) {
        console.error("Error fetching import types:", error);
        setError("Failed to fetch import types.");
      }
    };
    fetchImportType();
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setFile(event.target.files[0]);
      setError("");
      setMessage("");
      setExtractedData(null);
      setRawDataId(null);
    }
  };

  const handleImportTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedImportType(event.target.value);
  };

  const handleUpload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!file) {
      setError("Please select a PDF file first.");
      return;
    }
    if (!selectedImportType) {
      setError("Please select an import type.");
      return;
    }

    setLoading(true);
    setMessage("");
    setError("");
    setExtractedData(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("import_type_id", selectedImportType);

    try {
      const response = await axios.post<{
        [x: string]: any; data: ExtractedData[]; raw_data_id: string 
}>(
        "http://127.0.0.1:5000/upload-pdf",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      console.log("Backend Response:", response.data);

      if (response.data.error) {
        setError(response.data.error);
      } else {
        setExtractedData(response.data.data);
        setRawDataId(response.data.raw_data_id); // Store raw_data_id
        setMessage("PDF uploaded and processed successfully!");

        // Clear file input after successful upload
        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
        if (fileInput) {
          fileInput.value = ""; // Reset the file input
        }
        setFile(null); // Clear the file state
      }
    } catch (error: any) {
      console.error("Error uploading PDF:", error);
      setError(error.response?.data?.error || "Failed to upload and process the PDF.");
    } finally {
      setLoading(false);
    }
  };

  const handleReview = () => {
    console.log("Navigating to review page with rawDataId:", rawDataId);
    if (rawDataId) {
      navigate(`/review/${rawDataId}`);
    } else {
      console.error("rawDataId is null, cannot navigate.");
    }
  };

  return (
    <div className="container">
      {/* Skip Navigation Link for Accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <h2>Upload and Process PDF</h2>

      <form onSubmit={handleUpload} className="form">
        {/* Import Type Selection */}
        <div className="form-group">
          <label htmlFor="importType">Select an import type:</label>
          <select
            id="importType"
            value={selectedImportType}
            onChange={handleImportTypeChange}
            required
            aria-required="true"
          >
            {importTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
        </div>

        {/* File Input */}
        <div className="form-group">
          <label htmlFor="pdfFile">Choose PDF File:</label>
          <input
            type="file"
            id="pdfFile"
            accept="application/pdf"
            onChange={handleFileChange}
            required
            aria-required="true"
          />
        </div>

        {/* Upload Button */}
        <button type="submit" disabled={loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </form>

      {/* Success Message */}
      {message && (
        <p className="success-message" role="status">
          {message}
        </p>
      )}

      {/* Error Message */}
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {/* Extracted Data Table */}
      {extractedData && extractedData.length > 0 && (
        <div className="table-container">
          <h3>Extracted Data</h3>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Epic ID</th>
                <th>Phone Number</th>
                <th>Attending Physician</th>
                <th>Date</th>
                <th>Primary Care Provider</th>
                <th>Insurance</th>
                <th>Disposition</th>
                <th>Hospital</th>
              </tr>
            </thead>
            <tbody>
              {extractedData.map((record, index) => (
                <tr key={index}>
                  <td>{record.name || "—"}</td>
                  <td>{record.epic_id || "—"}</td>
                  <td>{record.phone_number || "—"}</td>
                  <td>{record.attending_physician || "—"}</td>
                  <td>{record.date || "—"}</td>
                  <td>{record.primary_care_provider || "—"}</td>
                  <td>{record.insurance || "—"}</td>
                  <td>{record.disposition || "—"}</td>
                  <td>{record.hospital || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            type="button"
            onClick={handleReview}
            disabled={!rawDataId}
            aria-disabled={!rawDataId}
            className="outlined"
          >
            Review Now
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadAndDisplayPDF;
