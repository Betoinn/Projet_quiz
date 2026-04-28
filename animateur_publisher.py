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
question_index = 0       # numéro de la question en cours
scores = {}              # nb de bonnes réponses du joueur


class AnimateurApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quiz MQTT — Animateur")
        self.geometry("800x600")
        self.resizable(False, False)

        # Titre
        self.label_titre = ctk.CTkLabel(self, text="Quiz MQTT", font=ctk.CTkFont(size=28, weight="bold"))
        self.label_titre.pack(pady=20)

        # Liste des joueurs
        self.label_joueurs = ctk.CTkLabel(self, text="Joueurs connectés :", font=ctk.CTkFont(size=16))
        self.label_joueurs.pack()

        self.liste_joueurs = ctk.CTkTextbox(self, width=400, height=120, state="disabled")
        self.liste_joueurs.pack(pady=10)

        # Bouton lancer
        self.btn_lancer = ctk.CTkButton(self, text="Lancer le quiz", command=self.lancer_quiz,
                                         state="disabled", width=200, height=40,
                                         font=ctk.CTkFont(size=15))
        self.btn_lancer.pack(pady=10)

        # Zone question en cours
        self.label_question = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=16), wraplength=700)
        self.label_question.pack(pady=10)

        # Réponses reçues
        self.label_reponses = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14), text_color="gray")
        self.label_reponses.pack()

        # Boutons correction et suite
        self.btn_correction = ctk.CTkButton(self, text="Afficher la correction", command=self.afficher_correction,
                                             state="disabled", width=200, height=40,
                                             font=ctk.CTkFont(size=15))
        self.btn_correction.pack(pady=5)

        self.btn_suivant = ctk.CTkButton(self, text="Question suivante", command=self.question_suivante,
                                          state="disabled", width=200, height=40,
                                          font=ctk.CTkFont(size=15))
        self.btn_suivant.pack(pady=5)

        # Zone scores
        self.label_scores = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14))
        self.label_scores.pack(pady=10)

        # Bouton scores finaux
        self.btn_scores = ctk.CTkButton(self, text="Envoyer les scores finaux", command=self.envoyer_scores_finaux,
                                         state="disabled", width=200, height=40,
                                         font=ctk.CTkFont(size=15))
        self.btn_scores.pack(pady=5)
        
    def setup_mqtt(self):
        self.client = paho.Client(client_id="animateur", protocol=paho.MQTTv5)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.will_set(f"isen-2026-NBEK/quiz/animateur", "offline", qos=1, retain=True)
        self.client.connect(BROKER, PORT, clean_start=False, keepalive=15)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[ANIMATEUR] Connecté : {rc}")
        self.client.subscribe(TOPIC_PRESENCE, qos=1)
        self.client.subscribe(TOPIC_REPONSES, qos=1)
        self.client.publish(f"isen-2026-NBEK/quiz/animateur", "online", qos=1, retain=True)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if "presence" in topic:
            pseudo = topic.split("/")[-1]
            joueurs_connectes[pseudo] = payload
            self.after(0, self.maj_liste_joueurs)

        elif "reponse" in topic:
            pseudo = topic.split("/")[-1]
            reponses_recues[pseudo] = payload
            # Sauvegarde recap en retained
            self.client.publish(TOPIC_RECAP, json.dumps(reponses_recues), qos=1, retain=True)
            self.after(0, self.maj_reponses)
    
    def maj_liste_joueurs(self):
        self.liste_joueurs.configure(state="normal")
        self.liste_joueurs.delete("1.0", "end")
        joueurs_prets = [p for p, s in joueurs_connectes.items() if s == "pret"]
        for p in joueurs_prets:
            self.liste_joueurs.insert("end", f"✓ {p}\n")
        self.liste_joueurs.configure(state="disabled")
        # Active le bouton lancer si au moins 2 joueurs prêts
        if len(joueurs_prets) >= 2:
            self.btn_lancer.configure(state="normal")
        else:
            self.btn_lancer.configure(state="disabled")

    def maj_reponses(self):
        joueurs_prets = [p for p, s in joueurs_connectes.items() if s == "pret"]
        nb_reponses = len(reponses_recues)
        nb_joueurs = len(joueurs_prets)
        self.label_reponses.configure(text=f"Réponses reçues : {nb_reponses}/{nb_joueurs}")
        if nb_reponses == nb_joueurs:
            self.btn_correction.configure(state="normal")

    def lancer_quiz(self):
        global question_index, scores
        question_index = 0
        scores = {p: 0 for p in joueurs_connectes if joueurs_connectes[p] == "pret"}
        self.btn_lancer.configure(state="disabled")
        self.client.publish(TOPIC_ETAT, "en_cours", qos=1, retain=True)
        self.afficher_question()

    def afficher_question(self):
        global reponses_recues
        reponses_recues = {}
        self.client.publish(TOPIC_RECAP, json.dumps({}), qos=1, retain=True)
        q = QUESTIONS[question_index]
        payload = json.dumps(q)
        self.client.publish(TOPIC_QUESTION, payload, qos=1, retain=True)
        self.client.publish(TOPIC_ETAT, f"question_{question_index+1}", qos=1, retain=True)
        self.label_question.configure(
            text=f"Q{question_index+1}/{len(QUESTIONS)} : {q['question']}\n"
                 f"A: {q['choix']['A']}   B: {q['choix']['B']}\n"
                 f"C: {q['choix']['C']}   D: {q['choix']['D']}"
        )
        self.label_reponses.configure(text="Réponses reçues : 0")
        self.btn_correction.configure(state="disabled")
        self.btn_suivant.configure(state="disabled")

    def afficher_correction(self):
        q = QUESTIONS[question_index]
        bonne = q["reponse"]
        # Calcule les scores
        for pseudo, rep in reponses_recues.items():
            if rep == bonne:
                scores[pseudo] = scores.get(pseudo, 0) + 1
        correction = json.dumps({"bonne_reponse": bonne, "scores": scores})
        self.client.publish(TOPIC_CORRECTION, correction, qos=1, retain=True)
        self.label_question.configure(
            text=f"Bonne réponse : {bonne} — {q['choix'][bonne]}"
        )
        self.label_scores.configure(text=str(scores))
        self.btn_correction.configure(state="disabled")
        if question_index + 1 < len(QUESTIONS):
            self.btn_suivant.configure(state="normal")
        else:
            self.btn_scores.configure(state="normal")

    def question_suivante(self):
        global question_index
        question_index += 1
        self.btn_suivant.configure(state="disabled")
        self.afficher_question()

    def envoyer_scores_finaux(self):
        joueurs_prets = [p for p in joueurs_connectes if joueurs_connectes[p] == "pret"]
        nb_questions = len(QUESTIONS)
        resultats = {}
        for p in joueurs_prets:
            nb_bonnes = scores.get(p, 0)
            resultats[p] = {
                "bonnes_reponses": nb_bonnes,
                "pourcentage": round(nb_bonnes / nb_questions * 100)
            }
        # Classement
        classement = sorted(resultats.items(), key=lambda x: x[1]["bonnes_reponses"], reverse=True)
        payload = json.dumps({"resultats": resultats, "classement": [p for p, _ in classement]})
        self.client.publish(TOPIC_SCORES, payload, qos=1, retain=True)
        self.client.publish(TOPIC_ETAT, "fini", qos=1, retain=True)
        self.label_scores.configure(text="Scores finaux envoyés aux joueurs !")
        self.btn_scores.configure(state="disabled")

if __name__ == "__main__":
    app = AnimateurApp()
    app.setup_mqtt()
    app.mainloop()