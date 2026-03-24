import streamlit as st
import words  # יבוא המילים של הראל בריקמן
# import ai_engine  # כאן רפאל יחבר את ה-AI בהמשך

st.set_page_config(page_title="Alias AI", page_icon="🕵️‍♂️")

# --- כותרת (הראל טוסון - UI) ---
st.title("🕵️‍♂️ משחק Alias AI")
st.subheader("הצליחו לנחש את המילה לפי רמזי הבינה המלאכותית!")

# --- אתחול המשחק ---
if 'secret_word' not in st.session_state:
    # כאן אנחנו משתמשים בפונקציה מהקובץ של הראל בריקמן
    st.session_state.secret_word = words.get_random_word("קל")
    st.session_state.hints = []

# --- תצוגת רמזים (רפאל - AI) ---
st.write("### רמזים:")
if st.button("בקש רמז חדש"):
    # כאן יבוא הקוד של רפאל שיוצר רמז
    new_hint = f"זה משהו שקשור ל-{st.session_state.secret_word[0]}..." 
    st.session_state.hints.append(new_hint)

for hint in st.session_state.hints:
    st.info(hint)

# --- קלט מהמשתמש (הראל טוסון - UI) ---
guess = st.text_input("מה המילה הסודית?")

if st.button("בדוק ניחוש"):
    # לוגיקת בדיקה (הראל בריקמן)
    if guess.strip() == st.session_state.secret_word:
        st.success("🎯 כל הכבוד! ניחשת נכון!")
        if st.button("משחק חדש"):
            del st.session_state.secret_word
            st.rerun()
    else:
        st.error("לא בדיוק... נסה שוב או בקש עוד רמז.")
