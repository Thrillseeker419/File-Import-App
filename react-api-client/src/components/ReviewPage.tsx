import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import ConfirmModal from "./ConfirmModal";

// Define interfaces for the expected data structure
interface RawData {
  fileName: string;
  uploadedBy: string;
  ingestTimestamp: string;
  rawContent: string;
  importType: string;
}

interface EnrichmentData {
  enrichment_data_id: string;
  temp_discharge_id: string;
  enrichment_type_id: string;
  enrichment_type_name: string;
  enrichment_value: string | null;
  approved_at: string | null;
  approved_by: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  // Add other fields as necessary
}

interface TemporaryDischarge {
  temp_discharge_id: string;
  name: string;
  epic_id: string;
  phone_number: string;
  attending_physician: string;
  date: string;
  primary_care_provider: string;
  insurance: string;
  disposition: string;
  status: string;
  hospital_name: string | null;
  raw_data_id: string | null;
  // Add other fields as necessary
}

interface ReviewData {
  temporaryDischarge: TemporaryDischarge[];
  rawData: RawData | null;
  enrichmentData: EnrichmentData[];
}

const ReviewPage: React.FC = () => {
  const { raw_data_id } = useParams<{ raw_data_id: string }>();
  const navigate = useNavigate();
  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [modalText, setModalText] = useState<string>("");
  const [currentRowId, setCurrentRowId] = useState<string | null>(null);
  const [currentAction, setCurrentAction] = useState<string>("");
  const [validationErrors, setValidationErrors] = useState<{
    [key: string]: { [field: string]: string };
  }>({});
  const API_BASE_URL = "http://127.0.0.1:5000";

  useEffect(() => {
    const fetchReviewData = async () => {
      try {
        const response = await axios.get<ReviewData>(
          `${API_BASE_URL}/review/${raw_data_id}`
        );
        console.log("review data: ", response.data);
        setReviewData(response.data);
      } catch (error) {
        console.error("Error fetching review data:", error);
        setError("Failed to fetch review data.");
      } finally {
        setLoading(false);
      }
    };
    fetchReviewData();
  }, [raw_data_id]);

  const downloadRawPDF = () => {
    if (reviewData?.rawData?.rawContent) {
      // Assuming rawContent is a hex string, decode it
      const byteData = reviewData.rawData.rawContent.replace(/^\\x/, "");
      const binaryData = new Uint8Array(
        byteData.match(/.{1,2}/g)!.map((byte) => parseInt(byte, 16))
      );
      const blob = new Blob([binaryData], { type: "application/pdf" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = reviewData.rawData.fileName;
      link.click();
    }
  };

  const handleAction = (action: string, rowId: string) => {
    setCurrentRowId(rowId);
    setCurrentAction(action);
    setModalText(
      `Are you sure you want to ${action} this discharge? This cannot be undone.`
    );
    setModalVisible(true);

    // Optionally clear existing errors for this record
    setValidationErrors((prev) => {
      const updated = { ...prev };
      delete updated[rowId];
      return updated;
    });
  };

  const confirmAction = async () => {
    if (!currentRowId || !currentAction) return;

    try {
      const endpoint =
        currentAction === "approve"
          ? `${API_BASE_URL}/api/approve/${currentRowId}`
          : `${API_BASE_URL}/api/reject/${currentRowId}`;

      console.log(`Calling endpoint: ${endpoint}`);
      await axios.post(endpoint);
      console.log(`Successfully called: ${endpoint}`);

      setReviewData((prev) => {
        if (!prev) return prev;
        const updatedDischarge = prev.temporaryDischarge.map((record) =>
          record.temp_discharge_id === currentRowId
            ? {
                ...record,
                status:
                  currentAction === "approve" ? "Approved" : "Rejected",
              }
            : record
        );
        return { ...prev, temporaryDischarge: updatedDischarge };
      });

      // Clear any existing errors for this record upon successful action
      setValidationErrors((prev) => {
        const updated = { ...prev };
        delete updated[currentRowId];
        return updated;
      });

      setModalVisible(false);
      alert("Discharge record updated successfully.");
    } catch (error: any) {
      console.error(`Error trying to ${currentAction} the record:`, error);
      if (error.response && error.response.data && error.response.data.errors) {
        // Associate errors with the specific temp_discharge_id
        setValidationErrors((prev) => ({
          ...prev,
          [currentRowId!]: error.response.data.errors,
        }));
        setModalText(
          `Validation errors occurred. Please correct the fields and try again.`
        );
      } else if (
        error.response &&
        error.response.data &&
        error.response.data.error
      ) {
        setModalText(
          `Failed to ${currentAction} the record: ${error.response.data.error}`
        );
      } else {
        setModalText(
          `An unexpected error occurred while trying to ${currentAction} the record.`
        );
      }
    }
  };

  const handleEdit = (rowId: string) => {
    navigate(`/edit/${rowId}`);
  };

  if (loading) return <p>Loading...</p>;
  if (error) return <p role="alert" style={{ color: "red" }}>{error}</p>;

  return (
    <main className="container">
      <h1>Review File Import</h1>
      {reviewData?.rawData && (
        <section aria-labelledby="raw-data-heading">
          <h2 id="raw-data-heading">Uploaded File Information</h2>
          <p>
            <strong>Import Type:</strong> {reviewData.rawData.importType}
          </p>
          <p>
            <strong>File Name:</strong> {reviewData.rawData.fileName}
          </p>
          <p>
            <strong>Uploaded By:</strong> {reviewData.rawData.uploadedBy}
          </p>
          <p>
            <strong>Uploaded On:</strong>{" "}
            {new Date(reviewData.rawData.ingestTimestamp).toLocaleString()}
          </p>
          <button
            onClick={downloadRawPDF}
            className="outlined"
            aria-label="Download Raw PDF"
          >
            Download Raw PDF
          </button>
        </section>
      )}

      {/* Temporary Discharge and Enrichment Data Section */}
      <section aria-labelledby="temporary-discharge-heading">
        <h2 id="temporary-discharge-heading">Temporary Discharge</h2>
        {reviewData?.temporaryDischarge.map((discharge) => {
          const errors = validationErrors[discharge.temp_discharge_id];

          return (
            <article
              className="discharge-section"
              key={discharge.temp_discharge_id}
            >
              <header>
                <h3>{discharge.name}</h3>
              </header>
              <div className="discharge-info">
                <p>
                  <strong>Epic ID:</strong> {discharge.epic_id}
                </p>
                <p>
                  <strong>Phone Number:</strong> {discharge.phone_number}
                </p>
                <p>
                  <strong>Attending Physician:</strong>{" "}
                  {discharge.attending_physician}
                </p>
                <p>
                  <strong>Date:</strong>{" "}
                  {new Date(discharge.date).toLocaleDateString()}
                </p>
                <p>
                  <strong>Primary Care Provider:</strong>{" "}
                  {discharge.primary_care_provider}
                </p>
                <p>
                  <strong>Insurance:</strong> {discharge.insurance}
                </p>
                <p>
                  <strong>Disposition:</strong> {discharge.disposition}
                </p>
                <p>
                  <strong>Status:</strong> {discharge.status}
                </p>
                <p>
                  <strong>Hospital:</strong>{" "}
                  {discharge.hospital_name || "N/A"}
                </p>
              </div>

              <section
                aria-labelledby={`enrichment-data-heading-${discharge.temp_discharge_id}`}
              >
                <h4 id={`enrichment-data-heading-${discharge.temp_discharge_id}`}>
                  Enrichment Data
                </h4>
                <div className="table-container">
                  {reviewData.enrichmentData.filter(
                    (enrichment) =>
                      enrichment.temp_discharge_id ===
                      discharge.temp_discharge_id
                  ).length > 0 ? (
                    <table className="enrichment-table">
                      <caption>
                        Enrichment Data for {discharge.name}
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Enrichment Type</th>
                          <th scope="col">Enrichment Value</th>
                          <th scope="col">Created On</th>
                          <th scope="col">Updated On</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reviewData.enrichmentData
                          .filter(
                            (enrichment) =>
                              enrichment.temp_discharge_id ===
                              discharge.temp_discharge_id
                          )
                          .map((enrichment) => (
                            <tr key={enrichment.enrichment_data_id}>
                              <td>
                                {enrichment.enrichment_type_name || "N/A"}
                              </td>
                              <td>
                                {enrichment.enrichment_value || "N/A"}
                              </td>
                              <td>
                                {enrichment.created_at
                                  ? new Date(
                                      enrichment.created_at
                                    ).toLocaleString()
                                  : "N/A"}
                              </td>
                              <td>
                                {enrichment.updated_at
                                  ? new Date(
                                      enrichment.updated_at
                                    ).toLocaleString()
                                  : "N/A"}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  ) : (
                    <p>No enrichment data available for this discharge.</p>
                  )}
                </div>
              </section>

              {/* Display Validation Errors for this specific record */}
              {errors && Object.keys(errors).length > 0 && (
                <div className="error-message" role="alert">
                  <ul>
                    {Object.entries(errors).map(([field, message]) => (
                      <li key={field}>{message}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Conditionally Render Action Buttons */}
              {discharge.status !== "Approved" && (
                <div className="action-buttons">
                  <button
                    onClick={() => handleEdit(discharge.temp_discharge_id)}
                    className="edit-btn"
                    aria-label={`Edit discharge for ${discharge.name}`}
                  >
                    Edit Discharge
                  </button>
                  <button
                    onClick={() =>
                      handleAction("approve", discharge.temp_discharge_id)
                    }
                    aria-label={`Approve discharge for ${discharge.name}`}
                  >
                    Approve
                  </button>
                  {/* Optional: Add a Reject button if needed */}
                  {/* <button
                    onClick={() =>
                      handleAction("reject", discharge.temp_discharge_id)
                    }
                    aria-label={`Reject discharge for ${discharge.name}`}
                  >
                    Reject
                  </button> */}
                </div>
              )}
              {/* Optional: Display a badge or indicator for Approved status */}
              {discharge.status === "Approved" && (
                <div className="status-badge approved" aria-label="Approved Status">
                  Approved
                </div>
              )}
            </article>
          );
        })}
      </section>
      <ConfirmModal
        visible={modalVisible}
        text={modalText}
        onConfirm={confirmAction}
        onCancel={() => setModalVisible(false)}
      />
    </main>
  );
};

export default ReviewPage;
