import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface RawDataEntry {
  raw_data_id: string;
  source_file_name: string;
  created_at: string;
  type_name: string;
  status: string;
}

const FileList: React.FC = () => {
  const [data, setData] = useState<RawDataEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [noFilesMessage, setNoFilesMessage] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    // Set default date range to last 7 days
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    setStartDate(sevenDaysAgo.toISOString().slice(0,16)); // 'YYYY-MM-DDThh:mm'
    setEndDate(now.toISOString().slice(0,16));
    fetchData(sevenDaysAgo.toISOString(), now.toISOString());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchData = async (filterStartDate?: string, filterEndDate?: string) => {
    setLoading(true);
    setError('');
    setNoFilesMessage('');
    try {
      let url = 'http://localhost:5000/raw-data';
      const params: any = {};

      if (filterStartDate) {
        params.start_date = filterStartDate;
      }

      if (filterEndDate) {
        params.end_date = filterEndDate;
      }

      const response = await axios.get<RawDataEntry[]>(url, { params });
      setData(response.data);
      setLoading(false);

      if (response.data.length === 0) {
        setNoFilesMessage('No files found for the selected time range.');
      }
    } catch (err: any) {
      console.error('Error fetching raw data:', err);
      setError('Failed to fetch raw data.');
      setLoading(false);
    }
  };

  const handleReview = (raw_data_id: string) => {
    navigate(`/review/${raw_data_id}`);
  };

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
      setError('Start date must be before end date.');
      return;
    }
    // Convert local datetime to UTC
    const utcStartDate = startDate ? new Date(startDate).toISOString() : undefined;
    const utcEndDate = endDate ? new Date(endDate).toISOString() : undefined;
    fetchData(utcStartDate, utcEndDate);
  };

  const handleClearFilters = () => {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    setStartDate(sevenDaysAgo.toISOString().slice(0,16));
    setEndDate(now.toISOString().slice(0,16));
    fetchData(sevenDaysAgo.toISOString(), now.toISOString());
  };

  return (
    <div className="container">
      <h2>Find an imported file to approve the import of its data into the database</h2>

      <form onSubmit={handleFilterSubmit} aria-label="Filter raw data by date range">
        <div className="form-group">
          <label htmlFor="start-date">Start Date and Time:</label>
          <input
            type="datetime-local"
            id="start-date"
            name="start-date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            aria-required="false"
          />
        </div>

        <div className="form-group">
          <label htmlFor="end-date">End Date and Time:</label>
          <input
            type="datetime-local"
            id="end-date"
            name="end-date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            aria-required="false"
          />
        </div>

        <button type="submit" aria-label="Filter files by selected date range">Filter</button>
        <button type="button" onClick={handleClearFilters} className="outlined" aria-label="Clear date filters">Clear Filters</button>
      </form>

      {loading && <div className="spinner" aria-label="Loading"></div>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {noFilesMessage && <p className="info-message">{noFilesMessage}</p>}

      {!loading && data.length > 0 && (
        <table aria-label="List of raw data ingested">
          <thead>
            <tr>
              <th scope="col">File Name</th>
              <th scope="col">Created At</th>
              <th scope="col">Import Type</th>
              <th scope="col">Status</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {data.map((entry) => (
              <tr key={entry.raw_data_id}>
                <td>{entry.source_file_name}</td>
                <td>{new Date(entry.created_at).toLocaleString()}</td>
                <td>{entry.type_name}</td>
                <td>{entry.status}</td>
                <td>
                  <button onClick={() => handleReview(entry.raw_data_id)} aria-label={`Review ${entry.source_file_name}`}>Review</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default FileList;
