const admin = require('firebase-admin');
const XLSX = require('xlsx');
const fs = require('fs');

// Initialize Firebase Admin SDK
const serviceAccount = require('./serviceAccountKey.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  // Replace with your actual project ID
  projectId: 'chatbot-35d5d'
});

const auth = admin.auth();
const db = admin.firestore();

// Function to generate password if not provided
function generatePassword(length = 10) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
  let password = '';
  for (let i = 0; i < length; i++) {
    password += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return password;
}

// Function to clean and format data - handles undefined/null values
function cleanData(obj) {
  const cleaned = {};
  for (let key in obj) {
    if (obj[key] !== undefined && obj[key] !== null && obj[key] !== '') {
      // Clean key name (remove special characters, spaces)
      const cleanKey = key.trim().replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
      const value = typeof obj[key] === 'string' ? obj[key].trim() : obj[key];
      // Only add non-empty values
      if (value !== '' && value !== 'undefined' && value !== 'null') {
        cleaned[cleanKey] = value;
      }
    }
  }
  return cleaned;
}

// Updated email validation - more flexible for names with multiple parts
function validateEmail(email, role) {
  // Allow multiple parts in names (like manohar.kumar.bhattarai@samriddhi.com)
  const studentPattern = /^[a-zA-Z]+(\.[a-zA-Z]+)*@samriddhi\.edu\.np$/;
  const teacherPattern = /^[a-zA-Z]+(\.[a-zA-Z]+)*@samriddhi\.com$/;
  
  if (role === 'student') {
    return studentPattern.test(email);
  } else if (role === 'teacher') {
    return teacherPattern.test(email);
  }
  return false;
}

// Helper function to safely get field value
function safeGet(obj, field, defaultValue = '') {
  const value = obj[field];
  if (value === undefined || value === null || value === '' || 
      value === 'undefined' || value === 'null' || value === 'N/A') {
    return defaultValue;
  }
  return typeof value === 'string' ? value.trim() : value;
}

// Create students
async function createStudents(studentsData) {
  console.log('\n=== Creating Students ===');
  const results = { success: 0, failed: 0, errors: [] };
  
  for (let i = 0; i < studentsData.length; i++) {
    const student = studentsData[i];
    
    try {
      // Get email and validate
      const email = safeGet(student, 'Email') || safeGet(student, 'email');
      if (!email) {
        throw new Error('Email is required');
      }
      
      if (!validateEmail(email, 'student')) {
        throw new Error('Invalid student email format. Should be: name.surname@samriddhi.edu.np');
      }
      
      // Get password or generate one
      const password = safeGet(student, 'Password') || safeGet(student, 'password') || generatePassword();
      
      // Create user in Firebase Auth
      const userRecord = await auth.createUser({
        email: email,
        password: password,
        displayName: safeGet(student, 'Name') || safeGet(student, 'name'),
        emailVerified: false
      });
      
      // Prepare student data for Firestore - handle all possible undefined values
      const studentData = {
        // Authentication data
        email: email,
        role: 'student',
        mustChangePassword: true,
        tempPassword: password,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
        lastLogin: null,
        
        // Personal Information
        id: safeGet(student, 'ID') || safeGet(student, 'id'),
        name: safeGet(student, 'Name') || safeGet(student, 'name'),
        dobAD: safeGet(student, 'DOB (A.D.)') || safeGet(student, 'dob_ad'),
        dobBS: safeGet(student, 'DOB (B.S.)') || safeGet(student, 'dob_bs'),
        gender: safeGet(student, 'Gender') || safeGet(student, 'gender'),
        phone: safeGet(student, 'Phone') || safeGet(student, 'phone'),
        
        // Address Information
        permanentAddress: safeGet(student, 'Perm. Address') || safeGet(student, 'permanent_address'),
        temporaryAddress: safeGet(student, 'Temp. Address') || safeGet(student, 'temporary_address'),
        
        // Academic Information
        program: safeGet(student, 'Program') || safeGet(student, 'program'),
        batch: safeGet(student, 'Batch') || safeGet(student, 'batch'),
        section: safeGet(student, 'Section') || safeGet(student, 'section'),
        yearSemester: safeGet(student, 'Year/Semester') || safeGet(student, 'year_semester'),
        rollNo: safeGet(student, 'Roll No.') || safeGet(student, 'roll_no'),
        symbolNo: safeGet(student, 'Symbol No.') || safeGet(student, 'symbol_no'),
        registrationNo: safeGet(student, 'Registration No.') || safeGet(student, 'registration_no'),
        joinedDate: safeGet(student, 'Joined Date') || safeGet(student, 'joined_date')
      };
      
      // Create searchable text (only from non-empty values)
      const searchableFields = [
        studentData.name, studentData.program, studentData.batch, 
        studentData.section, studentData.rollNo
      ].filter(field => field && field !== '');
      
      studentData.searchableText = searchableFields.join(' ').toLowerCase();
      
      // Store in Firestore users collection
      await db.collection('users').doc(userRecord.uid).set({
        email: studentData.email,
        name: studentData.name,
        role: 'student',
        mustChangePassword: true,
        createdAt: studentData.createdAt,
        lastLogin: null
      });
      
      // Store detailed student data in separate collection
      await db.collection('students').doc(userRecord.uid).set(studentData);
      
      console.log(`✅ Student created: ${email} (Password: ${password})`);
      results.success++;
      
    } catch (error) {
      console.error(`❌ Error creating student ${safeGet(student, 'Email') || safeGet(student, 'email') || 'unknown'}:`, error.message);
      results.failed++;
      results.errors.push({
        email: safeGet(student, 'Email') || safeGet(student, 'email') || 'unknown',
        error: error.message
      });
    }
  }
  
  return results;
}

