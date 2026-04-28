BROKER = "broker.emqx.io"
PORT   = 1883
PREFIX = "isen-2026-NBEK"

def topic(path):
    return f"{PREFIX}/quiz/{path}"

# État animateur
joueurs_presents = {}   # pseudo : "pret", "offline"
reponses_tour    = {}   # pseudo : lettre réponse (tour actuel)
scores           = {}   # pseudo : "correct": int, "total": int

# État joueur
state                = "attente"   # état global reçu du broker
question_active      = None        # question en cours
reponse_envoyee      = False       # est-ce que le joueur a répondu ?
scores_recus         = False       # classement final reçu ?
reponses_tour_joueur = None        # réponse du joueur pour la correction
correction_active    = None        # données de correction en cours
classement_final     = None        # classement final