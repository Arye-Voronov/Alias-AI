import streamlit as st
import words 

st.set_page_config(page_title="Alias AI", page_icon="🤖")
st.title("🤖 Alias AI")

# --- ניהול מצב המשחק (הזיכרון) ---
if 'secret_word' not in st.session_state:
    st.session_state.secret_word = None
    st.session_state.hints = []
    st.session_state.score = 0

# הפונקציה של הראל בריקמן לחישוב הניקוד
def calculate_score(hint_num):
    scores = {1: 10, 2: 7, 3: 4, 4: 2}
    return scores.get(hint_num, 1) # אם יש יותר מ-4 רמזים, מקבלים נקודה אחת

# --- בחירת קטגוריה ---
categories = words.get_categories()
selected_cat = st.selectbox("בחר נושא:", categories)

if st.button("התחל משחק / החלף מילה"):
    st.session_state.secret_word = words.get_random_word(selected_cat)
    st.session_state.hints = []
    st.success(f"המילה נבחרה מהנושא: {selected_cat}")

# --- מהלך המשחק ---
if st.session_state.secret_word:
    # כאן רפאל יכניס את הקוד שמפעיל את Gemini
    if st.button("בקש רמז מה-AI"):
        # כרגע זה רמז דמי, רפאל יחליף את זה
        new_hint = f"רמז {len(st.session_state.hints) + 1} למילה שמתחילה ב-'{st.session_state.secret_word[0]}'"
        st.session_state.hints.append(new_hint)

    # הצגת הרמזים
    for hint in st.session_state.hints:
        st.info(hint)

    # תיבת ניחוש
    guess = st.text_input("מה המילה הסודית?")
    
    if st.button("בדיקת ניחוש"):
        if guess.strip().lower() == st.session_state.secret_word.lower():
            st.balloons()
            # משתמשים בפונקציה של הראל לחישוב הניקוד לפי מספר הרמזים
            points = calculate_score(len(st.session_state.hints))
            st.session_state.score += points
            st.success(f"בול! כל הכבוד! זכית ב-{points} נקודות!")
        else:
            st.error("לא נכון, נסה שוב או בקש עוד רמז.")

# תצוגת ניקוד בסידבר
st.sidebar.metric("הניקוד המצטבר שלך 🏆", st.session_state.score)
st.sidebar.write(f"מספר רמזים שנוצלו: {len(st.session_state.hints)}")
