import streamlit as st
import words 

# הגדרות דף
st.set_page_config(page_title="Alias AI", page_icon="🤖")
st.title("🤖 Alias AI - משחק המילים")

# --- ניהול הזיכרון (Session State) ---
if 'secret_word' not in st.session_state:
    st.session_state.secret_word = None
    st.session_state.hints = []
    st.session_state.score = 0
    st.session_state.game_over = False

# הפונקציה של הראל לחישוב ניקוד (10 על ההתחלה, יורד ככל שיש יותר רמזים)
def calculate_score(hint_num):
    scores = {0: 10, 1: 10, 2: 7, 3: 5, 4: 3, 5: 1}
    return scores.get(hint_num, 0)

# --- תפריט צד (הראל טוסון יכול לעצב כאן) ---
with st.sidebar:
    st.header("תפריט")
    categories = words.get_categories()
    selected_cat = st.selectbox("בחר נושא:", categories)
    
    if st.button("🔄 משחק חדש / החלף מילה"):
        st.session_state.secret_word = words.get_random_word(selected_cat)
        st.session_state.hints = []
        st.session_state.game_over = False
        st.rerun()
    
    st.write("---")
    st.metric("הניקוד שלך 🏆", st.session_state.score)
    st.write(f"רמזים שנוצלו: {len(st.session_state.hints)}/5")

# --- מסך המשחק המרכזי ---
if st.session_state.secret_word:
    st.subheader(f"הקטגוריה: {selected_cat}")

    if not st.session_state.game_over:
        # כפתור רמז - כאן רפאל יתחבר עם ה-AI
        if st.button("💡 בקש רמז"):
            if len(st.session_state.hints) < 5:
                # זמני: רפאל יחליף את זה בקריאה ל-Gemini
                placeholder_hint = f"רמז {len(st.session_state.hints)+1}: המילה מתחילה ב-'{st.session_state.secret_word[0]}'"
                st.session_state.hints.append(placeholder_hint)
            else:
                st.warning("זהו, נגמרו הרמזים! חייב לנחש.")

        # הצגת הרמזים בתיבות כחולות
        for h in st.session_state.hints:
            st.info(h)

        # תיבת הניחוש
        guess = st.text_input("מה המילה הסודית?", key="guess_input")
        
        if st.button("בדיקת ניחוש"):
            if guess.strip().lower() == st.session_state.secret_word.lower():
                st.balloons()
                pts = calculate_score(len(st.session_state.hints))
                st.session_state.score += pts
                st.success(f"מדהים! צדקת וזכית ב-{pts} נקודות!")
                st.session_state.game_over = True
            else:
                st.error("לא נכון, נסה שוב!")
                # בדיקה אם הפסיד כי נגמרו הרמזים
                if len(st.session_state.hints) >= 5:
                    st.session_state.game_over = True

    # מה קורה כשנגמר המשחק (ניצחון או הפסד)
    if st.session_state.game_over:
        if guess.strip().lower() != st.session_state.secret_word.lower():
            st.error(f"נגמר המשחק! המילה הייתה: **{st.session_state.secret_word}**")
            st.write("בפעם הבאה תקבל 0 נקודות... נסה שוב!")
        
        if st.button("למילה הבאה ➡️"):
            st.session_state.secret_word = words.get_random_word(selected_cat)
            st.session_state.hints = []
            st.session_state.game_over = False
            st.rerun()
else:
    st.info("לחץ על 'משחק חדש' בתפריט הצד כדי להתחיל!")