// Create teachers/staff - Fixed to handle undefined values
async function createTeachers(teachersData) {
  console.log('\n=== Creating Teachers/Staff ===');
  const results = { success: 0, failed: 0, errors: [] };
  
  for (let i = 0; i < teachersData.length; i++) {
    const teacher = teachersData[i];
    
    try {
      // Get email and validate
      const email = safeGet(teacher, 'Email') || safeGet(teacher, 'email');
      if (!email) {
        throw new Error('Email is required');
      }
      
      if (!validateEmail(email, 'teacher')) {
        throw new Error(`Invalid teacher email format: ${email}. Should be: name.surname@samriddhi.com (names can have multiple parts)`);
      }
      
      // Get password or generate one
      const password = safeGet(teacher, 'Password') || safeGet(teacher, 'password') || generatePassword();
      
      // Create user in Firebase Auth
      const userRecord = await auth.createUser({
        email: email,
        password: password,
        displayName: safeGet(teacher, 'Name') || safeGet(teacher, 'name'),
        emailVerified: false
      });
      
      // Prepare teacher data for Firestore - handle all undefined values
      const teacherData = {
        // Authentication data
        email: email,
        role: 'teacher',
        mustChangePassword: true,
        tempPassword: password,
        createdAt: admin.firestore.FieldValue.serverTimestamp(),
        lastLogin: null,
        
        // Professional Information - use empty string instead of undefined
        name: safeGet(teacher, 'Name') || safeGet(teacher, 'name'),
        designation: safeGet(teacher, 'Designation') || safeGet(teacher, 'designation'),
        phone: safeGet(teacher, 'Phone') || safeGet(teacher, 'phone'),
        address: safeGet(teacher, 'Address') || safeGet(teacher, 'address'),
        degree: safeGet(teacher, 'Degree') || safeGet(teacher, 'degree'),
        subject: safeGet(teacher, 'Subject') || safeGet(teacher, 'subject') || 'General', // Default to 'General' if no subject
        
        // Permissions
        canAccessAllStudents: true,
        canModifyStudentData: true
      };
      
      // Create searchable text (only from non-empty values)
      const searchableFields = [
        teacherData.name, teacherData.designation, 
        teacherData.subject, teacherData.degree
      ].filter(field => field && field !== '' && field !== 'General');
      
      teacherData.searchableText = searchableFields.join(' ').toLowerCase();
      
      // Store in Firestore users collection
      await db.collection('users').doc(userRecord.uid).set({
        email: teacherData.email,
        name: teacherData.name,
        role: 'teacher',
        mustChangePassword: true,
        createdAt: teacherData.createdAt,
        lastLogin: null
      });
      
      // Store detailed teacher data in separate collection
      await db.collection('teachers').doc(userRecord.uid).set(teacherData);
      
      console.log(`✅ Teacher created: ${email} (Password: ${password})`);
      results.success++;
      
    } catch (error) {
      console.error(`❌ Error creating teacher ${safeGet(teacher, 'Email') || safeGet(teacher, 'email') || 'unknown'}:`, error.message);
      results.failed++;
      results.errors.push({
        email: safeGet(teacher, 'Email') || safeGet(teacher, 'email') || 'unknown',
        error: error.message
      });
    }
  }
  
  return results;
}

