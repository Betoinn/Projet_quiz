import random
import string

BROKER = "broker.emqx.io"
PORT   = 1883
PREFIX = "isen-2026-NBEK"

def topic(code, path):
    return f"{PREFIX}/quiz/{code}/{path}"

def topic_serveur(path):
    return f"{PREFIX}/serveur/{path}"

def generer_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Parties en cours (animateur) 
parties = {}

def nouvelle_partie(code, questions):
    parties[code] = {
        "state":           "attente",
        "questions":       questions,
        "question_index":  0,
        "joueurs_presents": {},
        "reponses_tour":   {},
        "scores":          {},
    }

# État joueur 
joueur_state            = "attente"   # état de la partie
joueur_code             = None        # code de la partie 
question_active         = None        # question en cours
reponse_envoyee         = False       # envoie de la réponse du joueur
scores_recus            = False       # reception du classement final 
reponses_tour_joueur    = None        # réponse du joueur pour la correction
correction_active       = None        # correction à la fin d'une question
classement_final        = None        # classement reçu 
questions_recues        = None        # questions reçues du serveur