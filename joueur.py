import customtkinter as ctk
import time
import json
import threading
import paho.mqtt.client as paho
import shared_state as state
import joueur_publisher as pub_module
import joueur_subscriber as sub_module

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COULEURS = {
    "A": "#e74c3c",
    "B": "#3498db",
    "C": "#f39c12",
    "D": "#2ecc71"
}


class JoueurApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Quiz MQTT — Joueur")
        self.geometry("800x600")
        self.resizable(False, False)
        self.pseudo = ""
        self.code   = ""
        self.pub    = None
        self.sub    = None

        # ── FRAME CONNEXION ────────────────────────────────────
        self.frame_connexion = ctk.CTkFrame(self)
        self.frame_connexion.pack(fill="both", expand=True, padx=60, pady=60)

        ctk.CTkLabel(self.frame_connexion, text="Quiz MQTT",
                     font=ctk.CTkFont(size=32, weight="bold")).pack(pady=20)

        ctk.CTkLabel(self.frame_connexion, text="Ton pseudo :",
                     font=ctk.CTkFont(size=15)).pack(pady=5)
        self.entry_pseudo = ctk.CTkEntry(self.frame_connexion, width=300,
                                          height=45, font=ctk.CTkFont(size=15),
                                          placeholder_text="Pseudo...")
        self.entry_pseudo.pack(pady=5)

        ctk.CTkLabel(self.frame_connexion, text="Code de la partie :",
                     font=ctk.CTkFont(size=15)).pack(pady=5)
        self.entry_code = ctk.CTkEntry(self.frame_connexion, width=300,
                                        height=45, font=ctk.CTkFont(size=15),
                                        placeholder_text="Code...")
        self.entry_code.pack(pady=5)

        self.btn_rejoindre = ctk.CTkButton(self.frame_connexion, text="Rejoindre",
                                            command=self.rejoindre,
                                            width=200, height=45,
                                            font=ctk.CTkFont(size=15, weight="bold"))
        self.btn_rejoindre.pack(pady=15)

        self.label_erreur = ctk.CTkLabel(self.frame_connexion, text="",
                                          text_color="red",
                                          font=ctk.CTkFont(size=13))
        self.label_erreur.pack()

        # ── FRAME ATTENTE ──────────────────────────────────────
        self.frame_attente = ctk.CTkFrame(self)

        ctk.CTkLabel(self.frame_attente, text="Quiz MQTT",
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=30)

        self.label_pseudo_affiche = ctk.CTkLabel(self.frame_attente, text="",
                                                  font=ctk.CTkFont(size=16))
        self.label_pseudo_affiche.pack(pady=5)

        self.label_code_affiche = ctk.CTkLabel(self.frame_attente, text="",
                                                font=ctk.CTkFont(size=14),
                                                text_color="gray")
        self.label_code_affiche.pack(pady=5)

        ctk.CTkLabel(self.frame_attente, text="En attente du lancement...",
                     font=ctk.CTkFont(size=15), text_color="gray").pack(pady=20)

        self.label_animateur_statut = ctk.CTkLabel(self.frame_attente, text="",
                                                    font=ctk.CTkFont(size=13),
                                                    text_color="red")
        self.label_animateur_statut.pack(pady=5)

        # ── FRAME PAUSE ────────────────────────────────────────
        self.frame_pause = ctk.CTkFrame(self)

        ctk.CTkLabel(self.frame_pause, text="Partie en pause",
                     font=ctk.CTkFont(size=28, weight="bold")).pack(pady=30)
        ctk.CTkLabel(self.frame_pause, text="L'animateur a mis la partie en pause.",
                     font=ctk.CTkFont(size=15), text_color="gray").pack(pady=10)
        ctk.CTkLabel(self.frame_pause, text="En attente de la reprise...",
                     font=ctk.CTkFont(size=14), text_color="gray").pack(pady=5)

        # ── FRAME QUESTION ─────────────────────────────────────
        self.frame_question = ctk.CTkFrame(self)

        self.frame_timer = ctk.CTkFrame(self.frame_question, fg_color="transparent")
        self.frame_timer.pack(fill="x", padx=20, pady=10)

        self.barre_timer = ctk.CTkProgressBar(self.frame_timer, width=700,
                                               height=20, corner_radius=5)
        self.barre_timer.pack()
        self.barre_timer.set(1)
        self.barre_timer.configure(progress_color="#2ecc71")

        self.label_num_q = ctk.CTkLabel(self.frame_question, text="",
                                         font=ctk.CTkFont(size=13),
                                         text_color="gray")
        self.label_num_q.pack(pady=3)

        self.label_question_joueur = ctk.CTkLabel(self.frame_question, text="",
                                                   font=ctk.CTkFont(size=20,
                                                                     weight="bold"),
                                                   wraplength=700)
        self.label_question_joueur.pack(pady=15)

        # Grille 2x2 style Kahoot
        self.frame_boutons = ctk.CTkFrame(self.frame_question, fg_color="transparent")
        self.frame_boutons.pack(fill="both", expand=True, padx=20, pady=10)
        self.frame_boutons.columnconfigure(0, weight=1)
        self.frame_boutons.columnconfigure(1, weight=1)
        self.frame_boutons.rowconfigure(0, weight=1)
        self.frame_boutons.rowconfigure(1, weight=1)

        self.btns_reponse = {}
        positions = {"A": (0,0), "B": (0,1), "C": (1,0), "D": (1,1)}
        for lettre, (row, col) in positions.items():
            btn = ctk.CTkButton(
                self.frame_boutons,
                text=f"{lettre}",
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color=COULEURS[lettre],
                hover_color=COULEURS[lettre],
                height=100, corner_radius=12,
                command=lambda l=lettre: self.envoyer_reponse(l)
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.btns_reponse[lettre] = btn

        self.label_attente_correction = ctk.CTkLabel(
            self.frame_question, text="",
            font=ctk.CTkFont(size=14), text_color="gray")
        self.label_attente_correction.pack(pady=5)

        # ── FRAME CORRECTION ───────────────────────────────────
        self.frame_correction = ctk.CTkFrame(self)

        self.label_resultat = ctk.CTkLabel(self.frame_correction, text="",
                                            font=ctk.CTkFont(size=36, weight="bold"))
        self.label_resultat.pack(pady=30)

        self.label_bonne_rep = ctk.CTkLabel(self.frame_correction, text="",
                                             font=ctk.CTkFont(size=18))
        self.label_bonne_rep.pack(pady=10)

        self.label_ma_reponse = ctk.CTkLabel(self.frame_correction, text="",
                                              font=ctk.CTkFont(size=15),
                                              text_color="gray")
        self.label_ma_reponse.pack(pady=5)

        # ── FRAME SCORES FINAUX ────────────────────────────────
        self.frame_scores = ctk.CTkFrame(self)

        ctk.CTkLabel(self.frame_scores, text="Resultats finaux",
                     font=ctk.CTkFont(size=26, weight="bold")).pack(pady=20)

        self.label_mon_score = ctk.CTkLabel(self.frame_scores, text="",
                                             font=ctk.CTkFont(size=18),
                                             text_color="#f0a500")
        self.label_mon_score.pack(pady=10)

        self.label_classement = ctk.CTkLabel(self.frame_scores, text="",
                                              font=ctk.CTkFont(size=15))
        self.label_classement.pack(pady=10)

        self.btn_quitter = ctk.CTkButton(self.frame_scores, text="Quitter",
                                          command=lambda: self.on_closing(),
                                          width=150, height=40,
                                          fg_color="#e74c3c",
                                          hover_color="#c0392b",
                                          font=ctk.CTkFont(size=14))
        self.btn_quitter.pack(pady=20)

    def rejoindre(self):
        """Valide le pseudo et le code puis lance la verification."""
        pseudo = self.entry_pseudo.get().strip()
        code   = self.entry_code.get().strip().upper()

        if not pseudo:
            self.label_erreur.configure(text="Entre un pseudo !", text_color="red")
            return
        if not code:
            self.label_erreur.configure(text="Entre un code de partie !", text_color="red")
            return
        if len(code) != 6:
            self.label_erreur.configure(text="Le code doit faire 6 caracteres !", text_color="red")
            return

        # Vérifie si la partie existe via MQTT
        self.label_erreur.configure(text="Verification...", text_color="gray")
        self.btn_rejoindre.configure(state="disabled")

        # Lance la vérification dans un thread séparé pour ne pas bloquer l'interface
        t = threading.Thread(target=self.verifier_partie, args=(pseudo, code), daemon=True)
        t.start()

    def verifier_partie(self, pseudo, code):
        """Vérifie si la partie existe en souscrivant temporairement à son état."""
        partie_trouvee = [False]
        etat_recu      = [False]

        def on_connect(c, userdata, flags, rc, properties=None):
            c.subscribe(state.topic(code, "state"), qos=1)

        def on_message(c, userdata, msg):
            payload = msg.payload.decode()
            if payload and payload not in ["fin", ""]:
                partie_trouvee[0] = True
            etat_recu[0] = True
            c.disconnect()

        def on_disconnect(c, userdata, flags, rc, properties=None):
            pass

        client_verif = paho.Client(
            callback_api_version=paho.CallbackAPIVersion.VERSION2,
            client_id=f"verif-{pseudo}-{code}",
            protocol=paho.MQTTv5
        )
        client_verif.on_connect    = on_connect
        client_verif.on_message    = on_message
        client_verif.on_disconnect = on_disconnect
        client_verif.connect(state.BROKER, state.PORT, clean_start=True)
        client_verif.loop_start()

        # Attend 2 secondes max pour recevoir une réponse
        timeout = 2
        debut   = time.time()
        while not etat_recu[0] and time.time() - debut < timeout:
            time.sleep(0.1)

        client_verif.loop_stop()

        if partie_trouvee[0]:
            self.after(0, lambda: self._confirmer_rejoindre(pseudo, code))
        else:
            self.after(0, lambda: self._partie_inexistante())

    def _partie_inexistante(self):
        """Affiche le message d'erreur si la partie n'existe pas."""
        self.label_erreur.configure(text="Partie inexistante !", text_color="red")
        self.btn_rejoindre.configure(state="normal")

    def _confirmer_rejoindre(self, pseudo, code):
        """Confirme et rejoint la partie."""
        self.pseudo = pseudo
        self.code   = code

        state.joueur_state         = "attente"
        state.joueur_code          = code
        state.question_active      = None
        state.reponse_envoyee      = False
        state.scores_recus         = False
        state.reponses_tour_joueur = None
        state.correction_active    = None
        state.classement_final     = None

        self.setup_mqtt()
        self.frame_connexion.pack_forget()
        self.frame_attente.pack(fill="both", expand=True, padx=40, pady=40)
        self.label_pseudo_affiche.configure(text=f"Connecte en tant que : {pseudo}")
        self.label_code_affiche.configure(text=f"Partie : {code}")

    def setup_mqtt(self):
        """Initialise et connecte les clients MQTT."""
        self.pub = pub_module.build_client(self.pseudo, self.code)
        self.pub.connect(state.BROKER, state.PORT, clean_start=False)
        self.pub.loop_start()

        self.sub = sub_module.build_client(
            self.pseudo, self.code,
            on_state_change = self.on_state_change,
            on_question     = self.on_question,
            on_correction   = self.on_correction,
            on_scores       = self.on_scores
        )
        self.sub.connect(state.BROKER, state.PORT, clean_start=False)
        self.sub.loop_start()

    def on_state_change(self, etat):
        """Appele quand l'etat de la partie change."""
        self.after(0, lambda: self._traiter_etat(etat))

    def _traiter_etat(self, etat):
        if etat == "fin":
            if not state.scores_recus:
                self.afficher_scores({})
        elif etat == "animateur_offline":
            # Ne rien faire si les scores sont déjà affichés
            if state.scores_recus:
                return
            self.frame_question.pack_forget()
            self.frame_correction.pack_forget()
            self.frame_scores.pack_forget()
            self.frame_attente.pack(fill="both", expand=True, padx=40, pady=40)
            self.label_animateur_statut.configure(
                text="L'animateur s'est deconnecte. En attente de reconnexion...")
        elif etat == "animateur_online":
            self.label_animateur_statut.configure(text="")
            self.label_code_affiche.configure(
                text=f"Partie : {self.code}", text_color="gray")
        elif etat == "pause":
            self.frame_question.pack_forget()
            self.frame_correction.pack_forget()
            self.frame_attente.pack_forget()
            self.frame_pause.pack(fill="both", expand=True, padx=40, pady=40)
        elif etat == "question":
            self.frame_pause.pack_forget()

    def on_question(self, q):
        """Appele quand une nouvelle question arrive."""
        self.after(0, lambda: self.afficher_question(q))

    def on_correction(self, data):
        """Appele quand la correction arrive."""
        self.after(0, lambda: self.afficher_correction(data))

    def on_scores(self, data):
        """Appele quand les scores finaux arrivent."""
        self.after(0, lambda: self.afficher_scores(data))

    def afficher_question(self, q):
        """Affiche la question avec la grille de reponses."""
        self.frame_attente.pack_forget()
        self.frame_correction.pack_forget()
        self.frame_question.pack(fill="both", expand=True, padx=20, pady=10)

        self.label_num_q.configure(
            text=f"Question {state.question_active.get('num_affiche', q.get('numero', '?'))}")
        self.label_question_joueur.configure(text=q["question"])
        self.label_attente_correction.configure(text="")

        for lettre, btn in self.btns_reponse.items():
            btn.configure(
                text=f"{lettre}. {q['choix'][lettre]}",
                state="normal",
                fg_color=COULEURS[lettre])

        timer = q.get("timer", 15)
        self.barre_timer.set(1)
        self.barre_timer.configure(progress_color="#2ecc71")
        self.after(0, lambda: self.maj_barre_timer(timer, timer))

    def maj_barre_timer(self, restant, total):
        """Met a jour la barre de progression du timer."""
        if state.reponse_envoyee or state.joueur_state != "question":
            self.barre_timer.set(0)
            return

        progression = restant / total
        self.barre_timer.set(progression)

        if progression > 0.3:
            self.barre_timer.configure(progress_color="#2ecc71")
        elif progression > 0.1:
            self.barre_timer.configure(progress_color="#f0a500")
        else:
            self.barre_timer.configure(progress_color="#e74c3c")

        if restant <= 0:
            self.barre_timer.set(0)
            for btn in self.btns_reponse.values():
                btn.configure(state="disabled")
            return

        self.after(1000, lambda: self.maj_barre_timer(restant - 1, total))

    def envoyer_reponse(self, lettre):
        """Envoie la reponse du joueur."""
        if state.reponse_envoyee:
            return
        state.reponse_envoyee = True

        pub_module.publier_reponse(self.pub, self.pseudo, self.code, lettre)

        for l, btn in self.btns_reponse.items():
            if l != lettre:
                btn.configure(state="disabled", fg_color="gray")

        self.label_attente_correction.configure(
            text="Reponse envoyee ! En attente de la correction...")

    def afficher_correction(self, data):
        """Affiche la correction pendant 5 secondes."""
        self.frame_question.pack_forget()
        self.frame_correction.pack(fill="both", expand=True, padx=60, pady=60)

        bonne  = data.get("bonne_reponse", "")
        texte  = data.get("texte_reponse", "")
        ma_rep = data.get("reponses", {}).get(self.pseudo)

        if not state.reponse_envoyee or ma_rep is None:
            self.label_resultat.configure(text="Temps ecoule !", text_color="#e74c3c")
        elif ma_rep == bonne:
            self.label_resultat.configure(text="Bonne reponse !", text_color="#2ecc71")
        else:
            self.label_resultat.configure(text="Mauvaise reponse !", text_color="#e74c3c")

        self.label_bonne_rep.configure(
            text=f"Bonne reponse : {bonne}. {texte}",
            text_color="#2ecc71")

        if ma_rep and ma_rep != bonne:
            self.label_ma_reponse.configure(text=f"Ta reponse : {ma_rep}",
                                             text_color="#e74c3c")
        else:
            self.label_ma_reponse.configure(text="")

        self.after(5000, self.apres_correction)

    def apres_correction(self):
        """Retourne en attente apres la correction."""
        if state.joueur_state == "fin":
            return
        self.frame_correction.pack_forget()
        self.frame_attente.pack(fill="both", expand=True, padx=40, pady=40)

    def afficher_scores(self, data):
        """Affiche le classement final."""
        self.frame_correction.pack_forget()
        self.frame_question.pack_forget()
        self.frame_attente.pack_forget()
        self.frame_scores.pack(fill="both", expand=True, padx=40, pady=40)

        classement = data.get("classement", [])

        mon_score = next(
            (j for j in classement if j["pseudo"] == self.pseudo), None)
        if mon_score:
            self.label_mon_score.configure(
                text=f"Ton score : {mon_score['correct']}/{mon_score['total']} ({mon_score['pct']}%)")

        medailles = {0: "1.", 1: "2.", 2: "3."}
        txt = ""
        for i, j in enumerate(classement):
            moi = " <- toi" if j["pseudo"] == self.pseudo else ""
            txt += f"{medailles.get(i, f'{i+1}.')}  {j['pseudo']}{moi}\n"
        self.label_classement.configure(text=txt)

    def on_closing(self):
        """Deconnecte proprement le joueur."""
        if self.pub:
            pub_module.publier_deconnexion(self.pub, self.pseudo, self.code)
            time.sleep(0.3)
            self.pub.loop_stop()
            self.pub.disconnect()
        if self.sub:
            self.sub.loop_stop()
            self.sub.disconnect()
        self.destroy()


app = JoueurApp()
app.protocol("WM_DELETE_WINDOW", app.on_closing)
app.mainloop()