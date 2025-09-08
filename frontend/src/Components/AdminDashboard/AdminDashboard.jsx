import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./AdminDashboard.css";

const AdminDashboard = () => {
  const navigate = useNavigate();

  // ----------------- State -----------------
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({});
  const [documents, setDocuments] = useState([]);
  const [queries, setQueries] = useState([]);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");

  const adminEmail = localStorage.getItem("adminEmail") || "Admin";

  // ----------------- Fetch Admin Data -----------------
  const fetchAdminData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [statsRes, docsRes, queriesRes, studentsRes, teachersRes] = await Promise.all([
        fetch("http://localhost:5000/admin/stats"),
        fetch("http://localhost:5000/admin/documents"),
        fetch("http://localhost:5000/admin/queries"),
        fetch("http://localhost:5000/admin/students"),
        fetch("http://localhost:5000/admin/teachers"),
      ]);

      if (!statsRes.ok) throw new Error("Stats API failed");
      if (!docsRes.ok) throw new Error("Documents API failed");
      if (!queriesRes.ok) throw new Error("Queries API failed");
      if (!studentsRes.ok) throw new Error("Students API failed");
      if (!teachersRes.ok) throw new Error("Teachers API failed");

      const statsData = await statsRes.json();
      const documentsData = await docsRes.json();
      const queriesData = await queriesRes.json();
      const studentsData = await studentsRes.json();
      const teachersData = await teachersRes.json();

      setStats(statsData);
      setDocuments(documentsData.documents || []);
      setQueries(queriesData.queries || []);
      setStudents(studentsData.students || []);
      setTeachers(teachersData.teachers || []);
    } catch (err) {
      console.error(err);
      setError(err.message);
      alert(`Fetch error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // ----------------- Lifecycle -----------------
  useEffect(() => {
    fetchAdminData();
    const interval = setInterval(fetchAdminData, 30000);
    return () => clearInterval(interval);
  }, []);

  // ----------------- Handlers -----------------
  const handleLogout = () => {
    localStorage.removeItem("userRole");
    localStorage.removeItem("adminEmail");
    localStorage.removeItem("isAuthenticated");
    navigate("/login");
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:5000/admin/documents/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      alert(`Document uploaded: ${data.message || "Success"}`);
      fetchAdminData();
    } catch (err) {
      alert("Upload failed");
    }
  };

  const deleteDocument = async (filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;
    try {
      await fetch(`http://localhost:5000/admin/documents/${filename}`, {
        method: "DELETE",
      });
      fetchAdminData();
    } catch (err) {
      alert("Delete failed");
    }
  };

  const reprocessDocument = async (filename) => {
    try {
      // This route is optional, currently not implemented in server.py
      await fetch(`http://localhost:5000/admin/documents/${filename}/reprocess`, { method: "POST" });
      alert("Reprocessing started");
      fetchAdminData();
    } catch (err) {
      alert("Reprocess failed");
    }
  };

  // ----------------- Loading -----------------
  if (loading)
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading admin dashboard...</p>
      </div>
    );

  // ----------------- JSX -----------------
  return (
    <div className="admin-container">
      {/* Header */}
      <header className="admin-header">
        <div className="header-content">
          <h1>Samriddhi Admin Dashboard</h1>
          <div className="header-right">
            <span className="admin-email">Welcome, {adminEmail}</span>
            <button className="logout-btn" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="admin-nav">
        <div className="nav-content">
          {["overview", "documents", "queries", "settings"].map((tab) => (
            <button
              key={tab}
              className={`nav-tab ${activeTab === tab ? "active" : ""}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="admin-content">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="overview-tab">
            <div className="stats-grid">
              <div className="stat-card">
                <h3>{stats.totalStudents}</h3>
                <p>Total Students</p>
              </div>
              <div className="stat-card">
                <h3>{stats.totalTeachers}</h3>
                <p>Total Teachers</p>
              </div>
              <div className="stat-card">
                <h3>{stats.totalQueries}</h3>
                <p>Total Queries</p>
              </div>
              <div className="stat-card">
                <h3>{stats.activeUsers}</h3>
                <p>Active Users</p>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === "documents" && (
          <div className="documents-tab">
            <div className="tab-header">
              <h2>Document Management</h2>
              <input
                type="file"
                id="file-upload"
                accept=".md"
                onChange={handleFileUpload}
                style={{ display: "none" }}
              />
              <label htmlFor="file-upload" className="upload-btn">
                Upload Document
              </label>
            </div>

            <table className="documents-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Size</th>
                  <th>Chunks</th>
                  <th>Last Modified</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>{doc.name}</td>
                    <td>{doc.size}</td>
                    <td>{doc.chunks}</td>
                    <td>{doc.lastModified}</td>
                    <td>
                      <span className={`status-badge ${doc.status}`}>{doc.status}</span>
                    </td>
                    <td>
                      <button onClick={() => reprocessDocument(doc.name)}>Reprocess</button>
                      <button onClick={() => deleteDocument(doc.name)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Queries Tab */}
        {activeTab === "queries" && (
          <div className="queries-tab">
            <h2>Query Logs</h2>
            <table className="queries-table">
              <thead>
                <tr>
                  <th>Query</th>
                  <th>Timestamp</th>
                  <th>Response Time</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {queries.map((q) => (
                  <tr key={q.id}>
                    <td>{q.query}</td>
                    <td>{q.timestamp}</td>
                    <td>{q.response_time}</td>
                    <td>
                      <span className={`status-badge ${q.status}`}>{q.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === "settings" && (
          <div className="settings-tab">
            <h2>Users</h2>
            <div className="settings-section">
              <h3>Students</h3>
              <ul>
                {students.map((s) => (
                  <li key={s.id}>
                    {s.name} ({s.roll})
                  </li>
                ))}
              </ul>
              <h3>Teachers</h3>
              <ul>
                {teachers.map((t) => (
                  <li key={t.id}>
                    {t.name} ({t.department})
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminDashboard;
