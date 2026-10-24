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

# Mémoire de travail
PENDING_DRAFT = {}
CHAT_HISTORY = []
PROCESSED_UPDATE_IDS = set()

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

    # 1. Commande Menu / Aide
    if text_clean.lower() in ["/start", "aide", "help", "menu"]:
        slots = config.get("schedule_slots", {})
        active_slots = [f"{s.get('label')} ({s.get('time')})" for s in slots.values() if s.get("enabled")]
        slots_str = ", ".join(active_slots) if active_slots else "Aucun"

        menu = f"""🤖 **Agent IA Facebook d'Emmanuel**

🚀 **/publier :** Publier une actu maintenant sur Facebook
📢 **/pub [ton offre] :** Rédiger une pub et générer sa photo
📊 **/campagne :** Voir l'état de la programmation en cours
💡 **/idees :** 3 idées de sujets
📌 **/niche [nom] :** Changer de thématique

*Niche : {config.get('niche')}*
*Créneaux : {slots_str}*
*Ou écris-moi simplement ce que tu souhaites faire !*"""
        send_tg_message(menu, t, c)
        return

    # 2. Commande Statut de la Campagne
    if text_clean.lower() in ["/campagne", "/programme", "/horaire", "campagne", "programme"]:
        slots = config.get("schedule_slots", {})
        slots_desc = [f"- **{v.get('label')}** : {v.get('time')} ({'Actif' if v.get('enabled') else 'Inactif'})" for v in slots.values()]
        
        stat_msg = f"""📊 **PROGRAMMATION ACTUELLE :**

- **Durée :** Du {camp_status['start_date']} au {camp_status['end_date']} ({camp_status['days_remaining']} j restants)
- **Publications :** {camp_status['posts_published']} sur {camp_status['total_expected_posts']} prévues
- **Type :** {config.get('campaign_content_type')}

⏰ **Créneaux :**
{chr(10).join(slots_desc)}"""
        send_tg_message(stat_msg, t, c)
        return

    # 3. Commande Publication Immédiate (/publier)
    if text_clean.lower() == "/publier":
        send_tg_message("🚀 Je prépare et publie immédiatement le post d'actualité sur Facebook...", t, c)
        try:
            ok = agent.run_autonomous_slot(force=True)
            if not ok:
                send_tg_message("⚠️ Impossible de finaliser la publication pour le moment.", t, c)
        except Exception as e:
            send_tg_message(f"❌ Erreur : {e}", t, c)
        return

    # 4. Commande Publicité (/pub)
    if text_clean.lower().startswith("/pub"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1 and parts[1].strip():
            offer = parts[1].strip()
            send_tg_message(f"📢 Création de la publicité pour : *{offer}*...", t, c)
            try:
                ad_data = agent.generate_ad_post(
                    product_name=offer,
                    offer_details=offer,
                    cta="Écrivez-nous en privé pour en profiter",
                    audience="Grand public & Clients",
                    config=config
                )
                img = agent.download_image(ad_data["image_prompt"])
                if img:
                    PENDING_DRAFT["text"] = ad_data["post_text"]
                    PENDING_DRAFT["image"] = img
                    
                    caption = f"✨ **Aperçu de la publicité :**\n\n{ad_data['post_text']}\n\n👉 Envoie **/valider** pour publier cette pub sur Facebook !"
                    send_tg_photo(caption, img, t, c)
                else:
                    send_tg_message(f"📝 Voici le texte rédigé :\n\n{ad_data['post_text']}", t, c)
            except Exception as e:
                send_tg_message(f"❌ Erreur : {e}", t, c)
        else:
            send_tg_message("📢 Que souhaites-tu promouvoir ?\nIndique ton offre après `/pub`, par exemple :\n`/pub Formation IA avec 30% de remise cette semaine`", t, c)
        return

    # 5. Validation du brouillon (/valider)
    if text_clean.lower() in ["/valider", "valider", "publie ça", "publier ça"]:
        if "text" in PENDING_DRAFT and "image" in PENDING_DRAFT:
            send_tg_message("🚀 Publication sur Facebook en cours...", t, c)
            ok, detail = agent.publish_to_facebook(PENDING_DRAFT["text"], PENDING_DRAFT["image"])
            if ok:
                send_tg_message("✅ **Ta publicité est publiée sur ta Page Facebook !**\n👉 https://www.facebook.com/profile.php?id=61578925910517", t, c)
                PENDING_DRAFT.clear()
            else:
                send_tg_message(f"❌ Erreur Facebook : {detail}", t, c)
        else:
            send_tg_message("ℹ️ Aucun brouillon en attente. Tu peux en concevoir un avec `/pub [mon offre]` ou lancer une actu avec `/publier`.", t, c)
        return

    # 6. Commande /niche
    if text_clean.lower().startswith("/niche"):
        parts = text_clean.split(" ", 1)
        if len(parts) > 1 and parts[1].strip():
            new_niche = parts[1].strip()
            config["niche"] = new_niche
            config["keywords"] = new_niche
            agent.save_config(config)
            send_tg_message(f"✅ Thématique enregistrée : **{new_niche}** (synchronisée avec la Mini-App).", t, c)
        else:
            send_tg_message("📌 Précise la niche, par exemple : `/niche E-commerce & Vente en ligne`", t, c)
        return

    # 7. Commande /idees
    if text_clean.lower() in ["/idees", "/idées", "idées", "idees"]:
        reply = agent.chat_with_agent("Donne 3 idées courtes et directes de publications pour aujourd'hui.")
        send_tg_message(reply, t, c)
        return

    # 8. Discussion continue et naturelle (Au fur et à mesure, SANS salutations répétitives)
    global CHAT_HISTORY
    CHAT_HISTORY.append({"role": "user", "content": text_clean})
    
    # Appel à Gemini avec la mémoire récente
    reply = agent.chat_with_agent(text_clean, history=CHAT_HISTORY)
    
    # Nettoyage automatique des salutations intempestives
    clean_reply = reply.strip()
    for salutation in ["Bonjour Emmanuel !", "Bonjour Emmanuel,", "Bonjour Emmanuel", "Salut Emmanuel !", "Salut Emmanuel,", "Salut Emmanuel"]:
        if clean_reply.startswith(salutation):
            clean_reply = clean_reply[len(salutation):].strip()
            
    CHAT_HISTORY.append({"role": "assistant", "content": clean_reply})
    if len(CHAT_HISTORY) > 12:
        CHAT_HISTORY = CHAT_HISTORY[-10:]
        
    send_tg_message(clean_reply, t, c)

def poll_once(token, chat_id, offset):
    """Effectue un cycle d'écoute en agrégeant les messages consécutifs pour éviter le spam."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        params = {"offset": offset, "timeout": 15}
        res = requests.get(url, params=params, timeout=25)
        if res.status_code == 200:
            data = res.json()
            updates = data.get("result", [])
            if not updates:
                return offset
                
            # Nouveau offset pour acquitter immédiatement tous les messages
            new_offset = updates[-1]["update_id"] + 1
            
            # Récupérer les messages adressés par Emmanuel
            user_messages = []
            for upd in updates:
                upd_id = upd.get("update_id")
                if upd_id in PROCESSED_UPDATE_IDS:
                    continue
                PROCESSED_UPDATE_IDS.add(upd_id)
                
                msg = upd.get("message", {})
                cid = str(msg.get("chat", {}).get("id", ""))
                txt = msg.get("text", "").strip()
                if cid == str(chat_id) and txt:
                    user_messages.append(txt)
                    
            # Si Emmanuel a envoyé plusieurs petits messages en quelques secondes, on les combine
            if user_messages:
                combined_text = " ".join(user_messages)
                print(f"📩 Reçu d'Emmanuel : {combined_text}")
                handle_telegram_message(combined_text, token, chat_id)
                
            return new_offset
        elif res.status_code == 409:
            time.sleep(8)
            return offset
    except Exception as e:
        time.sleep(3)
        return offset
    return offset

def start_polling_loop():
    token = TELEGRAM_BOT_TOKEN or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = TELEGRAM_CHAT_ID or os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        print("Telegram bot token non configuré.")
        return
        
    print("👂 Écouteur Telegram démarré avec purge du backlog...")
    
    # Purge des anciens messages pour ne pas balancer des tonnes de réponses au démarrage
    offset = 0
    try:
        init_res = requests.get(f"https://api.telegram.org/bot{token}/getUpdates?offset=-1", timeout=10)
        if init_res.status_code == 200:
            res_list = init_res.json().get("result", [])
            if res_list:
                offset = res_list[-1]["update_id"] + 1
                print(f"🧹 Backlog Telegram purgé, écoute à partir de l'update {offset}")
    except Exception:
        pass
        
    while True:
        offset = poll_once(token, chat_id, offset)

if __name__ == "__main__":
    start_polling_loop()
