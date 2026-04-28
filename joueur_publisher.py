# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 08:41:32 2026

@author: Utilisateur

joueur_publisher.py — POINT D'ENTRÉE JOUEUR
Lance : python joueur_publisher.py
"""

import paho.mqtt.client as paho
import json
import time

import shared_state as state
import joueur_subscriber as sub_module

# ─────────────────────────────────────────────────
#  PSEUDO
# ─────────────────────────────────────────────────
pseudo = input("Ton pseudo : ").strip()

# ─────────────────────────────────────────────────
#  CALLBACKS PUBLISHER
# ─────────────────────────────────────────────────
def on_connect_pub(client, userdata, flags, reason_code, properties):
    print(f"[PUB joueur] Connecté : {reason_code}")
    # Publier présence "pret" avec retain dès la connexion
    client.publish(state.topic(f"presence/{pseudo}"), "pret", qos=1, retain=True)

def on_disconnect_pub(client, userdata, flags, reason_code, properties):
    print(f"[PUB joueur] Déconnecté (code={reason_code}), reconnexion...")

# ─────────────────────────────────────────────────
#  CLIENT PUBLISHER
# ─────────────────────────────────────────────────
pub = paho.Client(
    callback_api_version=paho.CallbackAPIVersion.VERSION2,
    client_id=f"joueur-pub-{pseudo}-EK",
    protocol=paho.MQTTv5
)
# LWT : si crash → broker publie "offline" automatiquement
pub.will_set(state.topic(f"presence/{pseudo}"), "offline", qos=1, retain=True)
pub.on_connect    = on_connect_pub
pub.on_disconnect = on_disconnect_pub
pub.connect(state.BROKER, state.PORT, clean_start=False)
pub.loop_start()

# ─────────────────────────────────────────────────
#  CLIENT SUBSCRIBER (démarre en parallèle)
# ─────────────────────────────────────────────────
sub = sub_module.build_client(pseudo)
sub.connect(state.BROKER, state.PORT, clean_start=False)
sub.loop_start()

# ─────────────────────────────────────────────────
#  AFFICHAGE
# ─────────────────────────────────────────────────
print("╔══════════════════════════════════╗")
print("║      QUIZ MQTT — JOUEUR          ║")
print("╚══════════════════════════════════╝")
print(f"  Pseudo  : {pseudo}")
print(f"  Broker  : {state.BROKER}:{state.PORT}\n")
print("  En attente du lancement de la partie...\n")

# ─────────────────────────────────────────────────
#  BOUCLE PRINCIPALE
# ─────────────────────────────────────────────────
try:
    while True:
        # Phase question : attendre saisie de la réponse
        if state.state == "question" and state.question_active and not state.reponse_envoyee:
            rep = input("").strip().upper()
            if rep in ["A", "B", "C", "D"]:
                payload = json.dumps({
                    "pseudo":    pseudo,
                    "reponse":   rep,
                    "timestamp": int(time.time())
                })
                pub.publish(state.topic(f"reponse/{pseudo}"), payload, qos=1)
                state.reponse_envoyee = True
                print("  📤 Réponse envoyée ! En attente de la correction...")
            else:
                print("  ⚠️  Réponds avec A, B, C ou D : ", end="", flush=True)

        elif state.state == "fin" and state.scores_recus:
            break

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n  Déconnexion propre...")

finally:
    # Nettoyage : publier offline proprement
    pub.publish(state.topic(f"presence/{pseudo}"), "offline", qos=1, retain=True)
    time.sleep(0.5)
    pub.loop_stop()
    pub.disconnect()
    sub.loop_stop()
    sub.disconnect()
