import paho.mqtt.client as paho
import json
import shared_state as state
 
def build_client(code, on_questions_recues, on_joueur_update, on_reponse_recue):
    """
    Crée et retourne le client MQTT subscriber de l'animateur.
    Paramètres callbacks :
    - on_questions_recues : appelé quand le serveur répond avec les questions
    - on_joueur_update    : appelé quand un joueur se connecte/déconnecte
    - on_reponse_recue    : appelé quand un joueur envoie une réponse
    """
    client = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id=f"animateur-sub-{code}",  # ID unique par partie
        protocol=paho.MQTTv5
    )
 
    def on_connect(c, userdata, flags, rc, properties=None):
        print(f"[SUB animateur {code}] Connecté : {rc}")
        # Souscrit aux questions du serveur pour cette partie
        c.subscribe(state.topic_serveur(f"questions/{code}"), qos=1)
        # Souscrit aux stats du serveur pour cette partie
        c.subscribe(state.topic_serveur(f"stats/{code}"), qos=1)
        # Souscrit aux présences des joueurs
        c.subscribe(state.topic(code, "presence/+"), qos=1)
        # Souscrit aux réponses des joueurs
        c.subscribe(state.topic(code, "reponse/+"), qos=1)
 
    def on_message(c, userdata, msg):
        topic   = msg.topic
        payload = msg.payload.decode()
 
        if not payload:
            return
 
        # ── Questions reçues du serveur ───────────────────────
        if f"serveur/questions/{code}" in topic:
            try:
                data = json.loads(payload)
                if data.get("erreur"):
                    # Transmet le message d'erreur à l'interface
                    on_questions_recues(None, data["message"])
                else:
                    # Stocke les questions dans le state de la partie
                    state.parties[code]["questions"] = data["questions"]
                    on_questions_recues(data["questions"], None)
                    print(f"[SUB animateur {code}] {len(data['questions'])} questions reçues")
            except Exception as e:
                print(f"[ERR] Questions malformées : {e}")
 
        # ── Stats reçues du serveur ───────────────────────────
        elif f"serveur/stats/{code}" in topic:
            try:
                data = json.loads(payload)
                state.parties[code]["stats"] = data
                print(f"[SUB animateur {code}] Stats reçues")
            except Exception as e:
                print(f"[ERR] Stats malformées : {e}")
 
        # ── Présence d'un joueur ──────────────────────────────
        elif f"quiz/{code}/presence" in topic:
            pseudo = topic.split("/")[-1]
            if pseudo == "animateur":
                return
            # Met à jour le statut du joueur dans le state de la partie
            state.parties[code]["joueurs_presents"][pseudo] = payload
            # Initialise le score du joueur s'il n'existe pas encore
            if pseudo not in state.parties[code]["scores"]:
                state.parties[code]["scores"][pseudo] = {"correct": 0, "total": 0}
            on_joueur_update(code, pseudo, payload)
            print(f"[SUB animateur {code}] {pseudo} → {payload}")
 
        # ── Réponse d'un joueur ───────────────────────────────
        elif f"quiz/{code}/reponse" in topic:
            # Ignorer les retained (réponses d'une ancienne partie)
            if msg.retain:
                return
            pseudo = topic.split("/")[-1]
            try:
                data = json.loads(payload)
                state.parties[code]["reponses_tour"][pseudo] = data["reponse"]
                on_reponse_recue(code, pseudo, data["reponse"])
                print(f"[SUB animateur {code}] Réponse de {pseudo} : {data['reponse']}")
            except Exception as e:
                print(f"[ERR] Réponse malformée : {e}")
 
    def on_disconnect(c, userdata, flags, rc, properties=None):
        print(f"[SUB animateur {code}] Déconnecté : {rc}")
 
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect
    return client