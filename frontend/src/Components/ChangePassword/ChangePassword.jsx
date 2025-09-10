// src/Components/ChangePassword/ChangePassword.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { updatePassword } from "firebase/auth";
import { auth, db } from "../../firebase/firebase";
import { doc, updateDoc } from "firebase/firestore";

const ChangePassword = () => {
  const [newPassword, setNewPassword] = useState("");
  const navigate = useNavigate();

  const handlePasswordChange = async () => {
    try {
      const user = auth.currentUser;
      if (!user) {
        toast.error("No authenticated user found.");
        return;
      }

      // Update Firebase Auth password
      await updatePassword(user, newPassword);

      // Mark in Firestore that password change is complete
      await updateDoc(doc(db, "users", user.uid), {
        forcePasswordChange: false,
      });

      toast.success("Password changed successfully!");
      navigate("/chat");
    } catch (error) {
      console.error(error.message);
      toast.error("Failed to change password. Try again.");
    }
  };

  return (
    <div className="login-container">
      <div className="form-section">
        <h2>Change Your Password</h2>
        <input
          type="password"
          placeholder="Enter new password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="login-input"
        />
        <button onClick={handlePasswordChange}>Update Password</button>
      </div>
    </div>
  );
};

export default ChangePassword;
