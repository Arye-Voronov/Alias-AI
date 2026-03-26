import streamlit as st
import words 

st.set_page_config(page_title="Alias AI", page_icon="🤖")
st.title("🤖 Alias AI")

if 'secret_word' not in st.session_state:
    st.session_state.secret_word = None
    st.session_state.hints = []
    st.session_state.score = 0
    st.session_state.game_over = False

def calculate_score(hint_num):
    scores = {1: 10, 2: 7, 3: 4, 4: 2}
    return scores.get(hint_num, 0)

categories = words.get_categories()
selected_cat = st.selectbox("בחר נושא:", categories)

if st.button("התחל משחק חדש"):
    st.session_state.secret_word = words.get_random_word(selected_cat)
    st.session_state.hints = []
    st.session_state.game_over = False
    st.success(f"המילה נבחרה מהנושא: {selected_cat}")

if st.session_state.secret_word:
    if not st.session_state.game_over:
        if st.button("בקש רמז מה-AI"):
            if len(st.session_state.hints) < 5:
                new_hint = f"רמז {len(st.session_state.hints) + 1} למילה... (כאן יכנס ה-AI)"
                st.session_state.hints.append(new_hint)
            
            if len(st.session_state.hints) == 5:
                st.warning("ניסיון אחרון ודי!")

        for hint in st.session_state.hints:
            st.info(hint)

        guess = st.text_input("מה המילה הסודית?")
        
        if st.button("בדיקת ניחוש"):
            if guess.strip().lower() == st.session_state.secret_word.lower():
                st.balloons()
                points = calculate_score(len(st.session_state.hints))
                st.session_state.score += points
                st.success(f"בול! זכית ב-{points} נקודות!")
                st.session_state.game_over = True
            else:
                if len(st.session_state.hints) >= 5:
                    st.error(f"הפסדת! המילה הייתה: {st.session_state.secret_word}")
                    st.session_state.game_over = True
                else:
                    st.error("טעות, נסה שוב.")

    else:
        if st.button("עבור למילה הבאה (שמור ניקוד)"):
            st.session_state.secret_word = words.get_random_word(selected_cat)
            st.session_state.hints = []
            st.session_state.game_over = False
            st.rerun()

st.sidebar.metric("הניקוד המצטבר 🏆", st.session_state.score)
st.sidebar.write(f"רמזים שנוצלו: {len(st.session_state.hints)} / 5")
