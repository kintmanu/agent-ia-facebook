import os
import sys
import json
import time
import requests
import agent

# Clés
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61578925910517")

# Cache pour validation de brouillon et mémoire conversationnelle
PENDING_DRAFT = {}
CHAT_HISTORY = []

def send_tg_message(text, token=None, chat_id=None):
    t = token or TELEGRAM_BOT_TOKEN
    c = chat_id or TELEGRAM_CHAT_ID
    if not t or not c:
        return
    url = f"https://api.telegram.org/bot{t}/sendMessage"
    payload = {"chat_id": c, "text": text, "parse_mode": "Markdown"}
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
    data = {"chat_id": c, "caption": caption[:1000], "parse_mode": "Markdown"}
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
    camp_status = agent.get_campaign_status(config)

    # 1. Aide et Menu
    if text_clean.lower() in ["/start", "aide", "help", "menu"]:
        slots = config.get("schedule_slots", {})
        active_slots = [f"{s.get('label')} ({s.get('time')})" for s in slots.values() if s.get("enabled")]
        slots_str = ", ".join(active_slots) if active_slots else "Aucun créneau actif"

        menu = f"""👋 **Bonjour Emmanuel ! Je suis ton Agent IA Facebook.**

Voici ce que tu peux faire directement depuis Telegram :
💬 **Discussion continue :** Pose-moi des questions, demande des ajustements sur un texte ou une pub.
🚀 **/publier :** Lance immédiatement une publication d'actualité avec photo studio sur Facebook.
📢 **/pub [ton offre] :** Rédige une pub sur-mesure et crée son visuel (ex: `/pub Coaching Business -25%`).
📊 **/campagne :** Affiche le statut complet de ta programmation (durée, créneaux, progression).
💡 **/idees :** Te propose 3 idées fraîches de posts.
📌 **/niche [nom] :** Modifie la thématique (ex: `/niche E-commerce & IA`).

📊 *Campagne : {camp_status['start_date']} au {camp_status['end_date']} ({camp_status['days_remaining']} j restants)*
⏰ *Créneaux choisis : {slots_str}*"""
        send_tg_message(menu, t, c)
        return

    # 2. Statut Campagne et Programmation
    if text_clean.lower() in ["/campagne", "/programme", "/horaire", "campagne", "programme"]:
        slots = config.get("schedule_slots", {})
        slots_desc = []
        for k, v in slots.items():
            status_icon = "🟢" if v.get("enabled") else "⚪"
            slots_desc.append(f"{status_icon} **{v.get('label')}** : {v.get('time')}")
        
        stat_msg = f"""📊 **PROGRAMMATION DE TA CAMPAGNE :**

📅 **Période :** Du {camp_status['start_date']} au {camp_status['end_date']}
⏳ **Jours restants :** {camp_status['days_remaining']} jours (sur {camp_status['total_days']} jours)
📦 **Publications prévues :** {camp_status['posts_published']} publiées sur {camp_status['total_expected_posts']} prévues
🎯 **Type de contenu :** {config.get('campaign_content_type')}

⏰ **Créneaux horaires quotidiens :**
{chr(10).join(slots_desc)}

*(Tu peux activer/désactiver Matin, Midi ou Soir et ajuster les heures sur ta Mini-App)*"""
        send_tg_message(stat_msg, t, c)
        return

    # 3. Publication Immédiate (/publier)
    if text_clean.lower() == "/publier":
        send_tg_message("🚀 **Reçu ! Préparation d'une publication immédiate...**\nRecherche d'actualité, rédaction Gemini, création image FLUX HD...", t, c)
        try:
            ok = agent.run_autonomous_slot(force=True)
            if not ok:
                send_tg_message("⚠️ La publication n'a pas pu être finalisée.", t, c)
        except Exception as e:
            send_tg_message(f"❌ Erreur : {e}", t, c)
        return

    # 4. Créateur de Publicité (/pub)
    if text_clean.lower().startswith("/pub"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1:
            offer = parts[1].strip()
            send_tg_message(f"📢 **Conception de ta publicité en cours...**\nOffre : *{offer}*\nRédaction AIDA + Génération de la photo studio commerciale...", t, c)
            try:
                ad_data = agent.generate_ad_post(
                    product_name=offer,
                    offer_details=offer,
                    cta="Écrivez-nous en message privé pour en profiter",
                    audience="Grand public & Clients",
                    config=config
                )
                img = agent.download_image(ad_data["image_prompt"])
                if img:
                    PENDING_DRAFT["text"] = ad_data["post_text"]
                    PENDING_DRAFT["image"] = img
                    
                    caption = f"✨ **APERÇU DE LA PUBLICITÉ PRÊTE :**\n\n{ad_data['post_text']}\n\n👉 Réponds **/valider** pour publier cette publicité maintenant sur Facebook !"
                    send_tg_photo(caption, img, t, c)
                else:
                    send_tg_message(f"📝 Voici le texte publicitaire rédigé :\n\n{ad_data['post_text']}", t, c)
            except Exception as e:
                send_tg_message(f"❌ Erreur création pub : {e}", t, c)
        else:
            send_tg_message("📌 Précise ton offre après `/pub`, par exemple :\n`/pub Formation pratique en IA avec 30% de remise cette semaine`", t, c)
        return

    # 5. Validation et envoi du brouillon
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
            send_tg_message("ℹ️ Aucun brouillon en attente. Tu peux en concevoir un avec `/pub [mon offre]` ou publier une actu avec `/publier` !", t, c)
        return

    # 6. Commande /niche
    if text_clean.lower().startswith("/niche"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1:
            new_niche = parts[1].strip()
            config["niche"] = new_niche
            config["keywords"] = new_niche
            agent.save_config(config)
            send_tg_message(f"✅ **Thématique mise à jour !**\nNiche active : **{new_niche}**.\nSynchronisé avec ta Mini-App !", t, c)
        else:
            send_tg_message("📌 Précise la niche, par exemple : `/niche Business & Entrepreneuriat`", t, c)
        return

    # 7. Commande /idees
    if text_clean.lower() in ["/idees", "/idées", "idées", "idees"]:
        send_tg_message("🔍 Recherche d'idées percutantes adaptées à ton audience...", t, c)
        reply = agent.chat_with_agent("Donne-moi 3 idées de publications captivantes pour aujourd'hui (1 actualité, 1 astuce pratique, 1 offre engageante).")
        send_tg_message(reply, t, c)
        return

    # 8. Discussion continue avec mémoire
    global CHAT_HISTORY
    CHAT_HISTORY.append({"role": "user", "content": text_clean})
    reply = agent.chat_with_agent(text_clean, history=CHAT_HISTORY)
    CHAT_HISTORY.append({"role": "assistant", "content": reply})
    if len(CHAT_HISTORY) > 14:
        CHAT_HISTORY = CHAT_HISTORY[-12:]
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
