import streamlit as st
import json
import os
import requests
import threading
import io

# Import sécurisé de l'agent
import agent
import bot

st.set_page_config(
    page_title="Mon Agence IA - Privée & Sécurisée",
    page_icon="🤖",
    layout="wide"
)

# --- 1. GESTION ROBUSTE DES SECRETS ---
def get_secret(key, default=""):
    val = ""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            val = str(st.secrets[key])
    except Exception:
        pass
    if not val:
        val = os.environ.get(key, default)
    return str(val).strip().replace('"', '').replace("'", "")

APP_PASSWORD = get_secret("APP_PASSWORD", "kint2026")
GEMINI_KEY = get_secret("GEMINI_API_KEY")
FB_PAGE_ID = get_secret("FB_PAGE_ID", "61578925910517")
FB_TOKEN = get_secret("FB_PAGE_ACCESS_TOKEN")
TG_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

# Injection synchronisée des clés
agent.GEMINI_API_KEY = GEMINI_KEY
agent.FB_PAGE_ID = FB_PAGE_ID
agent.FB_PAGE_ACCESS_TOKEN = FB_TOKEN
agent.TELEGRAM_BOT_TOKEN = TG_TOKEN
agent.TELEGRAM_CHAT_ID = TG_CHAT_ID

bot.GEMINI_API_KEY = GEMINI_KEY
bot.FB_PAGE_ID = FB_PAGE_ID
bot.FB_PAGE_ACCESS_TOKEN = FB_TOKEN
bot.TELEGRAM_BOT_TOKEN = TG_TOKEN
bot.TELEGRAM_CHAT_ID = TG_CHAT_ID

# --- 2. GESTION DE L'ÉCOUTEUR TELEGRAM EN ARRIÈRE-PLAN (SINGLETON SÉCURISÉ) ---
_BOT_THREAD_STARTED = False
_BOT_LOCK = threading.Lock()

def ensure_telegram_listener():
    global _BOT_THREAD_STARTED
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    with _BOT_LOCK:
        if not _BOT_THREAD_STARTED:
            _BOT_THREAD_STARTED = True
            def runner():
                import time
                offset = 0
                url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
                while True:
                    try:
                        params = {"offset": offset, "timeout": 20}
                        res = requests.get(url, params=params, timeout=30)
                        if res.status_code == 200:
                            data = res.json()
                            for upd in data.get("result", []):
                                offset = upd["update_id"] + 1
                                msg = upd.get("message", {})
                                cid = str(msg.get("chat", {}).get("id", ""))
                                txt = msg.get("text", "")
                                if cid == str(TG_CHAT_ID) and txt:
                                    bot.handle_telegram_message(txt, TG_TOKEN, TG_CHAT_ID)
                        elif res.status_code == 409:
                            time.sleep(10)
                        else:
                            time.sleep(4)
                    except Exception:
                        time.sleep(5)
            t = threading.Thread(target=runner, daemon=True)
            t.start()

ensure_telegram_listener()

# --- 3. AUTHENTIFICATION PRIVÉE ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        st.markdown("<h2 style='text-align: center;'>🔒 Espace Privé - Emmanuel Kint</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Veuillez entrer votre mot de passe pour accéder au tableau de bord.</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            entered_pwd = st.text_input("Mot de passe secret :", type="password")
            if st.button("Se connecter 🔓", use_container_width=True, type="primary"):
                if entered_pwd == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect.")
        return False
    return True

if not check_password():
    st.stop()

# --- 4. CHARGEMENT CONFIGURATION ---
config = agent.load_config()

