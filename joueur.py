import customtkinter as ctk
import time
import json
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
 
ICONES = {
    "A": "▲",
    "B": "◆",
    "C": "●",
    "D": "■"
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
 
        # ── FRAME QUESTION ─────────────────────────────────────
        self.frame_question = ctk.CTkFrame(self)
 
        # Barre de progression du timer
        self.frame_timer = ctk.CTkFrame(self.frame_question,
                                         fg_color="transparent")
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
        self.frame_boutons = ctk.CTkFrame(self.frame_question,
                                           fg_color="transparent")
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
                text=f"{ICONES[lettre]}  {lettre}",
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
                                            font=ctk.CTkFont(size=36,
                                                             weight="bold"))
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
                                          command=self.on_closing,
                                          width=150, height=40,
                                          fg_color="#e74c3c",
                                          hover_color="#c0392b",
                                          font=ctk.CTkFont(size=14))
        self.btn_quitter.pack(pady=20)
 
    def rejoindre(self):
        """Valide le pseudo et le code puis se connecte."""
        pseudo = self.entry_pseudo.get().strip()
        code   = self.entry_code.get().strip().upper()
 
        if not pseudo:
            self.label_erreur.configure(text="Entre un pseudo !")
            return
        if not code:
            self.label_erreur.configure(text="Entre un code de partie !")
            return
        if len(code) != 6:
            self.label_erreur.configure(text="Le code doit faire 6 caracteres !")
            return
 
        self.pseudo = pseudo
        self.code   = code
 
        # Reinitialise le state joueur
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
            # Revient sur la frame attente et affiche le message
            self.frame_question.pack_forget()
            self.frame_correction.pack_forget()
            self.frame_scores.pack_forget()
            self.frame_attente.pack(fill="both", expand=True, padx=40, pady=40)
            self.label_animateur_statut.configure(
                text="L'animateur s'est deconnecte. En attente de reconnexion...")
        elif etat == "animateur_online":
            # Efface le message quand l'animateur revient
            self.label_animateur_statut.configure(text="")
            self.label_code_affiche.configure(
                text=f"Partie : {self.code}", text_color="gray")
 
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
 
        self.label_num_q.configure(text=f"Question {q.get('numero', '?')}")
        self.label_question_joueur.configure(text=q["question"])
        self.label_attente_correction.configure(text="")
 
        # Met a jour les boutons avec les choix
        for lettre, btn in self.btns_reponse.items():
            btn.configure(
                text=f"{ICONES[lettre]}  {lettre}. {q['choix'][lettre]}",
                state="normal",
                fg_color=COULEURS[lettre])
 
        # Lance la barre de progression
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
 
        # Couleur selon le temps restant
        if progression > 0.3:
            self.barre_timer.configure(progress_color="#2ecc71")  # vert
        elif progression > 0.1:
            self.barre_timer.configure(progress_color="#f0a500")  # jaune
        else:
            self.barre_timer.configure(progress_color="#e74c3c")  # rouge
 
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
 
        # Grise les autres boutons
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
 
        # Affiche si bonne ou mauvaise reponse
        if not state.reponse_envoyee or ma_rep is None:
            self.label_resultat.configure(text="Temps ecoule !",
                                           text_color="#e74c3c")
        elif ma_rep == bonne:
            self.label_resultat.configure(text="Bonne reponse !",
                                           text_color="#2ecc71")
        else:
            self.label_resultat.configure(text="Mauvaise reponse !",
                                           text_color="#e74c3c")
 
        self.label_bonne_rep.configure(
            text=f"Bonne reponse : {bonne}. {texte}",
            text_color="#2ecc71")
 
        if ma_rep and ma_rep != bonne:
            self.label_ma_reponse.configure(
                text=f"Ta reponse : {ma_rep}",
                text_color="#e74c3c")
        else:
            self.label_ma_reponse.configure(text="")
 
        # Attend 5 secondes puis retourne en attente
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
 
        # Affiche uniquement le score du joueur
        mon_score = next(
            (j for j in classement if j["pseudo"] == self.pseudo), None)
        if mon_score:
            self.label_mon_score.configure(
                text=f"Ton score : {mon_score['correct']}/{mon_score['total']} ({mon_score['pct']}%)")
 
        # Affiche le classement sans pourcentages
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
 
 
if __name__ == "__main__":
    app = JoueurApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()