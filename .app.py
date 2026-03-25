import streamlit as st
import words 

st.set_page_config(page_title="Alias AI", page_icon="🤖")
st.title("🤖 Alias AI")

if 'secret_word' not in st.session_state:
    st.session_state.secret_word = None
    st.session_state.hints = []
def calculate_score(hint_num):
    scores = {1: 10, 2: 7, 3: 4, 4: 2}
    return scores.get(hint_num, 0)

# בחירת קטגוריה
categories = words.get_categories()
selected_cat = st.selectbox("בחר נושא:", categories)

if st.button("התחל משחק / החלף מילה"):
    st.session_state.secret_word = words.get_random_word(selected_cat)
    st.session_state.hints = []
    st.success(f"המילה נבחרה מהנושא: {selected_cat}")

if st.session_state.secret_word:
    # כאן רפאל יכניס את הקוד שמפעיל את Gemini
    if st.button("בקש רמז מה-AI"):
        new_hint = f"רמז זמני למילה שמתחילה ב-'{st.session_state.secret_word[0]}'... (רפאל, כאן נכנס ה-AI שלך!)"
        st.session_state.hints.append(new_hint)

    # הצגת הרמזים שה-AI ייצר
    for hint in st.session_state.hints:
        st.info(hint)
def calculate_score(hint_num):
    scores = {1: 10, 2: 7, 3: 4, 4: 2}
    return scores.get(hint_num, 0)

    guess = st.text_input("מה המילה הסודית?")
    if st.button("בדיקת ניחוש"):
        if guess.strip().lower() == st.session_state.secret_word.lower():
            st.balloons()
            st.success("בול! כל הכבוד!")
        else:
            st.error("לא נכון, נסה שוב או בקש עוד רמז.")
def calculate_score(hint_num):
    scores = {1: 10, 2: 7, 3: 4, 4: 2}
    return scores.get(hint_num, 0)
