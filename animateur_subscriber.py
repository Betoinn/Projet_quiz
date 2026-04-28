
import paho.mqtt.client as paho
import json
import shared_state as state
 
def build_client():
    client = paho.Client(
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id="animateur-sub-EK",
        protocol=paho.MQTTv5
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    return client
 
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[SUB animateur] Connecté : {rc}")
    client.subscribe(state.topic("presence/+"), qos=1)
    client.subscribe(state.topic("reponse/+"),  qos=1)
 
def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode()
 
    if not payload:
        return
 
    if "presence" in topic:
        pseudo = topic.split("/")[-1]
        if pseudo == "animateur":
            return
        state.joueurs_presents[pseudo] = payload
        if pseudo not in state.scores:
            state.scores[pseudo] = {"correct": 0, "total": 0}
 
    elif "reponse" in topic:
        if msg.retain:
            return
        pseudo = topic.split("/")[-1]
        try:
            data = json.loads(payload)
            state.reponses_tour[pseudo] = data["reponse"]
            print(f"[SUB animateur] Réponse de {pseudo} : {data['reponse']}")
        except Exception as e:
            print(f"[ERR] Réponse malformée : {e}")
 
def on_disconnect(client, userdata, flags, rc, properties=None):
    print(f"[SUB animateur] Déconnecté : {rc}")