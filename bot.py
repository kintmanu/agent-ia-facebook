import os
import sys
import json
import time
import requests
import agent

# Variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61578925910517")

# Cache temporaire pour validation de publication
PENDING_DRAFT = {}

def send_tg_message(text, token=None, chat_id=None):
    t = token or TELEGRAM_BOT_TOKEN
    c = chat_id or TELEGRAM_CHAT_ID
    if not t or not c:
        return
    url = f"https://api.telegram.org/bot{t}/sendMessage"
    payload = {
        "chat_id": c,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"Erreur envoi message TG: {e}")

def send_tg_photo(caption, image_bytes, token=None, chat_id=None):
    t = token or TELEGRAM_BOT_TOKEN
    c = chat_id or TELEGRAM_CHAT_ID
    if not t or not c:
        return
    url = f"https://api.telegram.org/bot{t}/sendPhoto"
    data = {
        "chat_id": c,
        "caption": caption[:1000],
        "parse_mode": "Markdown"
    }
    files = {"photo": ("draft.jpg", image_bytes, "image/jpeg")}
    try:
        requests.post(url, data=data, files=files, timeout=35)
    except Exception as e:
        print(f"Erreur envoi photo TG: {e}")

def handle_telegram_message(text, token=None, chat_id=None):
    t = token or TELEGRAM_BOT_TOKEN
    c = chat_id or TELEGRAM_CHAT_ID
    text_clean = text.strip()
    config = agent.load_config()

    # 1. Commande /start ou Aide
    if text_clean.lower() in ["/start", "aide", "help", "menu"]:
        menu = f"""👋 **Bonjour Emmanuel ! Je suis ton Agent IA Facebook.**

Voici toutes les actions que tu peux faire avec moi :
💬 **Discussion libre :** Parle-moi de tes projets ou demande-moi des conseils.
🚀 **/publier :** Recherche une actualité tendance, crée l'image et publie direct sur Facebook !
📢 **/pub [ton offre] :** Crée une publicité sur-mesure (ex: `/pub -20% sur nos formations IA`).
💡 **/idees :** Je te propose 3 idées percutantes pour aujourd'hui.
📌 **/niche [nom] :** Change la thématique (ex: `/niche E-commerce & Vente en ligne`).
⏰ **/horaire [08h00 / 14h00] :** Change l'heure de programmation automatique.

📌 *Niche actuelle : {config.get('niche')}*
⏰ *Heure de publication : {config.get('schedule_time', '14h00')}*"""
        send_tg_message(menu, t, c)
        return

    # 2. Commande /publier (Publication d'actualité immédiate)
    if text_clean.lower() == "/publier":
        send_tg_message("🚀 **Reçu ! Je prépare le post...**\n1. Recherche de tendance\n2. Rédaction Gemini\n3. Création image HD (0 logo)\n4. Publication sur Facebook...", t, c)
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
                    send_tg_message(f"❌ Erreur Facebook : {detail}", t, c)
            else:
                send_tg_message("⚠️ Impossible de générer la photo pour ce post.", t, c)
        except Exception as e:
            send_tg_message(f"❌ Erreur : {e}", t, c)
        return

    # 3. Commande /pub (Créateur de Publicité Express sur-mesure)
    if text_clean.lower().startswith("/pub"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1:
            offer = parts[1].strip()
            send_tg_message(f"📢 **Création de ta publicité en cours...**\nOffre : *{offer}*\nJe rédige le texte vendeur et je génère la photo studio...", t, c)
            try:
                ad_data = agent.generate_ad_post(
                    product_name=offer,
                    offer_details=offer,
                    cta="Laissez un message ou écrivez-moi en privé",
                    audience="Grand public & Clients potentiels"
                )
                img = agent.download_image(ad_data["image_prompt"])
                if img:
                    PENDING_DRAFT["text"] = ad_data["post_text"]
                    PENDING_DRAFT["image"] = img
                    
                    caption = f"✨ **APERÇU DE LA PUBLICITÉ PRÊTE :**\n\n{ad_data['post_text']}\n\n👉 Envoie **/valider** pour publier cette pub immédiatement sur ta page Facebook !"
                    send_tg_photo(caption, img, t, c)
                else:
                    send_tg_message(f"📝 Voici le texte publicitaire rédigé :\n\n{ad_data['post_text']}", t, c)
            except Exception as e:
                send_tg_message(f"❌ Erreur création pub : {e}", t, c)
        else:
            send_tg_message("📌 Précise ton offre après `/pub`, par exemple :\n`/pub Formation exclusive en intelligence artificielle avec 30% de remise cette semaine`", t, c)
        return

    # 4. Commande /valider (pour valider le brouillon en cours)
    if text_clean.lower() in ["/valider", "valider", "publie ça", "publier ça"]:
        if "text" in PENDING_DRAFT and "image" in PENDING_DRAFT:
            send_tg_message("🚀 Publication sur Facebook en cours...", t, c)
            ok, detail = agent.publish_to_facebook(PENDING_DRAFT["text"], PENDING_DRAFT["image"])
            if ok:
                send_tg_message("✅ **SUCCÈS TOTAL ! Ta pub est maintenant en ligne sur Facebook !**\n👉 https://www.facebook.com/profile.php?id=61578925910517", t, c)
                PENDING_DRAFT.clear()
            else:
                send_tg_message(f"❌ Erreur Facebook : {detail}", t, c)
        else:
            send_tg_message("ℹ️ Aucun brouillon en attente. Tu peux en créer un avec `/pub [mon offre]` ou lancer un post avec `/publier` !", t, c)
        return

    # 5. Commande /niche
    if text_clean.lower().startswith("/niche"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1:
            new_niche = parts[1].strip()
            config["niche"] = new_niche
            config["keywords"] = new_niche
            agent.save_config(config)
            send_tg_message(f"✅ **Thématique mise à jour !**\nNiche active : **{new_niche}**.\nLe changement est aussi synchronisé sur ta Mini-App web !", t, c)
        else:
            send_tg_message("📌 Précise la niche, par exemple : `/niche Business & Entrepreneuriat`", t, c)
        return

    # 6. Commande /horaire
    if text_clean.lower().startswith("/horaire") or text_clean.lower().startswith("/heure"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1:
            new_hour = parts[1].strip()
            config["schedule_time"] = new_hour
            agent.save_config(config)
            send_tg_message(f"⏰ **Horaire programmé mis à jour !**\nHeure choisie : **{new_hour}**.\nSynchronisé avec la Mini-App !", t, c)
        else:
            send_tg_message("📌 Précise l'heure souhaitée, par exemple : `/horaire 18h00`", t, c)
        return

    # 7. Commande /idees
    if text_clean.lower() in ["/idees", "/idées", "idées", "idees"]:
        send_tg_message("🔍 Recherche d'idées percutantes adaptées à ton audience...", t, c)
        reply = agent.chat_with_agent("Donne-moi 3 idées de publications captivantes pour aujourd'hui (1 actualité, 1 conseil pratique, 1 idée d'offre/pub).")
        send_tg_message(reply, t, c)
        return

    # 8. Discussion libre avec Gemini (Community Manager)
    reply = agent.chat_with_agent(text_clean)
    send_tg_message(reply, t, c)

def start_polling_loop():
    token = TELEGRAM_BOT_TOKEN or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = TELEGRAM_CHAT_ID or os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        print("Telegram bot token non configuré.")
        return
        
    print("👂 Écouteur Telegram autonome actif...")
    offset = 0
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    while True:
        try:
            params = {"offset": offset, "timeout": 20}
            res = requests.get(url, params=params, timeout=30)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    cid = str(msg.get("chat", {}).get("id", ""))
                    text = msg.get("text", "")
                    
                    if cid == str(chat_id) and text:
                        print(f"📩 Reçu d'Emmanuel : {text}")
                        handle_telegram_message(text, token, chat_id)
            elif res.status_code == 409:
                time.sleep(8)
            else:
                time.sleep(3)
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    start_polling_loop()
