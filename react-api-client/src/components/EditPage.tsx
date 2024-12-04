import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";

// TypeScript Interfaces
interface EnrichmentType {
  enrichment_type_id: string;
  type_name: string;
  description: string;
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
  created_at: string | null;
  updated_at: string | null;
  description: string;
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
  submitted_at: string;
  approved_at: string | null;
  approved_by: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

interface ReviewData {
  dischargeData: TemporaryDischarge;
  enrichmentData: EnrichmentData[];
}

const EditPage: React.FC = () => {
  const { temp_discharge_id } = useParams<{ temp_discharge_id: string }>();
  const navigate = useNavigate();

  // State Definitions
  const [enrichmentTypes, setEnrichmentTypes] = useState<EnrichmentType[]>([]);
  const [formData, setFormData] = useState<ReviewData>({
    dischargeData: {
      temp_discharge_id: "",
      name: "",
      epic_id: "",
      phone_number: "",
      attending_physician: "",
      date: "",
      primary_care_provider: "",
      insurance: "",
      disposition: "",
      status: "",
      hospital_name: null,
      raw_data_id: null,
      submitted_at: "",
      approved_at: null,
      approved_by: null,
      created_by: null,
      updated_by: null,
      created_at: "",
      updated_at: "",
    },
    enrichmentData: [],
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({});

  // Fetch Enrichment Types and Discharge Data
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch all enrichment types
        const enrichmentResponse = await axios.get<{ enrichmentTypes: EnrichmentType[] }>(
          "http://127.0.0.1:5000/api/enrichment-types"
        );
        const fetchedEnrichmentTypes = enrichmentResponse.data.enrichmentTypes;
        setEnrichmentTypes(fetchedEnrichmentTypes);

        // Fetch discharge data
        const dischargeResponse = await axios.get<ReviewData>(
          `http://127.0.0.1:5000/api/temp-discharge/${temp_discharge_id}`
        );
        const fetchedDischargeData = dischargeResponse.data.dischargeData;
        const fetchedEnrichmentData = dischargeResponse.data.enrichmentData;

        // Merge enrichment types with existing enrichment data
        const mergedEnrichmentData: EnrichmentData[] = fetchedEnrichmentTypes.map((etype) => {
          const existing = fetchedEnrichmentData.find(
            (edata) => edata.enrichment_type_id === etype.enrichment_type_id
          );
          return existing
            ? existing
            : {
                enrichment_data_id: "",
                temp_discharge_id: temp_discharge_id || "",
                enrichment_type_id: etype.enrichment_type_id,
                enrichment_type_name: etype.type_name,
                enrichment_value: "",
                approved_at: null,
                approved_by: null,
                created_by: null,
                updated_by: null,
                created_at: null,
                updated_at: null,
                description: etype.description,
              };
        });

        setFormData({
          dischargeData: fetchedDischargeData,
          enrichmentData: mergedEnrichmentData,
        });
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to fetch data.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [temp_discharge_id]);

  // Validation Function
  const validateForm = (): boolean => {
    const errors: { [key: string]: string } = {};

    // Validate 'date' field
    const dateValue = formData.dischargeData.date;
    if (!dateValue) {
      errors.date = "Date is required.";
    } else {
      const dateRegex = /^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])-\d{4}$/; // MM-DD-YYYY
      if (!dateRegex.test(dateValue)) {
        errors.date = "Date must be in MM-DD-YYYY format.";
      } else {
        // Further validate if it's a real date
        const [month, day, year] = dateValue.split("-").map(Number);
        const dateObject = new Date(year, month - 1, day);
        if (
          dateObject.getFullYear() !== year ||
          dateObject.getMonth() + 1 !== month ||
          dateObject.getDate() !== day
        ) {
          errors.date = "Invalid date.";
        }
      }
    }

    // Validate phone number field. - Just doing a rudimentary check for now.
    const phoneNumber = formData.dischargeData.phone_number;
    if (phoneNumber && phoneNumber.replace(/\D/g, "").length < 6) {
    errors.phone_number = "Phone number must contain at least 6 digits if provided.";
    }
    
    // Validate other required fields
    const requiredFields = [
      "name",
      "epic_id",
    ];
    requiredFields.forEach((field) => {
      if (!formData.dischargeData[field as keyof TemporaryDischarge]) {
        errors[field] = `${field.replace(/_/g, " ")} is required.`;
      }
    });

    // Validate enrichment data (now not required)
    // Only validate if the field is filled or a valid option is selected
    enrichmentTypes.forEach((etype) => {
      const enrichment = formData.enrichmentData.find((ed) => ed.enrichment_type_id === etype.enrichment_type_id);
      if (enrichment && enrichment.enrichment_value && enrichment.enrichment_value !== "--select--") {
        if (
          etype.enrichment_type_id === "c8f7629d-38ec-4506-93b8-c2a9a08b3b65" ||
          etype.enrichment_type_id === "2a8760cb-505b-4c6f-a0b0-2a4d87fe8850"
        ) {
          // Expecting boolean values
          if (enrichment.enrichment_value !== "true" && enrichment.enrichment_value !== "false") {
            errors[`enrichment_${etype.enrichment_type_id}`] = `${etype.type_name} must be true or false.`;
          }
        } else {
          // For text enrichment types, enforce maximum length if applicable
          if (enrichment.enrichment_value.length > 255) {
            errors[`enrichment_${etype.enrichment_type_id}`] = `${etype.type_name} must be at most 255 characters.`;
          }
        }
      }
    });

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle Changes for Both Discharge and Enrichment Data
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
    enrichmentTypeId?: string
  ) => {
    const { value, name } = e.target;

    if (name.startsWith("dischargeData.")) {
      const key = name.split(".")[1];
      setFormData((prevData) => ({
        ...prevData,
        dischargeData: {
          ...prevData.dischargeData,
          [key]: value,
        },
      }));
    } else if (enrichmentTypeId) {
      // Update enrichmentData based on enrichment_type_id
      setFormData((prevData) => ({
        ...prevData,
        enrichmentData: prevData.enrichmentData.map((enrichment) =>
          enrichment.enrichment_type_id === enrichmentTypeId
            ? { ...enrichment, enrichment_value: value }
            : enrichment
        ),
      }));
    }
  };

