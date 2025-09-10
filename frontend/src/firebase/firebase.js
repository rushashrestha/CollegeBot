import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyASRH9QcBt8y1xlzU3a-OK3EJKO_RZ1Z6E",
  authDomain: "chatbot-35d5d.firebaseapp.com",
  projectId: "chatbot-35d5d",
  storageBucket: "chatbot-35d5d.firebasestorage.app",
  messagingSenderId: "441349684399",
  appId: "1:441349684399:web:555221144cdbdbfde0685a",
  measurementId: "G-Z03YGZZ21D"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

export { app, auth, db };
