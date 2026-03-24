import streamlit as st
import words  # ייבוא המחסן של הראל בריקמן

# הגדרות כותרת ועיצוב בסיסי (הראל טוסון יוכל להמשיך מכאן)
st.set_page_config(page_title="Alias AI - משחק מילים", page_icon="🎮")
st.title("🎮 Alias AI - משחק הניחושים")
st.markdown("---")

# ניהול מצב המשחק (Session State)
if 'current_word' not in st.session_state:
    st.session_state.current_word = None
    st.session_state.hints = []
    st.session_state.score = 0

# תפריט בחירת קטגוריה
categories = words.get_categories()
selected_category = st.selectbox("בחר נושא למשחק:", categories)

# כפתור להתחלת משחק או החלפת מילה
if st.button("משוך מילה חדשה"):
    word, hints = words.get_random_word(selected_category)
    st.session_state.current_word = word
    st.session_state.hints = hints
    st.success(f"נבחרה מילה מהקטגוריה: {selected_category}")

# הצגת המשחק במידה ונבחרה מילה
if st.session_state.current_word:
    st.subheader(f"הקטגוריה: {selected_category}")
    
    # הצגת רמזים (הראל בריקמן הכין רשימה, אנחנו מציגים אותם)
    st.write("💡 **רמזים מהמערכת:**")
    for hint in st.session_state.hints:
        st.info(hint)

    # תיבת ניחוש
    user_guess = st.text_input("מה המילה לדעתך?")
    
    if st.button("בדוק ניחוש"):
        if user_guess.strip() == st.session_state.current_word:
            st.balloons()
            st.success(f"כל הכבוד! המילה היא אכן: {st.session_state.current_word}")
            st.session_state.score += 10
        else:
            st.error("לא בדיוק... נסה שוב או בקש רמז מה-AI (בקרוב!)")

st.sidebar.metric("הניקוד שלך:", st.session_state.score)

# כאן רפאל יחבר את ה-AI שלו בעתיד
st.sidebar.markdown("---")
st.sidebar.write("🤖 סטטוס AI: ממתין לרפאל...")
