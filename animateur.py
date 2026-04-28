# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 14:25:25 2026

@author: Utilisateur
"""

import customtkinter as ctk
import time
import json
import threading
import shared_state as state
import animateur_publisher as pub_module
import animateur_subscriber as sub_module

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MAX_PARTIES = 4

class PartieFrame(ctk.CTkFrame):

    def __init__(self, master, code, app, **kwargs):
        super().__init__(master, **kwargs)
        self.code = code
        self.app  = app
        self.pub  = None
        self.sub  = None
        self.timer_thread = None
        self.partie_lancee = False

        # ── TITRE ──────────────────────────────────────────────
        ctk.CTkLabel(self, text=f"Partie : {code}",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)

        # ── JOUEURS ────────────────────────────────────────────
        self.liste_joueurs = ctk.CTkTextbox(self, width=250, height=60,
                                             font=ctk.CTkFont(size=12),
                                             state="disabled")
        self.liste_joueurs.pack(pady=3)

        self.label_statut = ctk.CTkLabel(self, text="En attente de joueurs...",
                                          font=ctk.CTkFont(size=11),
                                          text_color="gray")
        self.label_statut.pack()

        # ── QUESTION EN COURS ──────────────────────────────────
        self.label_question = ctk.CTkLabel(self, text="",
                                            font=ctk.CTkFont(size=12),
                                            wraplength=260)
        self.label_question.pack(pady=3)

        self.label_reponses = ctk.CTkLabel(self, text="",
                                            font=ctk.CTkFont(size=11),
                                            text_color="gray")
        self.label_reponses.pack()

        self.label_correction = ctk.CTkLabel(self, text="",
                                              font=ctk.CTkFont(size=11),
                                              text_color="#2ecc71")
        self.label_correction.pack()

        # ── SCORES ─────────────────────────────────────────────
        self.label_scores = ctk.CTkLabel(self, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color="#aaaaaa")
        self.label_scores.pack(pady=3)

        # ── BOUTONS ────────────────────────────────────────────
        frame_boutons = ctk.CTkFrame(self, fg_color="transparent")
        frame_boutons.pack(pady=5)

        self.btn_lancer = ctk.CTkButton(frame_boutons, text="▶ Lancer",
                                         command=self.lancer_partie,
                                         state="disabled", width=110, height=32,
                                         font=ctk.CTkFont(size=12, weight="bold"))
        self.btn_lancer.grid(row=0, column=0, padx=5)

        self.btn_terminer = ctk.CTkButton(frame_boutons, text="Stop",
                                           command=self.terminer_partie,
                                           state="normal", width=110, height=32,
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           fg_color="#e74c3c", hover_color="#c0392b")
        self.btn_terminer.grid(row=0, column=1, padx=5)

    def setup_mqtt(self):
        """Initialise et connecte les clients MQTT pour cette partie."""
        self.pub = pub_module.build_client(self.code)
        self.pub.connect(state.BROKER, state.PORT, clean_start=False)
        self.pub.loop_start()

        self.sub = sub_module.build_client(
            self.code,
            on_questions_recues = self.on_questions_recues,
            on_joueur_update    = self.on_joueur_update,
            on_reponse_recue    = self.on_reponse_recue
        )
        self.sub.connect(state.BROKER, state.PORT, clean_start=False)
        self.sub.loop_start()

        # Demande les questions au serveur
        time.sleep(1)
        pub_module.publier_demande_questions(
            self.pub, self.code,
            state.parties[self.code]["nb_questions"]
        )
        self.after(1000, self.maj_lobby)

    def on_questions_recues(self, questions, erreur):
        """Appelé quand le serveur répond à la demande de questions."""
        if erreur:
            self.after(0, lambda: self.label_statut.configure(
                text=erreur, text_color="red"))
            return
        state.parties[self.code]["questions"] = questions
        self.after(0, lambda: self.label_statut.configure(
            text=f"{len(questions)} questions prêtes !",
            text_color="#2ecc71"))

    def on_joueur_update(self, code, pseudo, statut):
        """Appelé quand un joueur se connecte ou se déconnecte."""
        self.after(0, self.maj_lobby)

        # Si partie en cours et il reste moins de 2 joueurs → terminer
        if self.partie_lancee:
            prets = [p for p, s in state.parties[code]["joueurs_presents"].items()
                     if s == "pret"]
            if len(prets) < 1:
                self.after(0, self.terminer_partie)

    def on_reponse_recue(self, code, pseudo, reponse):
        """Appelé quand un joueur envoie une réponse."""
        self.after(0, self.maj_reponses)

    def maj_lobby(self):
        """Met à jour la liste des joueurs."""
        partie = state.parties.get(self.code, {})
        joueurs = partie.get("joueurs_presents", {})
        prets   = [p for p, s in joueurs.items() if s == "pret"]

        self.liste_joueurs.configure(state="normal")
        self.liste_joueurs.delete("1.0", "end")
        for p in prets:
            self.liste_joueurs.insert("end", f"✓ {p}\n")
        self.liste_joueurs.configure(state="disabled")

        if not self.partie_lancee:
            questions = partie.get("questions")
            if len(prets) >= 2 and questions:
                self.btn_lancer.configure(state="normal")
                self.label_statut.configure(
                    text=f"{len(prets)} joueurs prêts — tu peux lancer !",
                    text_color="#2ecc71")
            else:
                self.btn_lancer.configure(state="disabled")
                if not questions:
                    self.label_statut.configure(
                        text="En attente des questions...", text_color="gray")
                else:
                    self.label_statut.configure(
                        text=f"En attente ({len(prets)}/2 joueurs)...",
                        text_color="gray")

    def maj_reponses(self):
        """Met à jour l'affichage des réponses reçues."""
        partie  = state.parties.get(self.code, {})
        prets   = [p for p, s in partie.get("joueurs_presents", {}).items()
                   if s == "pret"]
        nb_rep  = len(partie.get("reponses_tour", {}))
        self.label_reponses.configure(
            text=f"Réponses : {nb_rep}/{len(prets)}")

    def lancer_partie(self):
        """Lance la partie — publie la première question."""
        self.partie_lancee = True
        self.btn_lancer.configure(state="disabled")
        self.btn_terminer.configure(state="normal")
        partie = state.parties[self.code]
        prets  = [p for p, s in partie["joueurs_presents"].items() if s == "pret"]
        for p in prets:
            partie["scores"].setdefault(p, {"correct": 0, "total": 0})
        pub_module.publier_etat(self.pub, self.code, "question")
        self.afficher_question()

    def afficher_question(self):
        """Publie et affiche la question en cours."""
        partie = state.parties[self.code]
        partie["reponses_tour"].clear()
        pub_module.publier_recap(self.pub, self.code, {})

        idx = partie["question_index"]
        q = partie["questions"][idx]
        q["num_affiche"] = partie["question_index"] + 1

        pub_module.publier_question(self.pub, self.code, q)
        pub_module.publier_etat(self.pub, self.code, "question")

        nb_total = len(partie["questions"])
        num_affiche = partie["question_index"] + 1
        self.label_question.configure(
            text=f"Q{num_affiche}/{nb_total} : {q['question']}")
        self.label_reponses.configure(text="Réponses : 0")
        self.label_correction.configure(text="")

        # Lance le timer dans un thread séparé
        self.timer_thread = threading.Thread(
            target=self.attendre_reponses, args=(q,), daemon=True)
        self.timer_thread.start()

    def attendre_reponses(self, q):
        """Attend les réponses des joueurs pendant 15 secondes."""
        timer  = q.get("timer", 15)
        debut  = time.time()
        partie = state.parties[self.code]

        while time.time() - debut < timer:
            prets  = [p for p, s in partie["joueurs_presents"].items() if s == "pret"]
            nb_rep = len(partie["reponses_tour"])
            if nb_rep >= len(prets):
                break
            time.sleep(0.5)

        # Affiche la correction
        self.after(0, lambda: self.afficher_correction(q))

    def afficher_correction(self, q):
        """Calcule et publie la correction."""
        partie = state.parties[self.code]
        bonne  = q["reponse"]
        texte  = q["choix"][bonne]
        prets  = [p for p, s in partie["joueurs_presents"].items() if s == "pret"]

        # Calcule les scores
        for p in prets:
            rep = partie["reponses_tour"].get(p)
            partie["scores"][p]["total"] += 1
            if rep == bonne:
                partie["scores"][p]["correct"] += 1

        pub_module.publier_correction(
            self.pub, self.code, bonne, texte,
            partie["reponses_tour"].copy())
        pub_module.publier_recap(
            self.pub, self.code, partie["reponses_tour"].copy())

        # Affiche les scores actuels
        scores_txt = ""
        for p in prets:
            s = partie["scores"][p]
            scores_txt += f"{p}: {s['correct']}/{s['total']}  "
        self.label_correction.configure(
            text=f"✅ Bonne réponse : {bonne}. {texte}")
        self.label_scores.configure(text=scores_txt)

        # Attend 5 secondes puis passe à la suite
        self.after(5000, lambda: self.apres_correction(q))

    def apres_correction(self, q):
        """Passe à la question suivante ou termine la partie."""
        partie = state.parties[self.code]
        partie["question_index"] += 1

        if partie["question_index"] < len(partie["questions"]):
            self.afficher_question()
        else:
            self.terminer_partie_fin()

    def terminer_partie_fin(self):
        """Termine la partie normalement et envoie les scores finaux."""
        partie     = state.parties[self.code]
        prets      = [p for p, s in partie["joueurs_presents"].items() if s == "pret"]
        nb_q       = len(partie["questions"])
        classement = []

        for p in prets:
            s   = partie["scores"].get(p, {"correct": 0, "total": nb_q})
            pct = round((s["correct"] / nb_q) * 100, 1) if nb_q > 0 else 0
            classement.append({
                "pseudo":  p,
                "correct": s["correct"],
                "total":   nb_q,
                "pct":     pct
            })
        classement.sort(key=lambda x: x["correct"], reverse=True)

        pub_module.publier_scores(self.pub, self.code, classement)
        pub_module.publier_etat(self.pub, self.code, "fin")

        # Affiche le classement
        txt = "🏆 Classement :\n"
        medailles = {0: "🥇", 1: "🥈", 2: "🥉"}
        for i, j in enumerate(classement):
            txt += f"{medailles.get(i, f'{i+1}.')} {j['pseudo']} — {j['correct']}/{j['total']} ({j['pct']}%)\n"
        self.label_scores.configure(text=txt)
        self.label_correction.configure(text="")
        self.btn_terminer.configure(state="disabled")
        self.partie_lancee = False
        self.app.partie_terminee(self.code)

    def terminer_partie(self):
        """Termine la partie prématurément."""
        pub_module.publier_etat(self.pub, self.code, "fin")
        self.terminer_partie_fin()

    def deconnecter(self):
        """Déconnecte proprement les clients MQTT."""
        self.pub.publish(
            state.topic(self.code, "presence/animateur"), "offline", qos=1, retain=True)
        time.sleep(0.2)
        self.pub.loop_stop()
        self.pub.disconnect()
        self.sub.loop_stop()
        self.sub.disconnect()


class AnimateurApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quiz MQTT — Animateur")
        self.geometry("1400x800")
        self.resizable(True, True)
        self.parties_actives = {}  # code : PartieFrame

        # Titre
        ctk.CTkLabel(self, text="🎯 Quiz MQTT — Animateur",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        # Bouton nouvelle partie
        self.btn_nouvelle = ctk.CTkButton(self, text="➕ Nouvelle partie",
                                           command=self.creer_partie,
                                           width=200, height=40,
                                           font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_nouvelle.pack(pady=5)

        # Création frame
        self.frame_creation = ctk.CTkFrame(self)
        self.frame_creation.pack(pady=5)

        ctk.CTkLabel(self.frame_creation,
                     text="Nombre de questions :",
                     font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=10, pady=10)

        self.entry_nb_questions = ctk.CTkEntry(self.frame_creation, width=80,
                                                placeholder_text="ex: 5")
        self.entry_nb_questions.grid(row=0, column=1, padx=10)

        self.btn_confirmer = ctk.CTkButton(self.frame_creation, text="Confirmer",
                                            command=self.confirmer_creation,
                                            width=120, height=35)
        self.btn_confirmer.grid(row=0, column=2, padx=10)

        self.label_erreur_creation = ctk.CTkLabel(self.frame_creation, text="",
                                                   text_color="red",
                                                   font=ctk.CTkFont(size=12))
        self.label_erreur_creation.grid(row=1, column=0, columnspan=3)

        self.frame_creation.pack_forget()

        # Grille des parties
        self.frame_parties = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_parties.pack(fill="both", expand=True, padx=20, pady=10)

        self.frame_parties.columnconfigure(0, weight=1)
        self.frame_parties.columnconfigure(1, weight=1)
        self.frame_parties.rowconfigure(0, weight=1)
        self.frame_parties.rowconfigure(1, weight=1)

    def creer_partie(self):
        """Affiche le formulaire de création de partie."""
        if len(self.parties_actives) >= MAX_PARTIES:
            return
        self.frame_creation.pack(pady=5)
        self.entry_nb_questions.delete(0, "end")
        self.label_erreur_creation.configure(text="")

    def confirmer_creation(self):
        """Valide la création d'une nouvelle partie."""
        try:
            nb = int(self.entry_nb_questions.get().strip())
        except ValueError:
            self.label_erreur_creation.configure(
                text="Entre un nombre valide !")
            return

        # Charge les questions pour vérifier le max
        with open("questions.json", "r", encoding="utf-8") as f:
            toutes = json.load(f)

        if nb <= 0:
            self.label_erreur_creation.configure(
                text="Le nombre doit être supérieur à 0 !")
            return

        if nb > len(toutes):
            self.label_erreur_creation.configure(
                text=f"Maximum {len(toutes)} questions disponibles !")
            return

        # Génère un code unique
        code = state.generer_code()
        while code in self.parties_actives:
            code = state.generer_code()

        # Initialise la partie dans le state
        state.nouvelle_partie(code, [])
        state.parties[code]["nb_questions"] = nb

        # Crée le cadre de la partie
        position = len(self.parties_actives)
        row = position // 2
        col = position % 2

        frame = PartieFrame(self.frame_parties, code, self,
                            border_width=1, corner_radius=10)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        frame.setup_mqtt()

        self.parties_actives[code] = frame
        self.frame_creation.pack_forget()

        # Cache le bouton si 4 parties
        if len(self.parties_actives) >= MAX_PARTIES:
            self.btn_nouvelle.pack_forget()

        # Affiche le code à donner aux joueurs
        self.afficher_code(code)

    def afficher_code(self, code):
        """Affiche une popup avec le code de la partie."""
        popup = ctk.CTkToplevel(self)
        popup.title("Code de la partie")
        popup.geometry("300x150")
        popup.grab_set()

        ctk.CTkLabel(popup, text="Code à donner aux joueurs :",
                     font=ctk.CTkFont(size=14)).pack(pady=15)
        ctk.CTkLabel(popup, text=code,
                     font=ctk.CTkFont(size=32, weight="bold"),
                     text_color="#f0a500").pack()
        ctk.CTkButton(popup, text="OK", command=popup.destroy,
                      width=100).pack(pady=15)

    def partie_terminee(self, code):
        """Appelé quand une partie est terminée — réaffiche le bouton nouvelle partie."""
        if len(self.parties_actives) >= MAX_PARTIES:
            self.btn_nouvelle.pack(pady=5)

    def on_closing(self):
        """Déconnecte proprement toutes les parties."""
        for frame in self.parties_actives.values():
            frame.deconnecter()
        self.destroy()


import threading

def lancer():
    app = AnimateurApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

thread = threading.Thread(target=lancer, daemon=True)
thread.start()