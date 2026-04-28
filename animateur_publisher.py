# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 08:41:28 2026

@author: Utilisateur
"""

import customtkinter as ctk
import paho.mqtt.client as paho
import json
import time

# Configuration interface
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BROKER = "broker.emqx.io"
PORT = 1883

TOPIC_ETAT       = f"isen-2026-NBEK/quiz/etat"
TOPIC_QUESTION   = f"isen-2026-NBEK/quiz/question"
TOPIC_CORRECTION = f"isen-2026-NBEK/quiz/correction"
TOPIC_SCORES     = f"isen-2026-NBEK/quiz/scores"
TOPIC_PRESENCE   = f"isen-2026-NBEK/quiz/presence/+"
TOPIC_REPONSES   = f"isen-2026-NBEK/quiz/reponse/+"
TOPIC_RECAP      = f"isen-2026-NBEK/quiz/reponses_recap"

# Chargement des questions
with open("questions.json", "r", encoding="utf-8") as file :
    QUESTIONS = json.load(file)

# Variables globales
joueurs_connectes = {}   # etat du joueur
reponses_recues = {}     # réponse du joueur
question_index = 0
scores = {}              # nb de bonnes réponses du joueur