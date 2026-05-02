import paho.mqtt.client as paho
import json
import shared_state as state

def build_client(pseudo, code, on_state_change, on_question, on_correction, on_scores):

    client = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id=f"joueur-sub-{pseudo}-{code}",
        userdata={"pseudo": pseudo, "code": code},
        protocol=paho.MQTTv5
    )

    def on_connect(c, userdata, flags, rc, properties=None):
        print(f"[SUB joueur {pseudo}] Connecté : {rc}")
        # Souscrit à l'état de la partie
        c.subscribe(state.topic(code, "state"),      qos=1)
        c.subscribe(state.topic(code, "question"),   qos=1)
        c.subscribe(state.topic(code, "correction"), qos=1)
        c.subscribe(state.topic(code, "scores"),     qos=1)
        c.subscribe(state.topic_serveur(f"stats/{code}"), qos=1)
        c.subscribe(state.topic(code, "presence/animateur"), qos=1)

    def on_message(c, userdata, msg):
        topic   = msg.topic
        payload = msg.payload.decode()
        pseudo  = userdata["pseudo"]
        code    = userdata["code"]

        if not payload:
            return

        # Etat de la partie
        if topic == state.topic(code, "state"):
            state.joueur_state = payload
            on_state_change(payload)
            print(f"[SUB joueur {pseudo}] État → {payload}")

        # Présence de l'animateur 
        elif topic == state.topic(code, "presence/animateur"):
            if payload == "offline":
                on_state_change("animateur_offline")
                print(f"[SUB joueur {pseudo}] Animateur déconnecté")
            elif payload == "online":
                on_state_change("animateur_online")
                print(f"[SUB joueur {pseudo}] Animateur reconnecté")

        # Questions
        elif topic == state.topic(code, "question"):
            # Ignorer les retained si la partie n'est pas encore lancée
            if msg.retain and state.joueur_state != "question":
                return
            try:
                q = json.loads(payload)
                state.question_active = q
                state.reponse_envoyee = False
                on_question(q)
                print(f"[SUB joueur {pseudo}] Question reçue : {q['question']}")
            except Exception as e:
                print(f"[ERR] Question malformée : {e}")

        # Correction 
        elif topic == state.topic(code, "correction"):
            # Ignorer les retained
            if msg.retain:
                return
            try:
                data = json.loads(payload)
                state.reponses_tour_joueur = data.get("reponses", {}).get(pseudo)
                state.correction_active    = data
                on_correction(data)
                print(f"[SUB joueur {pseudo}] Correction reçue")
            except Exception as e:
                print(f"[ERR] Correction malformée : {e}")

        # Scores finaux 
        elif topic == state.topic(code, "scores"):
            if state.scores_recus:
                return
            state.scores_recus = True
            try:
                data = json.loads(payload)
                state.classement_final = data
                on_scores(data)
                print(f"[SUB joueur {pseudo}] Scores finaux reçus")
            except Exception as e:
                print(f"[ERR] Scores malformés : {e}")

        # Stats du serveur 
        elif topic == state.topic_serveur(f"stats/{code}"):
            if state.scores_recus:
                return
            state.scores_recus = True
            try:
                data = json.loads(payload)
                state.classement_final = data
                on_scores(data)
                print(f"[SUB joueur {pseudo}] Stats serveur reçues")
            except Exception as e:
                print(f"[ERR] Stats malformées : {e}")

    def on_disconnect(c, userdata, flags, rc, properties=None):
        print(f"[SUB joueur {pseudo}] Déconnecté : {rc}")

    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect
    return client