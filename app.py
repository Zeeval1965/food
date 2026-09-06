import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import date
from google import genai
from google.genai import types

# 1. הגדרת מסד נתונים מקומי (SQLite)
def init_db():
    conn = sqlite3.connect("nutrition.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            meal_name TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL
        )
    ''')
    conn.commit()
    conn.close()

def add_meal(meal_name, calories, protein, carbs, fat):
    conn = sqlite3.connect("nutrition.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO meals (date, meal_name, calories, protein, carbs, fat)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (str(date.today()), meal_name, calories, protein, carbs, fat))
    conn.commit()
    conn.close()

def get_today_meals():
    conn = sqlite3.connect("nutrition.db")
    df = pd.read_sql_query(
        "SELECT id, meal_name AS 'ארוחה', calories AS 'קלוריות', protein AS 'חלבון (ג\')', carbs AS 'פחמימות (ג\')', fat AS 'שומן (ג\')' FROM meals WHERE date = ?",
        conn, params=(str(date.today()),)
    )
    conn.close()
    return df

def delete_meal(meal_id):
    conn = sqlite3.connect("nutrition.db")
    c = conn.cursor()
    c.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    conn.commit()
    conn.close()

# 2. פענוח טקסט חופשי באמצעות Gemini AI
def parse_meal_with_ai(api_key, text_input):
    client = genai.Client(api_key=api_key)
    prompt = f"""
    נתח את תיאור המזון הבא בעברית והחזר ערכים תזונתיים משוערים בפורמט JSON בלבד.
    תיאור המזון: "{text_input}"

    פורמט התשובה (JSON בלבד, ללא טקסט נוסף):
    {{
        "meal_name": "שם או תיאור קצר של הארוחה",
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0
    }}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

# 3. ממשק משתמש ב-Streamlit
st.set_page_config(page_title="מחשבון תזונה אישי", layout="wide")
init_db()

st.title("🥗 מחשבון ומעקב תזונה אישי")

# סרגל צד - הגדרות ומפתח API
with st.sidebar:
    st.header("⚙️ הגדרות")
    api_key = st.text_input("מפתח Gemini API", type="password")
    
    st.subheader("🎯 יעדים יומיים")
    target_cal = st.number_input("יעד קלוריות", value=2000, step=50)
    target_protein = st.number_input("יעד חלבון (גרם)", value=150, step=5)
    target_carbs = st.number_input("יעד פחמימות (גרם)", value=200, step=5)
    target_fat = st.number_input("יעד שומן (גרם)", value=65, step=5)

tab1, tab2 = st.tabs(["➕ הוספת ארוחה", "📊 יומן ומדדים יומיים"])

with tab1:
    st.subheader("תיעוד ארוחה בטקסט חופשי")
    meal_input = st.text_area("מה אכלת?", placeholder="לדוגמה: 200 גרם חזה עוף בגריל, כוס אורז לבן מבושל וסלט ירקות עם כפית שמן זית")
    
    if st.button("פענח ארוחה ב-AI", type="primary"):
        if not api_key:
            st.error("יש להזין מפתח API בסרגל הצד.")
        elif not meal_input.strip():
            st.warning("יש להזין תיאור ארוחה.")
        else:
            with st.spinner("מפענח ערכים תזונתיים..."):
                try:
                    data = parse_meal_with_ai(api_key, meal_input)
                    st.session_state['parsed_meal'] = data
                    st.success("הארוחה פוענחה בהצלחה!")
                except Exception as e:
                    st.error(f"שגיאה בפענוח: {e}")

    if 'parsed_meal' in st.session_state:
        pm = st.session_state['parsed_meal']
        st.write("---")
        st.write("### אישור ועריכת ערכים")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            m_name = st.text_input("שם הארוחה", value=pm.get('meal_name', ''))
        with col2:
            m_cal = st.number_input("קלוריות", value=float(pm.get('calories', 0)))
        with col3:
            m_prot = st.number_input("חלבון (ג')", value=float(pm.get('protein', 0)))
        with col4:
            m_carb = st.number_input("פחמימות (ג')", value=float(pm.get('carbs', 0)))
        with col5:
            m_fat = st.number_input("שומן (ג')", value=float(pm.get('fat', 0)))

        if st.button("💾 שמור ביומן"):
            add_meal(m_name, m_cal, m_prot, m_carb, m_fat)
            st.success("הארוחה נשמרה בהצלחה!")
            del st.session_state['parsed_meal']
            st.rerun()

with tab2:
    st.subheader(f"סיכום יום ({date.today().strftime('%d/%m/%Y')})")
    df_today = get_today_meals()
    
    total_cal = df_today['קלוריות'].sum() if not df_today.empty else 0
    total_prot = df_today["חלבון (ג')"].sum() if not df_today.empty else 0
    total_carb = df_today["פחמימות (ג')"].sum() if not df_today.empty else 0
    total_fat = df_today["שומן (ג')"].sum() if not df_today.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("קלוריות", f"{total_cal:.0f} / {target_cal}", delta=f"{total_cal - target_cal:.0f}")
    m2.metric("חלבון", f"{total_prot:.1f}g / {target_protein}g", delta=f"{total_prot - target_protein:.1f}g")
    m3.metric("פחמימות", f"{total_carb:.1f}g / {target_carbs}g", delta=f"{total_carb - target_carbs:.1f}g")
    m4.metric("שומן", f"{total_fat:.1f}g / {target_fat}g", delta=f"{total_fat - target_fat:.1f}g")

    st.write("---")
    st.write("### פירוט ארוחות היום")
    
    if not df_today.empty:
        st.dataframe(df_today.drop(columns=['id']), use_container_width=True)
        
        with st.expander("🗑️ מחיקת ארוחה"):
            meal_to_delete = st.selectbox(
                "בחר ארוחה למחיקה", 
                options=df_today['id'], 
                format_func=lambda x: df_today[df_today['id']==x]['ארוחה'].values[0]
            )
            if st.button("מחק ארוחה"):
                delete_meal(meal_to_delete)
                st.success("הארוחה נמחקה.")
                st.rerun()
    else:
        st.info("טרם הוקלטו ארוחות להיום.")