  // Handle Form Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate the form
    if (!validateForm()) {
      alert("Please correct the errors in the form.");
      return;
    }

    // Prepare the payload
    const payload = {
      dischargeData: formData.dischargeData,
      enrichmentData: formData.enrichmentData
        .filter((edata) => edata.enrichment_value && edata.enrichment_value !== "--select--")
        .map((edata) => ({
          enrichment_type_id: edata.enrichment_type_id,
          enrichment_value: edata.enrichment_value,
        })),
    };

    try {
      console.log("Payload to update:", payload);
      await axios.put(`http://127.0.0.1:5000/api/temp-discharge/${temp_discharge_id}`, payload);
      alert("Record updated successfully!");
      navigate(-1); // Navigate back to the previous page
    } catch (err) {
      console.error("Error updating data:", err);
      alert("Failed to update record.");
    }
  };

  if (loading) return <p>Loading...</p>;
  if (error) return <p role="alert" className="error-message">{error}</p>;

  return (
    <main className="container">
      <h1>Edit Discharge Record</h1>
      <form onSubmit={handleSubmit}>
        {/* Discharge Data Section */}
        <section aria-labelledby="discharge-data-heading" className="discharge-section">
          <h2 id="discharge-data-heading">Discharge Data</h2>
          {
            Object.entries(formData.dischargeData).map(([key, value]) => {
                const nonEditableFields = [
                "created_by",
                "updated_by",
                "temp_discharge_id",
                "updated_at",
                "status",
                "submitted_at",
                "raw_data_id",
                "approved_at",
                "approved_by",
                "created_at",
                ];
                if (nonEditableFields.includes(key)) {
                return null;
                }

                let inputType = "text";
                if (key === "date") {
                inputType = "text"; // Changed from 'date' to 'text'
                }

                const isRequired = key === "name" || key === "epic_id"; // Only name and epic_id are required

                return (
                <div key={key} className="form-group">
                    <label htmlFor={key}>
                    {key.replace(/_/g, " ")}:
                    </label>
                    <input
                    type={inputType}
                    id={key}
                    name={`dischargeData.${key}`}
                    value={value || ""}
                    onChange={(e) => handleChange(e)}
                    required={isRequired} // Apply the required attribute conditionally
                    aria-describedby={validationErrors[key] ? `${key}-error` : undefined}
                    aria-invalid={!!validationErrors[key]}
                    />
                    {validationErrors[key] && (
                    <p id={`${key}-error`} className="error-message">
                        {validationErrors[key]}
                    </p>
                    )}
                </div>
                );
            })
            }
        </section>

        {/* Enrichment Data Section */}
        <section aria-labelledby="enrichment-data-heading" className="discharge-section">
          <h2 id="enrichment-data-heading">Enrichment Data</h2>
          {enrichmentTypes.map((etype) => {
            const enrichment = formData.enrichmentData.find(
              (edata) => edata.enrichment_type_id === etype.enrichment_type_id
            );

            // Determine if the enrichment type requires a true/false dropdown
            const isTrueFalseDropdown =
              etype.enrichment_type_id === "c8f7629d-38ec-4506-93b8-c2a9a08b3b65" ||
              etype.enrichment_type_id === "2a8760cb-505b-4c6f-a0b0-2a4d87fe8850";

            return (
              <div key={etype.enrichment_type_id} className="form-group">
                <label htmlFor={`enrichment-${etype.enrichment_type_id}`}>
                  {etype.type_name} ({etype.description || "N/A"}):
                </label>
                {isTrueFalseDropdown ? (
                  <select
                    id={`enrichment-${etype.enrichment_type_id}`}
                    name={`enrichmentData.${etype.enrichment_type_id}`}
                    value={enrichment?.enrichment_value || "--select--"} // Default to --select--
                    onChange={(e) => handleChange(e, etype.enrichment_type_id)}
                    aria-describedby={
                      validationErrors[`enrichment_${etype.enrichment_type_id}`]
                        ? `enrichment-${etype.enrichment_type_id}-error`
                        : undefined
                    }
                    aria-invalid={!!validationErrors[`enrichment_${etype.enrichment_type_id}`]}
                  >
                    <option value="--select--">--select--</option>
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                ) : (
                  <input
                    type="text"
                    id={`enrichment-${etype.enrichment_type_id}`}
                    name={`enrichmentData.${etype.enrichment_type_id}`}
                    value={enrichment?.enrichment_value || ""}
                    onChange={(e) => handleChange(e, etype.enrichment_type_id)}
                    placeholder={etype.description || `Enter ${etype.type_name}`}
                    maxLength={255} // Ensure it matches DB constraints
                    aria-describedby={
                      validationErrors[`enrichment_${etype.enrichment_type_id}`]
                        ? `enrichment-${etype.enrichment_type_id}-error`
                        : undefined
                    }
                    aria-invalid={!!validationErrors[`enrichment_${etype.enrichment_type_id}`]}
                  />
                )}
                {validationErrors[`enrichment_${etype.enrichment_type_id}`] && (
                  <p
                    id={`enrichment-${etype.enrichment_type_id}-error`}
                    className="error-message"
                  >
                    {validationErrors[`enrichment_${etype.enrichment_type_id}`]}
                  </p>
                )}
              </div>
            );
          })}
        </section>

        {/* Action Buttons */}
        <div className="action-buttons">
          <button type="submit">Save Changes</button>
          <button type="button" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </main>
  );
};

export default EditPage;
