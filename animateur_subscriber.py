# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 08:41:28 2026

@author: Utilisateur

animateur_publisher.py — POINT D'ENTRÉE ANIMATEUR
Lance : python animateur_publisher.py
"""

import paho.mqtt.client as paho
import json
import time

import shared_state as state
import animateur_subscriber as sub_module

# ─────────────────────────────────────────────────
#  CHARGEMENT DES QUESTIONS
# ─────────────────────────────────────────────────
with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

TIMER_DEFAUT = 20   # secondes par question si non spécifié

# ─────────────────────────────────────────────────
#  CALLBACKS PUBLISHER
# ─────────────────────────────────────────────────
def on_connect_pub(client, userdata, flags, reason_code, properties):
    print(f"[PUB animateur] Connecté : {reason_code}")
    client.publish(state.topic("presence/animateur"), "online", qos=1, retain=True)

def on_disconnect_pub(client, userdata, flags, reason_code, properties):
    print(f"[PUB animateur] Déconnecté (code={reason_code})")

# ─────────────────────────────────────────────────
#  CLIENT PUBLISHER
# ─────────────────────────────────────────────────
pub = paho.Client(
    callback_api_version=paho.CallbackAPIVersion.VERSION2,
    client_id="animateur-pub-EK",
    protocol=paho.MQTTv5
)
pub.will_set(state.topic("presence/animateur"), "offline", qos=1, retain=True)
pub.on_connect    = on_connect_pub
pub.on_disconnect = on_disconnect_pub
pub.connect(state.BROKER, state.PORT)
pub.loop_start()

# ─────────────────────────────────────────────────
#  CLIENT SUBSCRIBER (démarre en parallèle)
# ─────────────────────────────────────────────────
sub = sub_module.build_client()
sub.connect(state.BROKER, state.PORT)
sub.loop_start()

time.sleep(1)

# ─────────────────────────────────────────────────
#  LOBBY
# ─────────────────────────────────────────────────
pub.publish(state.topic("state"), "attente", qos=1, retain=True)

print("╔══════════════════════════════════╗")
print("║     QUIZ MQTT — ANIMATEUR        ║")
print("╚══════════════════════════════════╝")
print(f"  Broker  : {state.BROKER}:{state.PORT}")
print(f"  Préfixe : {state.PREFIX}/quiz/\n")
print(f"  {len(QUESTIONS)} questions chargées depuis questions.json\n")
print("  En attente d'au moins 2 joueurs...\n")

while True:
    prets = [p for p, s in state.joueurs_presents.items() if s == "pret"]
    if len(prets) >= 2:
        print(f"\n  Joueurs prêts : {', '.join(prets)}")
        conf = input("  ▶  Lancer la partie ? (o/n) : ").strip().lower()
        if conf == "o":
            break
    time.sleep(1)

# Initialisation scores
for pseudo in prets:
    state.scores.setdefault(pseudo, {"correct": 0, "total": 0})

# ─────────────────────────────────────────────────
#  BOUCLE DES QUESTIONS
# ─────────────────────────────────────────────────
for i, q in enumerate(QUESTIONS):
    state.reponses_tour.clear()

    timer = q.get("timer", TIMER_DEFAUT)

    print(f"\n{'─'*40}")
    print(f"  Question {i+1}/{len(QUESTIONS)} : {q['question']}")
    for lettre, texte in q["choix"].items():
        print(f"    {lettre}. {texte}")

    # Publier question + état
    pub.publish(state.topic("question"), json.dumps(q),   qos=1, retain=True)
    pub.publish(state.topic("state"),    "question",       qos=1, retain=True)

    # Attendre réponses ou timeout
    debut = time.time()
    while time.time() - debut < timer:
        joueurs_actifs = [p for p in prets if state.joueurs_presents.get(p) == "pret"]
        if len(state.reponses_tour) >= len(joueurs_actifs):
            break
        remaining = int(timer - (time.time() - debut))
        print(f"\r  ⏳ {remaining}s — {len(state.reponses_tour)}/{len(joueurs_actifs)} réponses reçues  ",
              end="", flush=True)
        time.sleep(0.5)
    print()

    # ── Correction ───────────────────────────────
    bonne = q["reponse"]
    texte_bonne = q["choix"][bonne]

    for pseudo in prets:
        rep = state.reponses_tour.get(pseudo)
        state.scores[pseudo]["total"] += 1
        if rep == bonne:
            state.scores[pseudo]["correct"] += 1

    correction = {
        "bonne_reponse":  bonne,
        "texte_reponse":  texte_bonne,
        "reponses":       state.reponses_tour.copy()
    }

    pub.publish(state.topic("correction"),     json.dumps(correction),              qos=1, retain=True)
    pub.publish(state.topic("reponses_recap"), json.dumps(state.reponses_tour.copy()), qos=1, retain=True)
    pub.publish(state.topic("state"),          "correction",                        qos=1, retain=True)

    print(f"  ✅ Bonne réponse : {bonne}. {texte_bonne}")
    for pseudo, rep in state.reponses_tour.items():
        icone = "🟢" if rep == bonne else "🔴"
        print(f"    {icone} {pseudo} → {rep}")
    for pseudo in prets:
        if pseudo not in state.reponses_tour:
            print(f"    ⏰ {pseudo} → pas de réponse")

    time.sleep(5)

# ─────────────────────────────────────────────────
#  SCORES FINAUX
# ─────────────────────────────────────────────────
nb_questions = len(QUESTIONS)
classement = []
for pseudo, s in state.scores.items():
    pct = round((s["correct"] / nb_questions) * 100, 1)
    classement.append({
        "pseudo":  pseudo,
        "correct": s["correct"],
        "total":   nb_questions,
        "pct":     pct
    })
classement.sort(key=lambda x: x["correct"], reverse=True)

pub.publish(state.topic("scores"), json.dumps({"classement": classement}), qos=1, retain=True)
pub.publish(state.topic("state"),  "fin",                                  qos=1, retain=True)

print(f"\n{'═'*40}")
print("  🏆 CLASSEMENT FINAL")
print(f"{'═'*40}")
medailles = {1: "🥇", 2: "🥈", 3: "🥉"}
for rank, j in enumerate(classement, 1):
    print(f"  {medailles.get(rank, f'{rank}.')} {j['pseudo']} — {j['correct']}/{j['total']} ({j['pct']}%)")

# ── Nettoyage ────────────────────────────────────
pub.publish(state.topic("presence/animateur"), "offline", qos=1, retain=True)
time.sleep(1)
pub.loop_stop()
pub.disconnect()
sub.loop_stop()
sub.disconnect()
