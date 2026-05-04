import paho.mqtt.client as paho
import json
import time
import shared_state as state

def build_client(pseudo, code):

    pub = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id=f"joueur-pub-{pseudo}-{code}",
        protocol=paho.MQTTv5
    )
    # LWT 
    pub.will_set(state.topic(code, f"presence/{pseudo}"),
                 "offline", qos=1, retain=True)
    pub.on_connect    = lambda c, u, f, rc, p=None: on_connect(c, u, f, rc, pseudo, code, p)
    pub.on_disconnect = on_disconnect
    return pub

def on_connect(client, userdata, flags, rc, pseudo, code, properties=None):

    print(f"[PUB joueur {pseudo}] Connecté : {rc}")
    # Annonce que le joueur est prêt
    client.publish(state.topic(code, f"presence/{pseudo}"),
                   "pret", qos=1, retain=True)

def on_disconnect(client, userdata, flags, rc, properties=None):
    print(f"[PUB joueur] Déconnecté : {rc}")
    if str(rc) != "Normal disconnection":
        try:
            client.reconnect()
        except Exception as e:
            print(f"[PUB joueur] Erreur reconnexion : {e}")

def publier_reponse(client, pseudo, code, reponse):

    payload = json.dumps({
        "pseudo":    pseudo,
        "reponse":   reponse,
        "timestamp": int(time.time())
    })
    client.publish(state.topic(code, f"reponse/{pseudo}"), payload, qos=1)
    print(f"[PUB joueur {pseudo}] Réponse envoyée : {reponse}")

def publier_deconnexion(client, pseudo, code):

    client.publish(state.topic(code, f"presence/{pseudo}"),
                   "offline", qos=1, retain=True)
    print(f"[PUB joueur {pseudo}] Déconnexion propre")