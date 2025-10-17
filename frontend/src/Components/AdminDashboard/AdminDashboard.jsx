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
  const [analytics, setAnalytics] = useState({});
  const [activeTab, setActiveTab] = useState("overview");

  // Modal states
  const [showStudentModal, setShowStudentModal] = useState(false);
  const [showTeacherModal, setShowTeacherModal] = useState(false);
  
  // Search state
  const [userSearchQuery, setUserSearchQuery] = useState("");

  // Form states
  const [studentForm, setStudentForm] = useState({
    // Authentication table fields
    email: "",
    password: "",
    role: "student",
    full_name: "",

    // Students data table fields
    name: "",
    dob_ad: "",
    dob_bs: "",
    gender: "",
    phone: "",
    perm_address: "",
    temp_address: "",
    program: "",
    batch: "",
    section: "",
    year_semester: "",
    roll_no: "",
    symbol_no: "",
    registration_no: "",
    joined_date: "",
  });

  const [teacherForm, setTeacherForm] = useState({
    // Authentication table fields
    email: "",
    password: "",
    role: "teacher",
    full_name: "",

    // Teachers data table fields
    name: "",
    designation: "",
    phone: "",
    address: "",
    degree: "",
    subject: "",
  });

  const adminEmail = localStorage.getItem("adminEmail") || "Admin";

  // ----------------- API Base URL -----------------
  const API_BASE = "http://localhost:5000";

  // ----------------- Fetch Functions -----------------
  const fetchStats = async () => {
    try {
      console.log("📊 Fetching stats...");
      const res = await fetch(`${API_BASE}/admin/stats`);
      if (!res.ok) throw new Error("Stats API failed");
      const data = await res.json();
      console.log("📊 Stats received:", data);
      setStats(data);
    } catch (err) {
    console.error("❌ Stats fetch error:", err);
    setError(err.message);
    // Set default values on error
    setStats({
      totalStudents: 0,
      totalTeachers: 0,
      totalQueries: 0,
      activeUsers: 0,
      totalDocuments: 0,
      successRate: 0
    });
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/documents`);
      if (!res.ok) throw new Error("Documents API failed");
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  const fetchQueries = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/queries`);
      if (!res.ok) throw new Error("Queries API failed");
      const data = await res.json();
      setQueries(data.queries || []);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  const fetchStudents = async () => {
    try {
      console.log("👥 Fetching students...");
      const res = await fetch(`${API_BASE}/admin/students`);
      if (!res.ok) throw new Error("Students API failed");
      const data = await res.json();
      console.log("👥 Students received:", data.students?.length || 0);
      setStudents(data.students || []);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  const fetchTeachers = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/teachers`);
      if (!res.ok) throw new Error("Teachers API failed");
      const data = await res.json();
      setTeachers(data.teachers || []);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/analytics`);
      if (!res.ok) throw new Error("Analytics API failed");
      const data = await res.json();
      setAnalytics(data);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  };

  const fetchDataForTab = (tab) => {
    switch (tab) {
      case "overview":
        fetchStats();
        fetchAnalytics();
        break;
      case "documents":
        fetchDocuments();
        break;
      case "queries":
        fetchQueries();
        break;
      case "users":
        fetchStudents();
        fetchTeachers();
        break;
      default:
        break;
    }
  };

  // ----------------- Lifecycle -----------------
  useEffect(() => {
    fetchStats();
    fetchAnalytics();
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchDataForTab(activeTab);
  }, [activeTab]);

  // ----------------- Handlers -----------------
  const handleLogout = () => {
    localStorage.removeItem("userRole");
    localStorage.removeItem("adminEmail");
    localStorage.removeItem("isAuthenticated");
    navigate("/login");
  };

  // Filter users based on search query
  const filteredStudents = students.filter((student) =>
    student.name.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
    student.email.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
    (student.roll_no && student.roll_no.toLowerCase().includes(userSearchQuery.toLowerCase()))
  );

  const filteredTeachers = teachers.filter((teacher) =>
    teacher.name.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
    teacher.email.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
    (teacher.designation && teacher.designation.toLowerCase().includes(userSearchQuery.toLowerCase()))
  );

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith(".md")) {
      alert("Please upload only .md files");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/admin/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      const data = await res.json();
      alert(`Document uploaded: ${data.message || "Success"}`);
      fetchDocuments();
    } catch (err) {
      alert("Upload failed: " + err.message);
    }
  };

  const deleteDocument = async (filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/admin/documents/${filename}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Delete failed");

      alert("Document deleted successfully");
      fetchDocuments();
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  };

  const reprocessDocument = async (filename) => {
    try {
      const res = await fetch(
        `${API_BASE}/admin/documents/${filename}/reprocess`,
        {
          method: "POST",
        }
      );

      if (!res.ok) throw new Error("Reprocess failed");

      alert("Reprocessing started");
      fetchDocuments();
    } catch (err) {
      alert("Reprocess failed: " + err.message);
    }
  };

  // ----------------- Student Management -----------------
  const handleAddStudent = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/admin/students`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(studentForm),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to add student");
      }

      const data = await res.json();
      alert("Student added successfully! They can now login.");

      // Reset form and close modal
      setStudentForm({
        email: "",
        password: "",
        role: "student",
        full_name: "",
        name: "",
        dob_ad: "",
        dob_bs: "",
        gender: "",
        phone: "",
        perm_address: "",
        temp_address: "",
        program: "",
        batch: "",
        section: "",
        year_semester: "",
        roll_no: "",
        symbol_no: "",
        registration_no: "",
        joined_date: "",
      });
      setShowStudentModal(false);
      fetchStudents();
      fetchStats(); // Refresh stats
    } catch (err) {
      alert("Failed to add student: " + err.message);
    }
  };

  // ----------------- Teacher Management -----------------
  const handleAddTeacher = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/admin/teachers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(teacherForm),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to add teacher");
      }

      const data = await res.json();
      alert("Teacher added successfully! They can now login.");

      // Reset form and close modal
      setTeacherForm({
        email: "",
        password: "",
        role: "teacher",
        full_name: "",
        name: "",
        designation: "",
        phone: "",
        address: "",
        degree: "",
        subject: "",
      });
      setShowTeacherModal(false);
      fetchTeachers();
      fetchStats(); // Refresh stats
    } catch (err) {
      alert("Failed to add teacher: " + err.message);
    }
  };

  const handleDeleteStudent = async (id) => {
    if (!window.confirm("Delete this student?")) return;
    try {
      const res = await fetch(`${API_BASE}/admin/students/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Failed to delete student");

      alert("Student deleted successfully");
      fetchStudents();
    } catch (err) {
      alert("Failed to delete student: " + err.message);
    }
  };

  const handleDeleteTeacher = async (id) => {
    if (!window.confirm("Delete this teacher?")) return;
    try {
      const res = await fetch(`${API_BASE}/admin/teachers/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Failed to delete teacher");

      alert("Teacher deleted successfully");
      fetchTeachers();
    } catch (err) {
      alert("Failed to delete teacher: " + err.message);
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

  // ----------------- Modal Components -----------------
  const StudentModal = () => (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Add New Student</h3>
          <button
            className="close-btn"
            onClick={() => setShowStudentModal(false)}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleAddStudent} className="modal-form">
          <div className="form-section">
            <h4>Login Information</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Full Name *</label>
                <input
                  type="text"
                  value={studentForm.full_name}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      full_name: e.target.value,
                    })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={studentForm.email}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, email: e.target.value })
                  }
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Password *</label>
                <input
                  type="password"
                  value={studentForm.password}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, password: e.target.value })
                  }
                  required
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h4>Personal Information</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Name (as in records) *</label>
                <input
                  type="text"
                  value={studentForm.name}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Gender</label>
                <select
                  value={studentForm.gender}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, gender: e.target.value })
                  }
                >
                  <option value="">Select Gender</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>DOB (A.D.)</label>
                <input
                  type="date"
                  value={studentForm.dob_ad}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, dob_ad: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>DOB (B.S.)</label>
                <input
                  type="text"
                  placeholder="YYYY-MM-DD"
                  value={studentForm.dob_bs}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, dob_bs: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Phone</label>
                <input
                  type="tel"
                  value={studentForm.phone}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, phone: e.target.value })
                  }
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h4>Address Information</h4>
            <div className="form-row">
              <div className="form-group full-width">
                <label>Permanent Address</label>
                <textarea
                  value={studentForm.perm_address}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      perm_address: e.target.value,
                    })
                  }
                  rows="3"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group full-width">
                <label>Temporary Address</label>
                <textarea
                  value={studentForm.temp_address}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      temp_address: e.target.value,
                    })
                  }
                  rows="3"
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h4>Academic Information</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Program *</label>
                <input
                  type="text"
                  value={studentForm.program}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, program: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Batch</label>
                <input
                  type="text"
                  value={studentForm.batch}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, batch: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Section</label>
                <input
                  type="text"
                  value={studentForm.section}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, section: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Year/Semester</label>
                <input
                  type="text"
                  value={studentForm.year_semester}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      year_semester: e.target.value,
                    })
                  }
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Roll No. *</label>
                <input
                  type="text"
                  value={studentForm.roll_no}
                  onChange={(e) =>
                    setStudentForm({ ...studentForm, roll_no: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Symbol No.</label>
                <input
                  type="text"
                  value={studentForm.symbol_no}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      symbol_no: e.target.value,
                    })
                  }
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Registration No.</label>
                <input
                  type="text"
                  value={studentForm.registration_no}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      registration_no: e.target.value,
                    })
                  }
                />
              </div>
              <div className="form-group">
                <label>Joined Date</label>
                <input
                  type="date"
                  value={studentForm.joined_date}
                  onChange={(e) =>
                    setStudentForm({
                      ...studentForm,
                      joined_date: e.target.value,
                    })
                  }
                />
              </div>
            </div>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowStudentModal(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Add Student
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  const TeacherModal = () => (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Add New Teacher</h3>
          <button
            className="close-btn"
            onClick={() => setShowTeacherModal(false)}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleAddTeacher} className="modal-form">
          <div className="form-section">
            <h4>Login Information</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Full Name *</label>
                <input
                  type="text"
                  value={teacherForm.full_name}
                  onChange={(e) =>
                    setTeacherForm({
                      ...teacherForm,
                      full_name: e.target.value,
                    })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={teacherForm.email}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, email: e.target.value })
                  }
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Password *</label>
                <input
                  type="password"
                  value={teacherForm.password}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, password: e.target.value })
                  }
                  required
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h4>Professional Information</h4>
            <div className="form-row">
              <div className="form-group">
                <label>Name (as in records) *</label>
                <input
                  type="text"
                  value={teacherForm.name}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Designation *</label>
                <input
                  type="text"
                  value={teacherForm.designation}
                  onChange={(e) =>
                    setTeacherForm({
                      ...teacherForm,
                      designation: e.target.value,
                    })
                  }
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Phone</label>
                <input
                  type="tel"
                  value={teacherForm.phone}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, phone: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Subject *</label>
                <input
                  type="text"
                  value={teacherForm.subject}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, subject: e.target.value })
                  }
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group full-width">
                <label>Address</label>
                <textarea
                  value={teacherForm.address}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, address: e.target.value })
                  }
                  rows="3"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group full-width">
                <label>Degree/Qualification</label>
                <input
                  type="text"
                  value={teacherForm.degree}
                  onChange={(e) =>
                    setTeacherForm({ ...teacherForm, degree: e.target.value })
                  }
                />
              </div>
            </div>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowTeacherModal(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Add Teacher
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  // ----------------- JSX -----------------
 return (
    <div className="admin-container">
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

      <nav className="admin-nav">
        <div className="nav-content">
          {["overview", "documents", "queries", "users"].map((tab) => (
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

      <main className="admin-content">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="overview-tab">
            <div className="stats-grid">
              <div className="stat-card">
                <h3>{stats.totalStudents || 0}</h3>
                <p>Total Students</p>
              </div>
              <div className="stat-card">
                <h3>{stats.totalTeachers || 0}</h3>
                <p>Total Teachers</p>
              </div>
              <div className="stat-card">
                <h3>{stats.totalQueries || 0}</h3>
                <p>Total Queries</p>
              </div>
              <div className="stat-card">
                <h3>{stats.activeUsers || 0}</h3>
                <p>Active Users</p>
              </div>
              <div className="stat-card">
                <h3>{stats.totalDocuments || 0}</h3>
                <p>Total Documents</p>
              </div>
              <div className="stat-card">
                <h3>{stats.successRate || 0}%</h3>
                <p>Success Rate</p>
              </div>
            </div>

            {/* Analytics Section */}
            <div className="analytics-section">
              <h2>Weekly Query Trends</h2>
              <div className="chart-container">
                {analytics.weeklyTrend && analytics.weeklyTrend.length > 0 ? (
                  <div className="bar-chart">
                    {analytics.weeklyTrend.map((day, index) => (
                      <div key={index} className="bar-item">
                        <div className="bar-label">{day.date}</div>
                        <div 
                          className="bar" 
                          style={{ height: `${Math.max(day.queries * 10, 20)}px` }}
                          title={`${day.queries} queries`}
                        ></div>
                        <div className="bar-value">{day.queries}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>No analytics data available</p>
                )}
                <div className="chart-footer">
                  <p>Total this week: {analytics.totalThisWeek || 0} queries</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === "documents" && (
          <div className="documents-tab">
            <div className="tab-header">
              <h2>Document Management</h2>
              <div className="upload-section">
                <input 
                  type="file" 
                  id="file-upload" 
                  accept=".md" 
                  onChange={handleFileUpload} 
                  style={{ display: "none" }} 
                />
                <label htmlFor="file-upload" className="upload-btn">
                  Upload Document (.md)
                </label>
                <span className="upload-hint">Only .md files are supported</span>
              </div>
            </div>

            {documents.length === 0 ? (
              <div className="empty-state">
                <p>No documents uploaded yet</p>
                <p>Upload .md files to get started</p>
              </div>
            ) : (
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
                      <td className="doc-name">{doc.name}</td>
                      <td>{doc.size}</td>
                      <td>{doc.chunks}</td>
                      <td>{doc.lastModified}</td>
                      <td>
                        <span className={`status-badge ${doc.status}`}>
                          {doc.status}
                        </span>
                      </td>
                      <td className="actions">
                        <button 
                          className="action-btn reprocess" 
                          onClick={() => reprocessDocument(doc.name)}
                        >
                          Reprocess
                        </button>
                        <button 
                          className="action-btn delete" 
                          onClick={() => deleteDocument(doc.name)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Queries Tab */}
        {activeTab === "queries" && (
          <div className="queries-tab">
            <h2>Query Logs</h2>
            {queries.length === 0 ? (
              <div className="empty-state">
                <p>No queries recorded yet</p>
              </div>
            ) : (
              <table className="queries-table">
                <thead>
                  <tr>
                    <th>Query</th>
                    <th>User</th>
                    <th>Role</th>
                    <th>Timestamp</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {queries.map((q) => (
                    <tr key={q.id}>
                      <td className="query-text" title={q.query}>
                        {q.query}
                      </td>
                      <td>{q.user_email || 'Unknown'}</td>
                      <td>
                        <span className={`role-badge ${q.user_role}`}>
                          {q.user_role}
                        </span>
                      </td>
                      <td>{new Date(q.timestamp).toLocaleString()}</td>
                      <td>
                        <span className={`status-badge ${q.status}`}>
                          {q.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Users Management Tab */}
        {activeTab === "users" && (
          <div className="users-tab">
            <div className="users-header">
              <h2>User Management</h2>
              
              <div className="user-actions">
                <button 
                  className="btn-primary large"
                  onClick={() => setShowStudentModal(true)}
                >
                  + Add Student
                </button>
                <button 
                  className="btn-secondary large"
                  onClick={() => setShowTeacherModal(true)}
                >
                  + Add Teacher
                </button>
              </div>
            </div>

            {/* Search Bar */}
            <div className="search-container">
              <input
                type="text"
                className="search-input"
                placeholder="Search users by name, email, roll no, or designation..."
                value={userSearchQuery}
                onChange={(e) => setUserSearchQuery(e.target.value)}
              />
              {userSearchQuery && (
                <button 
                  className="clear-search"
                  onClick={() => setUserSearchQuery("")}
                  title="Clear search"
                >
                  ×
                </button>
              )}
            </div>

            <div className="users-grid">
              {/* Students List */}
              <div className="users-section">
                <h3>Students ({filteredStudents.length})</h3>
                {filteredStudents.length === 0 ? (
                  <div className="empty-state small">
                    <p>{userSearchQuery ? "No students found matching your search" : "No students found"}</p>
                  </div>
                ) : (
                  <div className="users-list">
                    {filteredStudents.map((student) => (
                      <div key={student.id} className="user-card">
                        <div className="user-info">
                          <h4>{student.name}</h4>
                          <p><strong>Email:</strong> {student.email}</p>
                          <p><strong>Roll No:</strong> {student.roll_no}</p>
                          <p><strong>Program:</strong> {student.program}</p>
                          <p><strong>Batch:</strong> {student.batch}</p>
                        </div>
                        <button 
                          className="btn-danger"
                          onClick={() => handleDeleteStudent(student.id)}
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Teachers List */}
              <div className="users-section">
                <h3>Teachers ({filteredTeachers.length})</h3>
                {filteredTeachers.length === 0 ? (
                  <div className="empty-state small">
                    <p>{userSearchQuery ? "No teachers found matching your search" : "No teachers found"}</p>
                  </div>
                ) : (
                  <div className="users-list">
                    {filteredTeachers.map((teacher) => (
                      <div key={teacher.id} className="user-card">
                        <div className="user-info">
                          <h4>{teacher.name}</h4>
                          <p><strong>Email:</strong> {teacher.email}</p>
                          <p><strong>Designation:</strong> {teacher.designation}</p>
                          
                        </div>
                        <button 
                          className="btn-danger"
                          onClick={() => handleDeleteTeacher(teacher.id)}
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      {showStudentModal && <StudentModal />}
      {showTeacherModal && <TeacherModal />}
    </div>
  );
};

export default AdminDashboard;