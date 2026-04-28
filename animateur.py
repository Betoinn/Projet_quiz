# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 14:25:25 2026

@author: Utilisateur
"""

import paho.mqtt.client as paho
import json
import time

BROKER = "broker.emqx.io"
PORT = 1883

pseudo = input("Entrez votre pseudo : ")
salon = input("Salon à rejoindre : ")

# Topics
TOPIC_MESSAGES = f"isen-2026-NB/chat/salon/{salon}/messages"
TOPIC_DERNIER  = f"isen-2026-NB/chat/salon/{salon}/dernier"
TOPIC_PRESENCE = f"isen-2026-NB/chat/salon/{salon}/presence/{pseudo}"
TOPIC_PRESENCE_ALL = f"isen-2026-NB/chat/salon/{salon}/presence/+"

# Souscrit aux 3 topics, voir les personnes qui rejoignent le salon
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[CHAT] Connecté au broker")
    client.subscribe(TOPIC_MESSAGES, qos=1)
    client.subscribe(TOPIC_DERNIER, qos=1)
    client.subscribe(TOPIC_PRESENCE_ALL, qos=1)
    client.publish(TOPIC_PRESENCE, "online", qos=1, retain=True)
    print(f"[CHAT] Vous avez rejoint le salon '{salon}' en tant que '{pseudo}'")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()

    # Affiche l'état de connexion d'une personne
    if "presence" in topic:
        pseudo_autre = topic.split("/")[-1] # Extrait le pseudo depuis le topic
        if pseudo_autre != pseudo:
            print(f"***** {pseudo_autre} est {payload} *****")

    # Affiche le dernier message
    elif topic == TOPIC_DERNIER:
        if msg.retain:
            data = json.loads(payload)
            print(f"[Dernier message] {data['pseudo']} : {data['texte']}")

    # Affiche messages
    elif topic == TOPIC_MESSAGES:
        data = json.loads(payload)
        if data["pseudo"] != pseudo:
            print(f"{data['pseudo']} : {data['texte']}")


client = paho.Client(client_id=f"chat-{pseudo}", protocol=paho.MQTTv5) # Créer l'user sur MQTT
client.on_connect = on_connect
client.on_message = on_message
client.will_set(TOPIC_PRESENCE, "offline", qos=1, retain=True) # LWT (enregistre le LWT auprès du Broker)
client.connect(BROKER, PORT, clean_start=False) # Garde les messages en attente si on se déco
client.loop_start()

time.sleep(1) # attente pour recevoir les messages retained


print("Ecrire un message :")
try:
    while True:
        texte = input(f"{pseudo} : ")    # Attente du message
        if texte.strip() == "": 
            continue                     # Ignore si on appuie juste sur entrée
        message = json.dumps({
            "pseudo": pseudo,
            "texte": texte,
            "timestamp": int(time.time())
        })
        client.publish(TOPIC_MESSAGES, message, qos=1) 
        client.publish(TOPIC_DERNIER, message, qos=1, retain=True) 

except KeyboardInterrupt: # Fermeture 
    client.publish(TOPIC_PRESENCE, "offline", qos=1, retain=True)
    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("***** Vous etes déconnecté *****")


    



