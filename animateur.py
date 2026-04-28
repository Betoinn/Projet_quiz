# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 14:25:25 2026

@author: Utilisateur
"""

import customtkinter as ctk
import threading
import time
import json
import paho.mqtt.client as paho
import shared_state as state
import animateur_subscriber as sub_module

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

TIMER_DEFAUT = 20

class AnimateurApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quiz MQTT — Animateur")
        self.geometry("900x650")
        self.resizable(False, False)

        self.question_index = 0
        self.prets = []

        # ── TITRE ──
        ctk.CTkLabel(self, text="🎯 Quiz MQTT — Animateur",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        # ── FRAME LOBBY ──
        self.frame_lobby = ctk.CTkFrame(self)
        self.frame_lobby.pack(fill="both", expand=True, padx=30, pady=10)

        ctk.CTkLabel(self.frame_lobby, text="Joueurs connectés :",
                     font=ctk.CTkFont(size=16)).pack(pady=10)

        self.liste_joueurs = ctk.CTkTextbox(self.frame_lobby, width=500, height=150,
                                             font=ctk.CTkFont(size=14), state="disabled")
        self.liste_joueurs.pack(pady=5)

        self.label_statut = ctk.CTkLabel(self.frame_lobby,
                                          text="En attente d'au moins 2 joueurs...",
                                          font=ctk.CTkFont(size=13), text_color="gray")
        self.label_statut.pack(pady=5)

        self.btn_lancer = ctk.CTkButton(self.frame_lobby, text="▶  Lancer le quiz",
                                         command=self.lancer_quiz, state="disabled",
                                         width=220, height=45,
                                         font=ctk.CTkFont(size=15, weight="bold"))
        self.btn_lancer.pack(pady=15)

        # ── FRAME QUESTION ──
        self.frame_question = ctk.CTkFrame(self)

        self.label_num_question = ctk.CTkLabel(self.frame_question, text="",
                                                font=ctk.CTkFont(size=13), text_color="gray")
        self.label_num_question.pack(pady=5)

        self.label_question = ctk.CTkLabel(self.frame_question, text="",
                                            font=ctk.CTkFont(size=18, weight="bold"),
                                            wraplength=800)
        self.label_question.pack(pady=10)

        self.label_reponses = ctk.CTkLabel(self.frame_question, text="",
                                            font=ctk.CTkFont(size=14), text_color="#aaaaaa")
        self.label_reponses.pack(pady=5)

        self.label_timer = ctk.CTkLabel(self.frame_question, text="",
                                         font=ctk.CTkFont(size=22, weight="bold"),
                                         text_color="#f0a500")
        self.label_timer.pack(pady=5)

        self.label_correction = ctk.CTkLabel(self.frame_question, text="",
                                              font=ctk.CTkFont(size=15),
                                              text_color="#2ecc71", wraplength=800)
        self.label_correction.pack(pady=5)

        self.label_scores_tour = ctk.CTkLabel(self.frame_question, text="",
                                               font=ctk.CTkFont(size=13),
                                               text_color="#aaaaaa")
        self.label_scores_tour.pack(pady=5)

        self.btn_suivant = ctk.CTkButton(self.frame_question, text="Question suivante ▶",
                                          command=self.question_suivante, state="disabled",
                                          width=220, height=45,
                                          font=ctk.CTkFont(size=15, weight="bold"))
        self.btn_suivant.pack(pady=10)

        self.btn_scores_finaux = ctk.CTkButton(self.frame_question,
                                                text="🏆 Envoyer les scores finaux",
                                                command=self.envoyer_scores_finaux,
                                                state="disabled", width=220, height=45,
                                                font=ctk.CTkFont(size=15, weight="bold"))
        self.btn_scores_finaux.pack(pady=5)

        # ── FRAME SCORES ──
        self.frame_scores = ctk.CTkFrame(self)

        ctk.CTkLabel(self.frame_scores, text="🏆 Classement final",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        self.label_classement = ctk.CTkLabel(self.frame_scores, text="",
                                              font=ctk.CTkFont(size=15))
        self.label_classement.pack(pady=10)

    def setup_mqtt(self):
        self.pub = paho.Client(
            callback_api_version=paho.CallbackAPIVersion.VERSION2,
            client_id="animateur-pub-EK",
            protocol=paho.MQTTv5
        )
        self.pub.will_set(state.topic("presence/animateur"), "offline", qos=1, retain=True)
        self.pub.on_connect = self.on_connect_pub
        self.pub.connect(state.BROKER, state.PORT)
        self.pub.loop_start()

        self.sub = sub_module.build_client()
        self.sub.connect(state.BROKER, state.PORT)
        self.sub.loop_start()

        time.sleep(1)
        self.pub.publish(state.topic("state"), "attente", qos=1, retain=True)
        self.after(500, self.maj_lobby)

    def on_connect_pub(self, client, userdata, flags, rc, properties=None):
        print(f"[ANIMATEUR] Connecté : {rc}")
        client.publish(state.topic("presence/animateur"), "online", qos=1, retain=True)

    def maj_lobby(self):
        self.liste_joueurs.configure(state="normal")
        self.liste_joueurs.delete("1.0", "end")
        prets = [p for p, s in state.joueurs_presents.items() if s == "pret"]
        for p in prets:
            self.liste_joueurs.insert("end", f"✓  {p}\n")
        self.liste_joueurs.configure(state="disabled")
        if len(prets) >= 2:
            self.btn_lancer.configure(state="normal")
            self.label_statut.configure(text=f"{len(prets)} joueurs prêts — tu peux lancer !")
        else:
            self.btn_lancer.configure(state="disabled")
            self.label_statut.configure(text="En attente d'au moins 2 joueurs...")
        self.after(1000, self.maj_lobby)

    def lancer_quiz(self):
        self.prets = [p for p, s in state.joueurs_presents.items() if s == "pret"]
        for p in self.prets:
            state.scores.setdefault(p, {"correct": 0, "total": 0})
        self.frame_lobby.pack_forget()
        self.frame_question.pack(fill="both", expand=True, padx=30, pady=10)
        self.question_index = 0
        self.afficher_question()

    def afficher_question(self):
        state.reponses_tour.clear()
        q = QUESTIONS[self.question_index]
        self.pub.publish(state.topic("question"), json.dumps(q), qos=1, retain=True)
        self.pub.publish(state.topic("state"), "question", qos=1, retain=True)

        self.label_num_question.configure(
            text=f"Question {self.question_index+1} / {len(QUESTIONS)}")
        self.label_question.configure(text=q["question"])
        self.label_correction.configure(text="")
        self.label_scores_tour.configure(text="")
        self.btn_suivant.configure(state="disabled")
        self.btn_scores_finaux.configure(state="disabled")

        timer = q.get("timer", TIMER_DEFAUT)
        self.label_timer.configure(text=f"⏳ {timer}s")
        self.after(0, lambda: self.countdown(timer, q))

    def countdown(self, remaining, q):
        joueurs_actifs = [p for p in self.prets if state.joueurs_presents.get(p) == "pret"]
        nb_rep = len(state.reponses_tour)
        self.label_reponses.configure(text=f"Réponses reçues : {nb_rep}/{len(joueurs_actifs)}")

        if remaining <= 0 or nb_rep >= len(joueurs_actifs):
            self.label_timer.configure(text="")
            self.afficher_correction(q)
            return

        self.label_timer.configure(text=f"⏳ {remaining}s")
        self.after(1000, lambda: self.countdown(remaining - 1, q))

    def afficher_correction(self, q):
        bonne = q["reponse"]
        texte_bonne = q["choix"][bonne]

        for p in self.prets:
            rep = state.reponses_tour.get(p)
            state.scores[p]["total"] += 1
            if rep == bonne:
                state.scores[p]["correct"] += 1

        correction = {
            "bonne_reponse": bonne,
            "texte_reponse": texte_bonne,
            "reponses": state.reponses_tour.copy()
        }
        self.pub.publish(state.topic("correction"), json.dumps(correction), qos=1, retain=True)
        self.pub.publish(state.topic("state"), "correction", qos=1, retain=True)

        self.label_correction.configure(
            text=f"✅ Bonne réponse : {bonne}. {texte_bonne}")

        scores_txt = ""
        for p in self.prets:
            rep = state.reponses_tour.get(p, "—")
            icone = "🟢" if rep == bonne else "🔴"
            scores_txt += f"{icone} {p} → {rep}   "
        self.label_scores_tour.configure(text=scores_txt)

        if self.question_index + 1 < len(QUESTIONS):
            self.btn_suivant.configure(state="normal")
        else:
            self.btn_scores_finaux.configure(state="normal")

    def question_suivante(self):
        self.question_index += 1
        self.btn_suivant.configure(state="disabled")
        self.afficher_question()

    def envoyer_scores_finaux(self):
        nb_questions = len(QUESTIONS)
        classement = []
        for p, s in state.scores.items():
            pct = round((s["correct"] / nb_questions) * 100, 1)
            classement.append({"pseudo": p, "correct": s["correct"],
                                "total": nb_questions, "pct": pct})
        classement.sort(key=lambda x: x["correct"], reverse=True)

        self.pub.publish(state.topic("scores"),
                         json.dumps({"classement": classement}), qos=1, retain=True)
        self.pub.publish(state.topic("state"), "fin", qos=1, retain=True)

        self.frame_question.pack_forget()
        self.frame_scores.pack(fill="both", expand=True, padx=30, pady=10)

        medailles = {0: "🥇", 1: "🥈", 2: "🥉"}
        txt = ""
        for i, j in enumerate(classement):
            txt += f"{medailles.get(i, f'{i+1}.')}  {j['pseudo']} — {j['correct']}/{j['total']} ({j['pct']}%)\n\n"
        self.label_classement.configure(text=txt)

    def on_closing(self):
        self.pub.publish(state.topic("presence/animateur"), "offline", qos=1, retain=True)
        time.sleep(0.3)
        self.pub.loop_stop()
        self.pub.disconnect()
        self.sub.loop_stop()
        self.sub.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = AnimateurApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.setup_mqtt()
    app.mainloop()