# --- 5. BARRE LATÉRALE ---
with st.sidebar:
    st.title("🤖 Mon Agence IA")
    st.success("🟢 Connecté : Emmanuel Kint")
    st.caption("Page Facebook : **Emmanuel kint**")
    
    st.divider()
    st.subheader("⚙️ État des Connexions")
    
    if GEMINI_KEY:
        st.write("🧠 Cerveau IA (Gemini) : 🟢 Prêt")
    else:
        st.write("🧠 Cerveau IA (Gemini) : 🔴 Manquant")
        
    if FB_TOKEN:
        st.write("📘 Facebook Graph API : 🟢 Connecté")
    else:
        st.write("📘 Facebook Graph API : 🔴 Manquant")
        
    if TG_TOKEN:
        st.write("📲 Telegram Bot : 🟢 Actif 24h/24")
    else:
        st.write("📲 Telegram Bot : ⚪ Non configuré")

    st.divider()
    st.subheader("🔔 Test Direct Telegram")
    if st.button("Envoyer un test sur mon Telegram", use_container_width=True):
        if not TG_TOKEN or not TG_CHAT_ID:
            st.warning("⚠️ Clés Telegram non configurées.")
        else:
            with st.spinner("Envoi du message en cours..."):
                ok = agent.test_telegram_connection()
                if ok:
                    st.success("🔔 Message envoyé avec succès sur ton Telegram !")
                else:
                    st.error("❌ Erreur lors de l'envoi sur Telegram.")

    st.divider()
    if st.button("Déconnexion 🔒", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 6. ENTÊTE DU DASHBOARD ---
st.title("🚀 Tableau de bord - Mon Agent IA Facebook")
st.markdown("Pilote ta page Facebook en direct, discute avec ton Community Manager IA, lance des publications d'actualités et crée des publicités percutantes.")

# Résumé visuel
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🎯 Niche Actuelle", config.get("niche", "Tech & IA")[:22] + "...")
with col2:
    st.metric("⏰ Heure de programmation", config.get("schedule_time", "14h00"))
with col3:
    st.metric("🔄 Fréquence", config.get("frequency", "1 fois par jour"))

st.divider()

# --- 7. ONGLETS PRINCIPAUX ---
tab_chat, tab_ads, tab_config, tab_live, tab_history = st.tabs([
    "💬 Studio Créatif & Chat IA",
    "📢 Créateur de Publicités & Offres",
    "🎯 Thématique & Horaires",
    "⚡ Radar & Publication Directe",
    "📜 Historique & Suivi"
])

# ==========================================
# ONGLET 1 : CHAT ET STUDIO CRÉATIF AVEC L'AGENT
# ==========================================
with tab_chat:
    st.subheader("💬 Parle en direct avec ton Community Manager IA")
    st.caption("Demande-lui des idées, rédige des posts sur-mesure, ou échange avec lui sur la stratégie de ta page Facebook.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "👋 Bonjour Emmanuel ! Que souhaites-tu publier aujourd'hui sur ta page Facebook ? Tu peux me demander des idées de sujets, un texte sur-mesure ou me donner des consignes précises !"}
        ]
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt_input := st.chat_input("Écris ton message à ton Community Manager IA..."):
        st.session_state.messages.append({"role": "user", "content": prompt_input})
        with st.chat_message("user"):
            st.markdown(prompt_input)
            
        with st.chat_message("assistant"):
            with st.spinner("🤖 Réflexion de ton Community Manager en cours..."):
                reply = agent.chat_with_agent(prompt_input, st.session_state.messages)
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

    st.divider()
    st.markdown("#### 🎨 Créer le Visuel et Publier un post issu de la discussion")
    st.caption("Tu aimes un texte généré dans la discussion ? Colle-le ici pour générer instantanément l'image HD et le publier sur Facebook ou l'envoyer sur Telegram.")
    
    custom_post_text = st.text_area("Texte du post à illustrer et publier :", placeholder="Colle ici le post rédigé par l'IA...", height=120)
    
    col_vis1, col_vis2 = st.columns(2)
    with col_vis1:
        if st.button("🖼️ 1. Générer le visuel studio HD (0 logo)", use_container_width=True):
            if not custom_post_text.strip():
                st.warning("⚠️ Renseigne d'abord le texte du post.")
            else:
                with st.spinner("Génération du prompt visuel et création de l'image FLUX..."):
                    img_prompt = agent.create_image_prompt_from_text(custom_post_text)
                    img_bytes = agent.download_image(img_prompt)
                    if img_bytes:
                        st.session_state.current_draft_text = custom_post_text
                        st.session_state.current_draft_image = img_bytes
                        st.success("✨ Visuel créé avec succès sans aucun filigrane !")
                    else:
                        st.error("Erreur de génération de l'image.")
                        
    if "current_draft_image" in st.session_state and st.session_state.current_draft_image:
        col_prev1, col_prev2 = st.columns([1, 1])
        with col_prev1:
            st.image(st.session_state.current_draft_image, caption="Aperçu HD 1080x1080", use_column_width=True)
        with col_prev2:
            st.markdown("**Texte du post prêt :**")
            st.info(st.session_state.get("current_draft_text", ""))
            
            btn_fb = st.button("🚀 Publier maintenant sur la page Facebook", type="primary", use_container_width=True)
            btn_tg = st.button("📲 M'envoyer l'aperçu sur Telegram", use_container_width=True)
            
            if btn_fb:
                with st.spinner("Publication sur Facebook en cours..."):
                    ok, detail = agent.publish_to_facebook(st.session_state.current_draft_text, st.session_state.current_draft_image)
                    if ok:
                        agent.send_telegram_report(st.session_state.current_draft_text, st.session_state.current_draft_image, config.get("niche"))
                        st.success("✅ **POST PUBLIÉ AVEC SUCCÈS SUR FACEBOOK !**")
                        st.markdown("[👉 Voir le post en direct sur ta page Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
                    else:
                        st.error(f"❌ Erreur Facebook : {detail}")
                        
            if btn_tg:
                with st.spinner("Envoi sur Telegram..."):
                    ok, detail = agent.send_telegram_preview(st.session_state.current_draft_text, st.session_state.current_draft_image)
                    if ok:
                        st.success("✅ Aperçu complet avec photo envoyé sur ton téléphone Telegram !")
                    else:
                        st.error(f"❌ Erreur Telegram : {detail}")

# ==========================================
# ONGLET 2 : CRÉATEUR DE PUBLICITÉS ET OFFRES
# ==========================================
with tab_ads:
    st.subheader("📢 Créateur de Publicités & Offres Express")
    st.caption("Génère des publications promotionnelles à fort impact (Framework marketing AIDA) avec visuels commerciaux professionnels.")
    
    col_ad1, col_ad2 = st.columns(2)
    with col_ad1:
        ad_product = st.text_input("Produit, Service ou Événement à promouvoir :", placeholder="ex: Formation Pratique en IA, Coaching Business, Boutique...")
        ad_offer = st.text_area("Offre & Avantages clés :", placeholder="ex: -30% pour les 10 premiers inscrits, accompagnement individuel inclus, accès à vie...", height=100)
    with col_ad2:
        ad_cta = st.text_input("Appel à l'action souhaité (CTA) :", value="Écris-moi en message privé ou commente 'INFO' pour démarrer !")
        ad_target = st.text_input("Public cible :", value="Entrepreneurs, passionnés de technologie et créateurs")
        
    if st.button("✨ Concevoir la Publicité & l'Image Studio", type="primary", use_container_width=True):
        if not ad_product.strip():
            st.warning("⚠️ Renseigne au moins le nom du produit ou service.")
        else:
            with st.spinner("🤖 Rédaction du copywriting persuasif et création de la photo publicitaire..."):
                try:
                    ad_result = agent.generate_ad_post(ad_product, ad_offer, ad_cta, ad_target, config)
                    img_data = agent.download_image(ad_result["image_prompt"])
                    if img_data:
                        st.session_state.ad_text = ad_result["post_text"]
                        st.session_state.ad_image = img_data
                        st.success(f"✨ Campagne conçue avec succès : **{ad_result.get('headline', 'Publicité')}**")
                    else:
                        st.session_state.ad_text = ad_result["post_text"]
                        st.warning("Texte rédigé mais l'image n'a pas pu être chargée.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    if "ad_image" in st.session_state and st.session_state.ad_image:
        st.divider()
        st.subheader("👁️ Aperçu de la Campagne Publicitaire")
        col_ad_res1, col_ad_res2 = st.columns([1, 1])
        with col_ad_res1:
            st.image(st.session_state.ad_image, caption="Photo publicitaire 1080x1080 sans filigrane", use_column_width=True)
        with col_ad_res2:
            st.markdown("**Texte publicitaire généré :**")
            st.info(st.session_state.get("ad_text", ""))
            
            pub_ad_btn = st.button("🚀 Publier cette pub sur Facebook", type="primary", key="pub_ad_fb", use_container_width=True)
            tg_ad_btn = st.button("📲 M'envoyer la pub sur Telegram", key="pub_ad_tg", use_container_width=True)
            
            if pub_ad_btn:
                with st.spinner("Publication de la publicité sur Facebook..."):
                    ok, detail = agent.publish_to_facebook(st.session_state.ad_text, st.session_state.ad_image)
                    if ok:
                        agent.send_telegram_report(st.session_state.ad_text, st.session_state.ad_image, "Publicité")
                        st.success("✅ **PUBLICITÉ PUBLIÉE AVEC SUCCÈS SUR FACEBOOK !**")
                        st.markdown("[👉 Voir la publicité sur ta page Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
                    else:
                        st.error(f"❌ Erreur Facebook : {detail}")
                        
            if tg_ad_btn:
                with st.spinner("Envoi sur Telegram..."):
                    ok, detail = agent.send_telegram_preview(st.session_state.ad_text, st.session_state.ad_image, title="📢 NOUVELLE PUBLICITÉ PRÊTE")
                    if ok:
                        st.success("✅ Publicité envoyée sur ton Telegram !")
                    else:
                        st.error(f"❌ Erreur Telegram : {detail}")

# ==========================================
# ONGLET 3 : THÉMATIQUE, HORAIRES ET PROGRAMMATION
# ==========================================
with tab_config:
    st.subheader("1. Thématique et Niche de travail")
    
    niches_predefinies = [
        "Intelligence Artificielle & Outils Tech",
        "E-commerce, Vente & Marketing Digital",
        "Business, Entrepreneuriat & Motivation",
        "Cryptomonnaies, Web3 & Finance Moderne",
        "Productivité & Automatisation No-Code"
    ]
    
    current_niche = config.get("niche", niches_predefinies[0])
    selected_niche = st.radio(
        "Choisis une thématique principale :",
        niches_predefinies + ["Thématique personnalisée..."],
        index=niches_predefinies.index(current_niche) if current_niche in niches_predefinies else len(niches_predefinies)
    )
    
    if selected_niche == "Thématique personnalisée...":
        custom_niche = st.text_input("Indique ta thématique sur-mesure :", value=current_niche if current_niche not in niches_predefinies else "")
        final_niche = custom_niche if custom_niche else "Intelligence Artificielle"
    else:
        final_niche = selected_niche
        
    st.divider()
    st.subheader("2. Ton et Style de Communication")
    tone_options = [
        "Professionnel, captivant et vulgarisé",
        "Inspirant, percutant et dynamique",
        "Chaleureux, accessible et amical",
        "Éducatif, précis et orienté tutoriels"
    ]
    saved_tone = config.get("tone", tone_options[0])
    current_tone = saved_tone if saved_tone in tone_options else tone_options[0]
    chosen_tone = st.selectbox("Style de rédaction :", tone_options, index=tone_options.index(current_tone))
    
    st.divider()
    st.subheader("3. Heure et Fréquence de Publication Automatique")
    st.write("Tu peux modifier l'heure de publication quand tu le souhaites selon ton humeur ou ta stratégie !")
    
    heures_possibles = ["07h00", "08h00", "09h00", "10h00", "12h00", "14h00", "16h00", "18h00", "20h00", "22h00"]
    saved_time = config.get("schedule_time", "14h00")
    current_time_index = heures_possibles.index(saved_time) if saved_time in heures_possibles else 5
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        chosen_time = st.selectbox("Heure de publication automatique :", heures_possibles, index=current_time_index)
    with col_t2:
        frequences = ["1 fois par jour", "2 fois par jour (Matin & Soir)", "Sur demande uniquement (Pas d'auto)"]
        saved_freq = config.get("frequency", frequences[0])
        chosen_freq = st.selectbox("Fréquence :", frequences, index=frequences.index(saved_freq) if saved_freq in frequences else 0)
        
    if st.button("💾 Enregistrer mes réglages", type="primary", use_container_width=True):
        config["niche"] = final_niche
        config["keywords"] = final_niche
        config["tone"] = chosen_tone
        config["schedule_time"] = chosen_time
        config["frequency"] = chosen_freq
        agent.save_config(config)
        st.success(f"✅ Enregistré ! Niche : **{final_niche}** | Heure : **{chosen_time}** ({chosen_freq}). Les changements sont aussi synchronisés avec ton bot Telegram !")
        st.rerun()

# ==========================================
# ONGLET 4 : RADAR ET PUBLICATION IMMÉDIATE
# ==========================================
with tab_live:
    st.subheader("⚡ Radar d'Actualités & Publication Instantanée")
    st.write("Recherche les actualités tendances du jour dans ta niche, rédige le post avec Gemini, génère l'image FLUX sans filigrane, et publie sur Facebook.")
    
    if st.button("🚀 Lancer une publication d'actualité maintenant", type="primary", use_container_width=True):
        status_box = st.status("Démarrage de la publication...", expanded=True)
        try:
            status_box.write("🔍 1. Recherche des actualités tendances récentes...")
            articles = agent.fetch_ai_news(config, force=True)
            if not articles:
                status_box.update(label="Aucun article trouvé", state="error")
                st.stop()
            status_box.write(f"💡 Article retenu : **{articles[0]['title']}**")
            
            status_box.write("🧠 2. Rédaction du post captivant avec Gemini...")
            content = agent.generate_post(articles, config)
            status_box.write("📝 Post rédigé avec succès !")
            
            status_box.write("🎨 3. Génération de l'image haute définition (FLUX, 0 filigrane)...")
            image_data = agent.download_image(content["image_prompt"])
            if not image_data:
                status_box.update(label="Erreur génération image", state="error")
                st.stop()
            status_box.write("✨ Image prête (1080x1080, propre) !")
            
            status_box.write("🚀 4. Envoi sur la Page Facebook...")
            fb_ok, fb_detail = agent.publish_to_facebook(content["post_text"], image_data)
            
            if fb_ok:
                status_box.write("📲 5. Envoi du rapport en direct sur ton Telegram...")
                agent.send_telegram_report(content["post_text"], image_data, config.get("niche"))
                agent.save_to_history(content["selected_link"])
                status_box.update(label="✅ Publication réussie avec succès !", state="complete")
                
                st.divider()
                st.subheader("Aperçu du post publié sur Facebook")
                col_res1, col_res2 = st.columns([1, 1])
                with col_res1:
                    st.image(image_data, caption="Image publiée (1080x1080)", use_column_width=True)
                with col_res2:
                    st.markdown(content["post_text"])
                    st.markdown("[👉 Ouvrir le post sur Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
            else:
                status_box.update(label="❌ Erreur de publication Facebook", state="error")
                st.error(f"Détail de l'erreur Facebook : {fb_detail}")
        except Exception as e:
            status_box.error(f"Erreur : {e}")

# ==========================================
# ONGLET 5 : HISTORIQUE
# ==========================================
with tab_history:
    st.subheader("📜 Historique des publications")
    st.caption("Mémoire anti-doublon des actualités déjà publiées sur la page Facebook :")
    if os.path.exists("history.txt"):
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        if lines:
            for l in reversed(lines[-15:]):
                st.markdown(f"- 🔗 `{l[:90]}...`")
        else:
            st.info("Aucun historique pour le moment.")
    else:
        st.info("Aucun historique pour le moment.")
