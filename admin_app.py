import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
import string
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(page_title="نظام الإدارة - Admin", layout="wide", page_icon="🏫")

# --- دالة الاتصال بجوجل شيت ---
def get_database():
    # في حالة الرفع على Streamlit Cloud نستخدم st.secrets
    # تأكد من وضع بيانات الاعتماد في secrets.toml
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    sheet = client.open("School_System") # تأكد أن الاسم مطابق لاسم ملف الشيت
    return sheet

# --- دوال مساعدة ---
def generate_student_id():
    return random.choice(string.ascii_uppercase) + ''.join(random.choices(string.digits, k=7))

def generate_student_password():
    return ''.join(random.choices(string.ascii_letters, k=2)) + ''.join(random.choices(string.digits, k=6))

def generate_teacher_id():
    return "T-" + ''.join(random.choices(string.digits, k=5))

# --- الواجهة الرئيسية ---
st.title("🏫 لوحة تحكم الإدارة")
sheet = get_database()

menu = st.sidebar.selectbox("القائمة", ["تسجيل طالب جديد", "بحث عن طالب", "الخزينة (دفع المصاريف)", "تسجيل معلم", "إضافة مواد دراسية"])

# ----------------- 1. تسجيل طالب -----------------
if menu == "تسجيل طالب جديد":
    st.header("تسجيل طالب جديد")
    with st.form("student_reg"):
        name = st.text_input("اسم الطالب رباعي")
        phone = st.text_input("رقم الهاتف")
        total_fees = st.number_input("المصاريف الدراسية المستحقة", min_value=0)
        submitted = st.form_submit_button("تسجيل")
        
        if submitted and name:
            ws = sheet.worksheet("Students")
            existing_ids = ws.col_values(1)
            
            # توليد كود غير مكرر
            while True:
                new_id = generate_student_id()
                if new_id not in existing_ids:
                    break
            
            # البيانات: ID, Name, Phone, TotalFees, PaidFees, Password, RegDate
            row = [new_id, name, phone, total_fees, 0, "", str(datetime.now().date())]
            ws.append_row(row)
            st.success(f"تم تسجيل الطالب بنجاح! كود الطالب هو: {new_id}")

# ----------------- 2. بحث عن طالب -----------------
elif menu == "بحث عن طالب":
    st.header("البحث عن طالب")
    search_term = st.text_input("ابحث بالاسم أو الكود")
    if search_term:
        ws = sheet.worksheet("Students")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # تحويل الأرقام لنصوص للبحث
        df['StudentID'] = df['StudentID'].astype(str)
        
        results = df[df['Name'].str.contains(search_term) | df['StudentID'].str.contains(search_term)]
        if not results.empty:
            st.dataframe(results)
        else:
            st.warning("لا توجد نتائج")

# ----------------- 3. الخزينة -----------------
elif menu == "الخزينة (دفع المصاريف)":
    st.header("تحصيل المصروفات")
    st_code = st.text_input("أدخل كود الطالب للدفع")
    
    if st_code:
        ws = sheet.worksheet("Students")
        cell = ws.find(st_code)
        
        if cell:
            row_num = cell.row
            row_values = ws.row_values(row_num)
            # StudentID is col 1, Name 2, TotalFees 4, PaidFees 5
            name = row_values[1]
            total = float(row_values[3])
            paid_so_far = float(row_values[4]) if row_values[4] else 0.0
            remaining = total - paid_so_far
            
            st.info(f"الطالب: {name} | المبلغ المستحق المتبقي: {remaining}")
            
            payment = st.number_input("المبلغ المدفوع (كاش)", min_value=1.0, max_value=remaining)
            
            if st.button("تأكيد الدفع"):
                new_paid = paid_so_far + payment
                
                # تحديث المبلغ المدفوع
                ws.update_cell(row_num, 5, new_paid)
                
                # توليد باسورد إذا لم يكن موجوداً
                current_pass = row_values[5]
                password_msg = ""
                if not current_pass:
                    new_pass = generate_student_password()
                    ws.update_cell(row_num, 6, new_pass)
                    password_msg = f"تم إنشاء بيانات الدخول.\nالكود: {st_code}\nالباسوورد: {new_pass}"
                else:
                    password_msg = f"بيانات الدخول موجودة مسبقاً.\nالكود: {st_code}\nالباسوورد: {current_pass}"
                
                st.success("تم الدفع بنجاح!")
                st.balloons()
                st.code(password_msg, language="text")
        else:
            st.error("كود الطالب غير صحيح")

# ----------------- 4. تسجيل معلم -----------------
elif menu == "تسجيل معلم":
    st.header("إضافة معلم جديد")
    with st.form("teacher_reg"):
        t_name = st.text_input("اسم المعلم")
        t_subject = st.text_input("المادة")
        t_grade = st.selectbox("الصف الدراسي", ["الأول", "الثاني", "الثالث"])
        t_term = st.selectbox("الترم", ["الأول", "الثاني"])
        
        t_sub = st.form_submit_button("تسجيل المعلم")
        
        if t_sub:
            ws = sheet.worksheet("Teachers")
            t_id = generate_teacher_id()
            t_pass = generate_student_password() # استخدام نفس دالة التوليد للاختصار
            
            # Teachers: ID, Name, Subject, Grade, Term, Password
            ws.append_row([t_id, t_name, t_subject, t_grade, t_term, t_pass])
            st.success(f"تم التسجيل. كود المعلم: {t_id} | الباسوورد: {t_pass}")

# ----------------- 5. إضافة مواد -----------------
elif menu == "إضافة مواد دراسية":
    st.header("إضافة الروابط والامتحانات")
    type_mat = st.radio("نوع الإضافة", ["عام (لكل الطلاب)", "مادة (خاص بمعلم)"])
    
    with st.form("mat_form"):
        title = st.text_input("عنوان المادة/الامتحان")
        link = st.text_input("الرابط")
        
        teacher_id = ""
        if type_mat == "مادة (خاص بمعلم)":
             teacher_id = st.text_input("كود المعلم صاحب المادة")
             
        submit_mat = st.form_submit_button("نشر")
        
        if submit_mat and title and link:
            ws = sheet.worksheet("Materials")
            # Materials: Type, Title, Link, TeacherID, Date
            m_type = "Global" if type_mat == "عام (لكل الطلاب)" else "Subject"
            ws.append_row([m_type, title, link, teacher_id, str(datetime.now())])
            st.success("تمت الإضافة بنجاح")
