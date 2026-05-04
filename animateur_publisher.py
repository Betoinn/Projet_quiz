import paho.mqtt.client as paho
import json
import shared_state as state
 
def build_client(code):

    pub = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id=f"animateur-pub-{code}",  # ID unique par partie
        protocol=paho.MQTTv5
    )
    # LWT 
    pub.will_set(state.topic(code, "presence/animateur"), "offline", qos=1, retain=True)
    pub.on_connect    = lambda c, u, f, rc, p=None: on_connect(c, u, f, rc, code, p)
    pub.on_disconnect = on_disconnect
    return pub
 
def on_connect(client, userdata, flags, rc, code, properties=None):
    print(f"[PUB animateur {code}] Connecté : {rc}")
    # Annonce la présence de l'animateur
    client.publish(state.topic(code, "presence/animateur"), "online", qos=1, retain=True)
    # Publie l'état initial de la partie
    client.publish(state.topic(code, "state"), "attente", qos=1, retain=True)
 
def on_disconnect(client, userdata, flags, rc, properties=None):
    print(f"[PUB animateur] Déconnecté : {rc}")
    if str(rc) != "Normal disconnection":
        print(f"[PUB animateur] Tentative de reconnexion...")
        try:
            client.reconnect()
        except Exception as e:
            print(f"[PUB animateur] Erreur reconnexion : {e}")
 
# FONCTIONS DE PUBLICATION
 
def publier_demande_questions(client, code, nb_questions):
    payload = json.dumps({"nb_questions": nb_questions})
    client.publish(state.topic_serveur(f"demande/{code}"), payload, qos=1)
    print(f"[PUB animateur {code}] Demande de {nb_questions} questions")
 
def publier_question(client, code, question):
    client.publish(state.topic(code, "question"), json.dumps(question), qos=1, retain=True)
    print(f"[PUB animateur {code}] Question publiée : {question['question']}")
 
def publier_etat(client, code, etat):
    client.publish(state.topic(code, "state"), etat, qos=1, retain=True)
    print(f"[PUB animateur {code}] État → {etat}")

def publier_pause(client, code):
    client.publish(state.topic(code, "state"), "pause", qos=1, retain=True)
    print(f"[PUB animateur {code}] Etat → pause")
 
def publier_correction(client, code, bonne_reponse, texte_reponse, reponses):
    payload = json.dumps({
        "bonne_reponse": bonne_reponse,
        "texte_reponse": texte_reponse,
        "reponses":      reponses
    })
    client.publish(state.topic(code, "correction"), payload, qos=1, retain=True)
    print(f"[PUB animateur {code}] Correction publiée : {bonne_reponse}")
 
def publier_scores(client, code, classement):
    payload = json.dumps({"classement": classement})
    client.publish(state.topic(code, "scores"), payload, qos=1, retain=True)
    print(f"[PUB animateur {code}] Scores finaux publiés")
 
def publier_recap(client, code, reponses):
    client.publish(state.topic(code, "reponses_recap"), json.dumps(reponses), qos=1, retain=True)