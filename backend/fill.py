import random
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("VITE_SUPABASE_ANON_KEY"))

def generate_performance_data():
    """Generate realistic performance data for all students"""
    
    # Fetch all students
    students = supabase.table("students_data").select("id, program, year_semester").execute()
    
    for student in students.data:
        # Extract semester number from year_semester (e.g., "Semester 3" -> 3)
        semester_num = 1
        if student.get('year_semester'):
            import re
            match = re.search(r'\d+', student['year_semester'])
            if match:
                semester_num = int(match.group())
        
        # Calculate credits based on semester (typical: 18-24 credits per semester)
        credits_per_semester = random.randint(18, 24)
        total_credits = (semester_num - 1) * credits_per_semester + random.randint(12, credits_per_semester)
        
        # Program total credits (CSIT/BCA = 126, BSW/BBS = 120)
        total_program_credits = 126 if student['program'] in ['CSIT', 'BCA'] else 120
        credits_remaining = max(0, total_program_credits - total_credits)
        
        # Generate GPA (realistic distribution)
        # 70% students: 2.5-3.5, 20%: 3.5-4.0, 10%: 2.0-2.5
        rand = random.random()
        if rand < 0.70:
            cgpa = round(random.uniform(2.5, 3.5), 2)
        elif rand < 0.90:
            cgpa = round(random.uniform(3.5, 4.0), 2)
        else:
            cgpa = round(random.uniform(2.0, 2.5), 2)
        
        # Current semester GPA varies ±0.3 from CGPA
        current_semester_gpa = round(cgpa + random.uniform(-0.3, 0.3), 2)
        current_semester_gpa = max(0, min(4.0, current_semester_gpa))
        
        # Overall GPA same as CGPA for simplicity
        gpa = cgpa
        
        # Attendance (realistic distribution)
        # 60% students: 75-90%, 30%: 60-75%, 10%: <60%
        rand = random.random()
        if rand < 0.60:
            attendance = round(random.uniform(75, 90), 2)
        elif rand < 0.90:
            attendance = round(random.uniform(60, 75), 2)
        else:
            attendance = round(random.uniform(40, 60), 2)
        
        # Academic status based on CGPA and attendance
        if cgpa >= 3.0 and attendance >= 75:
            academic_status = "Good Standing"
        elif cgpa >= 2.5 and attendance >= 60:
            academic_status = "Satisfactory"
        elif cgpa >= 2.0 or attendance >= 50:
            academic_status = "Warning"
        else:
            academic_status = "Probation"
        
        # Update student record
        supabase.table("students_data").update({
            "gpa": gpa,
            "cgpa": cgpa,
            "current_semester_gpa": current_semester_gpa,
            "total_credits_earned": total_credits,
            "attendance_percentage": attendance,
            "academic_status": academic_status,
            "credits_remaining": credits_remaining,
            "last_performance_update": "now()"
        }).eq("id", student['id']).execute()
        
        print(f"✅ Updated student ID {student['id']}: CGPA={cgpa}, Attendance={attendance}%")

if __name__ == "__main__":
    print("🚀 Generating performance data for all students...")
    generate_performance_data()
    print("✨ Done!")