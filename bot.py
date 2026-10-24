import os
import sys
import json
import time
import requests
import agent

# Récupération des clés
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61578925910517")

# Configuration des modules
agent.GEMINI_API_KEY = GEMINI_API_KEY
agent.FB_PAGE_ID = FB_PAGE_ID
agent.FB_PAGE_ACCESS_TOKEN = FB_PAGE_ACCESS_TOKEN
agent.TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN
agent.TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID

def send_tg_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Erreur envoi message TG: {e}")

def chat_with_gemini(user_message, history_context=""):
    config = agent.load_config()
    system_prompt = f"""Tu es l'assistant IA personnel et Community Manager officiel d'Emmanuel Kint.
Tu gères sa page Facebook professionnelle.
Niche active actuelle : {config.get('niche')}
Ton : {config.get('tone')}

RÔLE ET CAPACITÉS :
- Tu es courtois, dynamique, force de proposition et créatif.
- Tu réponds en français clair avec des émojis adaptés.
- Si Emmanuel te demande des idées de sujets, propose 3 idées percutantes et modernes.
- Si Emmanuel te demande de rédiger un post, fais-le avec une accroche, des puces, une question engageante et 4 hashtags.
- Si Emmanuel demande de changer de sujet ou de niche, confirme-lui avec enthousiasme.
- Sois concis et direct, adapté à un format de messagerie mobile."""

    full_prompt = f"{system_prompt}\n\nMessage d'Emmanuel : {user_message}"
    try:
        reply = agent.call_gemini(full_prompt)
        return reply
    except Exception as e:
        return f"Oups, j'ai rencontré un petit souci pour réfléchir : {e}"

def handle_incoming_message(text):
    text_clean = text.strip()
    config = agent.load_config()
    
    # Commande /start ou aide
    if text_clean.lower() in ["/start", "aide", "help", "menu"]:
        menu = """👋 **Bonjour Emmanuel ! Je suis ton Agent IA Facebook.**

Voici ce que tu peux faire avec moi :
💬 **Discute simplement :** Pose-moi n'importe quelle question ou demande-moi des idées de posts.
🚀 **/publier :** Lance immédiatement une publication avec photo HD sur ta page Facebook !
📌 **/niche [nom] :** Change la thématique de travail (ex: `/niche Crypto & Finance`).
💡 **/idees :** Je te propose 3 sujets tendances pour aujourd'hui."""
        send_tg_message(menu)
        return

    # Commande /publier
    if text_clean.lower() == "/publier":
        send_tg_message("🚀 **Reçu ! Je me mets au travail...**\nRecherche d'actualités, rédaction Gemini, création de l'image et publication sur Facebook en cours...")
        try:
            articles = agent.fetch_ai_news(config, force=True)
            content = agent.generate_post(articles, config)
            img = agent.download_image(content["image_prompt"])
            if img:
                ok, detail = agent.publish_to_facebook(content["post_text"], img)
                if ok:
                    agent.save_to_history(content["selected_link"])
                    agent.send_telegram_report(content["post_text"], img, config.get("niche"))
                else:
                    send_tg_message(f"❌ Erreur lors de la publication Facebook : {detail}")
            else:
                send_tg_message("⚠️ Impossible de générer la photo pour ce post.")
        except Exception as e:
            send_tg_message(f"❌ Erreur : {e}")
        return

    # Commande /niche
    if text_clean.lower().startswith("/niche"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1:
            new_niche = parts[1].strip()
            config["niche"] = new_niche
            config["keywords"] = new_niche
            agent.save_config(config)
            send_tg_message(f"✅ **Niche mise à jour !**\nJe me concentre désormais sur : **{new_niche}**.")
        else:
            send_tg_message("📌 Précise la niche, par exemple : `/niche E-commerce & Marketing`")
        return

    # Commande /idees
    if text_clean.lower() in ["/idees", "/idées", "idées", "idees"]:
        send_tg_message("🔍 Recherche d'idées percutantes du jour en cours...")
        reply = chat_with_gemini("Donne-moi 3 idées de posts très engageantes pour aujourd'hui adaptées à notre audience.")
        send_tg_message(reply)
        return

    # Discussion libre avec Gemini
    reply = chat_with_gemini(text_clean)
    send_tg_message(reply)

def start_polling_loop():
    if not TELEGRAM_BOT_TOKEN:
        print("Bot token manquant, écouteur Telegram inactif.")
        return
        
    print("👂 Écouteur Telegram démarré (24h/24) !")
    offset = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    while True:
        try:
            params = {"offset": offset, "timeout": 20}
            res = requests.get(url, params=params, timeout=30)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "")
                    
                    # On ne répond qu'à Emmanuel
                    if chat_id == str(TELEGRAM_CHAT_ID) and text:
                        print(f"📩 Message reçu d'Emmanuel : {text}")
                        handle_incoming_message(text)
            elif res.status_code == 409:
                time.sleep(5)
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    start_polling_loop()