// Main bulk creation function
async function createBulkUsers(excelFilePath) {
  try {
    console.log('Reading Excel file...');
    
    if (!fs.existsSync(excelFilePath)) {
      throw new Error(`File not found: ${excelFilePath}`);
    }
    
    const workbook = XLSX.readFile(excelFilePath);
    console.log('Available sheets:', workbook.SheetNames);
    
    // Read both sheets - try multiple possible sheet names
    let studentsData = [];
    let teachersData = [];
    
    // Look for student data
    const studentSheetNames = ['Students', 'Student', 'students', 'student', 'Sheet1'];
    for (const sheetName of studentSheetNames) {
      if (workbook.Sheets[sheetName]) {
        studentsData = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName]);
        console.log(`Found student data in sheet: ${sheetName}`);
        break;
      }
    }
    
    // Look for teacher data
    const teacherSheetNames = ['Teachers', 'Teacher', 'Staff', 'teachers', 'staff'];
    for (const sheetName of teacherSheetNames) {
      if (workbook.Sheets[sheetName]) {
        teachersData = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName]);
        console.log(`Found teacher data in sheet: ${sheetName}`);
        break;
      }
    }
    
    console.log(`Found ${studentsData.length} students and ${teachersData.length} teachers/staff`);
    
    // Show sample data structure for debugging
    if (studentsData.length > 0) {
      console.log('\nSample student columns:', Object.keys(studentsData[0]));
    }
    if (teachersData.length > 0) {
      console.log('Sample teacher columns:', Object.keys(teachersData[0]));
    }
    
    // Create users
    const studentResults = studentsData.length > 0 ? await createStudents(studentsData) : { success: 0, failed: 0, errors: [] };
    const teacherResults = teachersData.length > 0 ? await createTeachers(teachersData) : { success: 0, failed: 0, errors: [] };
    
    // Print summary
    console.log('\n' + '='.repeat(50));
    console.log('CREATION SUMMARY');
    console.log('='.repeat(50));
    console.log(`Students - Success: ${studentResults.success}, Failed: ${studentResults.failed}`);
    console.log(`Teachers - Success: ${teacherResults.success}, Failed: ${teacherResults.failed}`);
    console.log(`Total Success: ${studentResults.success + teacherResults.success}`);
    console.log(`Total Failed: ${studentResults.failed + teacherResults.failed}`);
    
    // Print errors if any
    const allErrors = [...studentResults.errors, ...teacherResults.errors];
    if (allErrors.length > 0) {
      console.log('\nERRORS:');
      allErrors.forEach(err => {
        console.log(`❌ ${err.email}: ${err.error}`);
      });
    }
    
    console.log('\n✅ User creation completed!');
    
  } catch (error) {
    console.error('Error in bulk user creation:', error);
  }
}

// Test function to query created data
async function testDataRetrieval() {
  console.log('\n=== Testing Data Retrieval ===');
  
  try {
    // Get a sample student
    const studentsSnapshot = await db.collection('students').limit(1).get();
    if (!studentsSnapshot.empty) {
      console.log('Sample student data:');
      console.log(studentsSnapshot.docs[0].data());
    }
    
    // Get a sample teacher
    const teachersSnapshot = await db.collection('teachers').limit(1).get();
    if (!teachersSnapshot.empty) {
      console.log('\nSample teacher data:');
      console.log(teachersSnapshot.docs[0].data());
    }
    
  } catch (error) {
    console.error('Error testing data retrieval:', error);
  }
}

// Main execution
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log('Usage: node createSamriddhiUsers.js <excel-file-path> [test]');
    console.log('Example: node createSamriddhiUsers.js ./teachers.xlsx');
    console.log('Example: node createSamriddhiUsers.js ./students.xlsx');
    console.log('Add "test" to run data retrieval test: node createSamriddhiUsers.js ./teachers.xlsx test');
    return;
  }
  
  const excelFilePath = args[0];
  const shouldTest = args[1] === 'test';
  
  await createBulkUsers(excelFilePath);
  
  if (shouldTest) {
    await testDataRetrieval();
  }
  
  console.log('\nScript completed successfully!');
  process.exit(0);
}

// Run the script
main().catch(console.error);