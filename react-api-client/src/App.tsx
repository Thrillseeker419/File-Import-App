import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import UploadAndDisplayPDF from "./components/UploadAndDisplayPDF";
import ReviewPage from "./components/ReviewPage"; 
import EditPage from "./components/EditPage";
import FileList from "./components/FileList"; 

const App: React.FC = () => {
  return (
    <Router>
      <nav>
        <ul>
          <li>
            <Link to="/">Home</Link>
          </li>
          <li>
            <Link to="/upload">Upload PDF</Link>
          </li>
          <li>
            <Link to="/review-list">Review</Link> 
          </li>
        </ul>
      </nav>

      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/upload" element={<UploadAndDisplayPDF />} />
          <Route path="/review-list" element={<FileList />} /> 
          <Route path="/review/:raw_data_id" element={<ReviewPage />} />
          <Route path="/edit/:temp_discharge_id" element={<EditPage />} />
        </Routes>
      </div>
    </Router>
  );
};

// Simple home page
const Home: React.FC = () => {
  return (
    <div>
      <h1>Welcome to the PDF Processor App</h1>
      <p>
        Navigate to the <Link to="/upload">Upload PDF</Link> page to start processing PDFs.
      </p>
    </div>
  );
};

export default App;
