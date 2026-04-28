BROKER = "broker.emqx.io"
PORT   = 1883
PREFIX = "isen-2026-NBEK"

def topic(path):
    return f"{PREFIX}/quiz/{path}"

# État animateur
joueurs_presents = {}
reponses_tour    = {}
scores           = {}

# État joueur
state           = "attente"
question_active = None
reponse_envoyee = False
scores_recus    = False