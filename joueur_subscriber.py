# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 08:41:33 2026

@author: Utilisateur

joueur_subscriber.py
Écoute l'état du jeu, les questions, corrections et scores.
Démarre dans un thread depuis joueur_publisher.py.
"""

import paho.mqtt.client as paho
import json
import shared_state as state

# ─────────────────────────────────────────────────
#  CALLBACKS
# ─────────────────────────────────────────────────
def on_connect(client, userdata, flags, reason_code, properties):
    pseudo = userdata["pseudo"]
    print(f"[SUB joueur] Connecté : {reason_code}")
    client.subscribe(state.topic("state"),      qos=1)
    client.subscribe(state.topic("question"),   qos=1)
    client.subscribe(state.topic("correction"), qos=1)
    client.subscribe(state.topic("scores"),     qos=1)

def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode()
    pseudo  = userdata["pseudo"]

    if not payload:
        return

    # ── État global ──────────────────────────────
    if topic == state.topic("state"):
        state.state = payload
        if payload == "attente":
            print("\n  ⏳ En attente du lancement de la partie...")
        elif payload == "question":
            state.reponse_envoyee = False
        elif payload == "fin":
            print("\n  🏁 La partie est terminée !")

    # ── Question ─────────────────────────────────
    elif topic == state.topic("question"):
        if msg.retain and state.state != "question":
            return  # ignorer retained si pas encore en phase question
        state.question_active = json.loads(payload)
        _afficher_question(state.question_active)

    # ── Correction ───────────────────────────────
    elif topic == state.topic("correction"):
        if msg.retain:
            return
        data      = json.loads(payload)
        bonne     = data["bonne_reponse"]
        texte     = data["texte_reponse"]
        ma_rep    = data["reponses"].get(pseudo)

        print(f"\n  ✅ Bonne réponse : {bonne}. {texte}")
        if ma_rep is None:
            print("  ⏰ Tu n'as pas répondu à temps !")
        elif ma_rep == bonne:
            print("  🟢 Bonne réponse !")
        else:
            print(f"  🔴 Mauvaise réponse (tu avais répondu : {ma_rep})")

    # ── Scores finaux ─────────────────────────────
    elif topic == state.topic("scores"):
        if state.scores_recus:
            return
        state.scores_recus = True
        data = json.loads(payload)
        print(f"\n{'═'*40}")
        print("  🏆 CLASSEMENT FINAL")
        print(f"{'═'*40}")
        medailles = {1: "🥇", 2: "🥈", 3: "🥉"}
        for rank, j in enumerate(data["classement"], 1):
            moi = " ← toi" if j["pseudo"] == pseudo else ""
            print(f"  {medailles.get(rank, str(rank)+'.')} {j['pseudo']} — {j['correct']}/{j['total']} ({j['pct']}%){moi}")

def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[SUB joueur] Déconnecté (code={reason_code}), reconnexion...")

# ─────────────────────────────────────────────────
#  AFFICHAGE QUESTION
# ─────────────────────────────────────────────────
def _afficher_question(q):
    print(f"\n{'─'*40}")
    print(f"  ❓ Question {q['numero']} ({q.get('timer', 20)}s) :")
    print(f"  {q['question']}")
    print()
    for lettre, texte in q["choix"].items():
        print(f"    {lettre}. {texte}")
    print()
    print("  Ta réponse (A/B/C/D) : ", end="", flush=True)

# ─────────────────────────────────────────────────
#  CONSTRUCTION DU CLIENT (appelé depuis publisher)
# ─────────────────────────────────────────────────
def build_client(pseudo):
    client = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id=f"joueur-sub-{pseudo}-EK",
        userdata={"pseudo": pseudo},
        protocol=paho.MQTTv5
    )
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect
    return client
