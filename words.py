import random

# הראל בריקמן - פה זה המקום שלך! תוסיף כמה מילים שאתה רוצה בתוך הרשימות
WORD_BANK = {
    "קל": ["כלב", "חתול"],
    "בינוני": ["מחשב", "מטוס"],
    "קשה": ["אנציקלופדיה", "סטרטוספירה"]
}

def get_random_word(difficulty="קל"):
    # פונקציה שבוחרת מילה מהרשימה של הראל
    words = WORD_BANK.get(difficulty, WORD_BANK["קל"])
    return random.choice(words)
