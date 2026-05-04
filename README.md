Sur python, il faut installer customtkinter ("pip install customtkinter")
Sur MQTTX, souscrire au topic : isen-2026-NBEK/#

Retained :

quiz/{code}/state → état de la partie
quiz/{code}/question → question en cours
quiz/{code}/correction → correction
quiz/{code}/scores → scores finaux
quiz/{code}/reponses_recap → récap des réponses
quiz/{code}/presence/animateur → présence animateur
quiz/{code}/presence/{pseudo} → présence de chaque joueur
serveur/stats/{code} → stats finales du serveur

LWT :

quiz/{code}/presence/animateur → si l'animateur crash → publie "offline"
quiz/{code}/presence/{pseudo} → si un joueur crash → publie "offline"
