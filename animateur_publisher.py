# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 08:41:28 2026

@author: Utilisateur
"""

import paho.mqtt.client as paho
import json

BROKER = "broker.emqx.io"
PORT = 1883
PREFIX = "isen-2026-NB/quiz"

TOPIC_ETAT       = f"isen-2026-NBEK/etat"
TOPIC_QUESTION   = f"isen-2026-NBEK/question"
TOPIC_CORRECTION = f"isen-2026-NBEK/correction"
TOPIC_SCORES     = f"isen-2026-NBEK/scores"
TOPIC_RECAP      = f"isen-2026-NBEK/reponses_recap"

def publier_question(client, question):
    client.publish(TOPIC_QUESTION, json.dumps(question), qos=1, retain=True)

def publier_etat(client, etat):
    client.publish(TOPIC_ETAT, etat, qos=1, retain=True)

def publier_correction(client, bonne_reponse, scores):
    payload = json.dumps({"bonne_reponse": bonne_reponse, "scores": scores})
    client.publish(TOPIC_CORRECTION, payload, qos=1, retain=True)

def publier_scores_finaux(client, resultats, classement):
    payload = json.dumps({"resultats": resultats, "classement": classement})
    client.publish(TOPIC_SCORES, payload, qos=1, retain=True)

def publier_recap(client, reponses):
    client.publish(TOPIC_RECAP, json.dumps(reponses), qos=1, retain=True)

