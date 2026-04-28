# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 08:41:28 2026

@author: Utilisateur
"""

import paho.mqtt.client as paho
import shared_state as state

def build_client():
    pub = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id="animateur-pub-EK",
        protocol=paho.MQTTv5
    )
    pub.will_set(state.topic("presence/animateur"), "offline", qos=1, retain=True)
    pub.on_connect = on_connect
    pub.on_disconnect = on_disconnect
    return pub

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[PUB animateur] Connecté : {rc}")
    client.publish(state.topic("presence/animateur"), "online", qos=1, retain=True)

def on_disconnect(client, userdata, flags, rc, properties=None):
    print(f"[PUB animateur] Déconnecté : {rc}")