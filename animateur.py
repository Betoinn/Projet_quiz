# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 14:25:25 2026

@author: Utilisateur
"""

import customtkinter as ctk
import time
import json
import shared_state as state
import animateur_publisher as pub_module
import animateur_subscriber as sub_module

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

class AnimateurApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quiz Animateur")
        self.geometry("700x500")

        ctk.CTkLabel(self, text="Quiz Animateur",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        # Liste joueurs
        ctk.CTkLabel(self, text="Joueurs connectés :",
                     font=ctk.CTkFont(size=14)).pack()
        self.liste_joueurs = ctk.CTkTextbox(self, width=500, height=120,
                                             state="disabled")
        self.liste_joueurs.pack(pady=10)

        self.label_statut = ctk.CTkLabel(self, text="En attente de joueurs...",
                                          text_color="gray",
                                          font=ctk.CTkFont(size=13))
        self.label_statut.pack(pady=5)

        # Bouton lancer
        self.btn_lancer = ctk.CTkButton(self, text="Lancer le quiz",
                                         command=self.lancer_quiz,
                                         state="disabled", width=200, height=40,
                                         font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_lancer.pack(pady=10)

        # Log MQTT
        ctk.CTkLabel(self, text="Log MQTT :",
                     font=ctk.CTkFont(size=13)).pack()
        self.log = ctk.CTkTextbox(self, width=500, height=120, state="disabled")
        self.log.pack(pady=10)

    def setup_mqtt(self):
        self.pub = pub_module.build_client()
        self.pub.connect(state.BROKER, state.PORT, clean_start=False)
        self.pub.loop_start()

        self.sub = sub_module.build_client()
        self.sub.connect(state.BROKER, state.PORT, clean_start=False)
        self.sub.loop_start()

        time.sleep(1)
        self.pub.publish(state.topic("state"), "attente", qos=1, retain=True)
        self.log_message("Connecté au broker, état : attente")
        self.after(1000, self.maj_lobby)

    def log_message(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", f"{msg}\n")
        self.log.configure(state="disabled")

    def maj_lobby(self):
        self.liste_joueurs.configure(state="normal")
        self.liste_joueurs.delete("1.0", "end")
        prets = [p for p, s in state.joueurs_presents.items() if s == "pret"]
        for p in prets:
            self.liste_joueurs.insert("end", f"✓ {p}\n")
        self.liste_joueurs.configure(state="disabled")

        if len(prets) >= 2:
            self.btn_lancer.configure(state="normal")
            self.label_statut.configure(text=f"{len(prets)} joueurs prêts !")
        else:
            self.btn_lancer.configure(state="disabled")
            self.label_statut.configure(text=f"En attente ({len(prets)}/2 joueurs)...")

        self.after(1000, self.maj_lobby)

    def lancer_quiz(self):
        self.pub.publish(state.topic("state"), "question", qos=1, retain=True)
        q = QUESTIONS[0]
        self.pub.publish(state.topic("question"), json.dumps(q), qos=1, retain=True)
        self.log_message(f"Question 1 publiée : {q['question']}")
        self.btn_lancer.configure(state="disabled")

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