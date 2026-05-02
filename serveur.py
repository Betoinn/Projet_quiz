# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 15:01:28 2026

@author: Utilisateur
"""

import paho.mqtt.client as paho
import json
import random
import shared_state as state

BROKER = "broker.emqx.io"
PORT   = 1883

# Chargement de toutes les questions depuis le json
with open("questions.json", "r", encoding="utf-8") as f:
    TOUTES_QUESTIONS = json.load(f)

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[SERVEUR] Connecté : {rc}")
    # Souscrit aux demandes de questions de l'animateur (de toutes parties)
    client.subscribe(state.topic_serveur("demande/+"), qos=1)
    # Souscrit aux scores de toutes les parties pour calculer les stats
    client.subscribe(f"{state.PREFIX}/quiz/+/scores", qos=1)

def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode()

    if not payload:
        return

    # Demande de questions 
    if "serveur/demande" in topic:
        code = topic.split("/")[-1]
        try:
            data = json.loads(payload)
            nb   = data["nb_questions"]

            # Vérifie que le nb demandé ne dépasse pas le total
            if nb > len(TOUTES_QUESTIONS):
                erreur = json.dumps({
                    "erreur": True,
                    "message": f"Nombre trop élevé — max {len(TOUTES_QUESTIONS)} questions disponibles"
                })
                client.publish(state.topic_serveur(f"questions/{code}"),
                               erreur, qos=1)
                print(f"[SERVEUR] Erreur : {nb} > {len(TOUTES_QUESTIONS)}")
                return

            # Pioche aléatoirement le nb de questions dans le json
            questions = random.sample(TOUTES_QUESTIONS, nb)

            # Timer de 15 secondes pour chaque question
            for q in questions:
                q["timer"] = 15

            # Publie les questions pour l'animateur
            payload_questions = json.dumps({
                "erreur":    False,
                "questions": questions
            })
            client.publish(state.topic_serveur(f"questions/{code}"),
                           payload_questions, qos=1)
            print(f"[SERVEUR] {nb} questions envoyées pour la partie {code}")

        except Exception as e:
            print(f"[SERVEUR] Erreur demande : {e}")

    # Scores finaux reçus et calcul des stats 
    elif "/quiz/" in topic and "/scores" in topic:
        code = topic.split("/")[3]
        try:
            data       = json.loads(payload)
            classement = data["classement"]

            # Calcule les stats pour chaque joueur
            stats = []
            for j in classement:
                stats.append({
                    "pseudo":   j["pseudo"],
                    "correct":  j["correct"],
                    "total":    j["total"],
                    "pct":      j["pct"]
                })

            # Publie les stats finales
            payload_stats = json.dumps({
                "classement": classement,
                "stats":      stats
            })
            client.publish(state.topic_serveur(f"stats/{code}"),
                           payload_stats, qos=1, retain=True)
            print(f"[SERVEUR] Stats calculées pour la partie {code}")

        except Exception as e:
            print(f"[SERVEUR] Erreur stats : {e}")

def on_disconnect(client, userdata, flags, rc, properties=None):
    print(f"[SERVEUR] Déconnecté : {rc}")

# Lancement du serveur 
client = paho.Client(
    callback_api_version=paho.CallbackAPIVersion.VERSION2,
    client_id="serveur-quiz-NBEK-2026",
    protocol=paho.MQTTv5
)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect

client.connect(BROKER, PORT, clean_start=True)
print("[SERVEUR] Démarrage...")
print(f"[SERVEUR] {len(TOUTES_QUESTIONS)} questions disponibles")
import threading

def lancer_serveur():
    client.loop_forever()

thread = threading.Thread(target=lancer_serveur, daemon=True)
thread.start()