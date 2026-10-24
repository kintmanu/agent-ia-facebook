import streamlit as st
import json
import os
import datetime
import requests
import threading
import io

import agent
import bot

st.set_page_config(
    page_title="Mon Agence IA - Privée & Sécurisée",
    page_icon="🤖",
    layout="wide"
)

# --- 1. GESTION DES SECRETS ---
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

# --- 2. ÉCOUTEUR TELEGRAM SINGLETON SÉCURISÉ ---
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

# --- 3. AUTHENTIFICATION ---
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

# --- 4. CHARGEMENT CONFIG & CAMPAGNE ---
config = agent.load_config()
camp_status = agent.get_campaign_status(config)

# --- 5. BARRE LATÉRALE ---
with st.sidebar:
    st.title("🤖 Mon Agence IA")
    st.success("🟢 Connecté : Emmanuel Kint")
    st.caption("Page Facebook : **Emmanuel kint**")
    
    st.divider()
    st.subheader("📊 État de la Campagne")
    if camp_status["is_active"]:
        st.success(f"🟢 Active : {camp_status['days_remaining']} j restants")
        st.progress(camp_status["progress_percent"])
        st.caption(f"📅 Du {camp_status['start_date']} au {camp_status['end_date']}")
        st.caption(f"📦 Publications : **{camp_status['posts_published']} / {camp_status['total_expected_posts']}**")
    else:
        st.warning("⏸️ Campagne en pause ou terminée")

    st.divider()
    st.subheader("🔔 Test Direct Telegram")
    if st.button("Envoyer un test sur mon Telegram", use_container_width=True):
        if not TG_TOKEN or not TG_CHAT_ID:
            st.warning("⚠️ Clés Telegram non configurées.")
        else:
            with st.spinner("Envoi du message..."):
                ok = agent.test_telegram_connection()
                if ok:
                    st.success("🔔 Message envoyé avec succès !")
                else:
                    st.error("❌ Erreur lors de l'envoi sur Telegram.")

    st.divider()
    if st.button("Déconnexion 🔒", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 6. ENTÊTE ---
st.title("🚀 Tableau de bord - Mon Agent IA Facebook")

# Métriques rapides
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("🎯 Niche Active", config.get("niche", "Tech & IA")[:18] + "...")
with m2:
    st.metric("⏰ Créneaux Actifs", f"{camp_status['active_slots_count']} / 3 par jour")
with m3:
    st.metric("📅 Durée Campagne", f"{camp_status['total_days']} jours")
with m4:
    st.metric("📦 Posts Prévus", f"{camp_status['total_expected_posts']} publications")

st.divider()

# --- 7. ONGLETS DE TRAVAIL ---
tab_chat, tab_schedule, tab_ads, tab_live, tab_history = st.tabs([
    "💬 Studio Créatif & Chat IA",
    "🎯 Programmation des Créneaux & Campagne",
    "📢 Créateur de Publicités Express",
    "⚡ Radar & Publication Directe",
    "📜 Historique & Suivi"
])

# ==========================================
# ONGLET 1 : CHAT EN DIRECT & STUDIO CRÉATIF
# ==========================================
with tab_chat:
    st.subheader("💬 Échange continu avec ton Community Manager IA")
    st.caption("Discute naturellement avec ton IA : demande des idées, peaufine des textes, ajuste des phrases sans que l'agent n'oublie le contexte !")

    # Boutons d'inspiration rapide en haut
    col_chip1, col_chip2, col_chip3, col_chip4 = st.columns(4)
    with col_chip1:
        if st.button("💡 3 idées de posts pour aujourd'hui", use_container_width=True):
            st.session_state.quick_prompt = "Donne-moi 3 idées de publications captivantes pour aujourd'hui adaptées à notre audience."
    with col_chip2:
        if st.button("📢 Proposer une offre publicitaire", use_container_width=True):
            st.session_state.quick_prompt = "Propose-moi un concept de publicité accrocheur pour promouvoir mes services ou formations."
    with col_chip3:
        if st.button("🚀 Rédiger un post inspirant sur l'IA", use_container_width=True):
            st.session_state.quick_prompt = "Rédige un post Facebook inspirant et vulgarisé sur l'impact de l'IA aujourd'hui, avec une question pour engager."
    with col_chip4:
        if st.button("🧹 Nouvelle discussion", use_container_width=True):
            st.session_state.messages = []
            st.session_state.draft_image = None
            st.session_state.draft_text = ""
            st.rerun()

    # Initialisation de l'historique
    if "messages" not in st.session_state or not st.session_state.messages:
        st.session_state.messages = [
            {"role": "assistant", "content": "👋 Bonjour Emmanuel ! Je suis prêt pour ta page Facebook. De quoi souhaites-tu parler ou quel post veux-tu qu'on prépare aujourd'hui ?"}
        ]

    # Affichage du flux de discussion
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Si le message de l'assistant contient un post rédigé, afficher l'action directe
            if msg["role"] == "assistant" and len(msg["content"]) > 80 and ("#" in msg["content"] or "👉" in msg["content"] or "🚀" in msg["content"]):
                with st.expander("🖼️ Transformer cette réponse en Publication Facebook (avec Image HD)", expanded=False):
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"🎨 Générer le visuel pour ce texte", key=f"btn_gen_{idx}", use_container_width=True):
                            with st.spinner("Génération de l'image 1080x1080 FLUX sans filigrane..."):
                                img_prompt = agent.create_image_prompt_from_text(msg["content"])
                                img_bytes = agent.download_image(img_prompt)
                                if img_bytes:
                                    st.session_state.draft_image = img_bytes
                                    st.session_state.draft_text = msg["content"]
                                    st.success("✨ Visuel prêt !")
                                else:
                                    st.error("Erreur téléchargement image.")

    # Affichage du brouillon généré s'il y en a un actif
    if "draft_image" in st.session_state and st.session_state.draft_image:
        st.divider()
        st.markdown("### 👁️ Publication prête à être lancée")
        col_prev1, col_prev2 = st.columns([1, 1])
        with col_prev1:
            st.image(st.session_state.draft_image, caption="Image 1080x1080 (0 logo)", use_column_width=True)
        with col_prev2:
            st.markdown("**Texte sélectionné :**")
            st.info(st.session_state.get("draft_text", ""))
            
            post_fb_btn = st.button("🚀 Publier maintenant sur ma Page Facebook", type="primary", key="send_fb_chat", use_container_width=True)
            post_tg_btn = st.button("📲 M'envoyer l'aperçu sur Telegram", key="send_tg_chat", use_container_width=True)
            
            if post_fb_btn:
                with st.spinner("Publication sur Facebook..."):
                    ok, detail = agent.publish_to_facebook(st.session_state.draft_text, st.session_state.draft_image)
                    if ok:
                        agent.send_telegram_report(st.session_state.draft_text, st.session_state.draft_image, config.get("niche"))
                        st.success("✅ **POST PUBLIÉ SUR TA PAGE FACEBOOK !**")
                        st.markdown("[👉 Ouvrir sur Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
                    else:
                        st.error(f"❌ Erreur : {detail}")
                        
            if post_tg_btn:
                with st.spinner("Envoi sur Telegram..."):
                    ok, detail = agent.send_telegram_preview(st.session_state.draft_text, st.session_state.draft_image)
                    if ok:
                        st.success("✅ Envoyé sur ton Telegram !")
                    else:
                        st.error(f"❌ Erreur : {detail}")

    # Gestion de la saisie utilisateur (Input en bas)
    input_text = ""
    if "quick_prompt" in st.session_state and st.session_state.quick_prompt:
        input_text = st.session_state.quick_prompt
        del st.session_state.quick_prompt
        
    user_prompt = st.chat_input("Écris ton message à ton Community Manager IA...") or input_text
    
    if user_prompt:
        # 1. Ajout du message utilisateur
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        # 2. Réflexion et réponse avec mémoire
        with st.chat_message("assistant"):
            with st.spinner("🤖 Ton Community Manager réfléchit..."):
                reply = agent.chat_with_agent(user_prompt, history=st.session_state.messages)
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.rerun()

# =======================================================
# ONGLET 2 : PROGRAMMATION DES CRÉNEAUX ET CAMPAGNE
# =======================================================
with tab_schedule:
    st.subheader("🎯 Programmation des Créneaux Quotidiens & Durée de Campagne")
    st.markdown("Configure précisément les heures de publication (Matin, Midi, Soir) et la durée de la campagne (7 jours, 1 mois ou personnalisé).")

    slots = config.get("schedule_slots", {})
    morning_slot = slots.get("morning", {"enabled": True, "time": "08h00"})
    midday_slot = slots.get("midday", {"enabled": False, "time": "13h00"})
    evening_slot = slots.get("evening", {"enabled": True, "time": "19h00"})

    # --- 1. SÉLECTION DES 3 CRÉNEAUX HORAIRES ---
    st.markdown("#### 1. Choix des Créneaux Quotidiens (Matin / Midi / Soir)")
    st.caption("Active 1, 2 ou 3 créneaux par jour et règle l'heure exacte souhaitée pour chacun :")

    heures_matin = ["06h00", "07h00", "08h00", "09h00", "10h00", "11h00"]
    heures_midi = ["12h00", "12h30", "13h00", "13h30", "14h00", "15h00"]
    heures_soir = ["17h00", "18h00", "19h00", "20h00", "21h00", "22h00"]

    col_slot1, col_slot2, col_slot3 = st.columns(3)
    
    with col_slot1:
        st.markdown("##### 🌅 Créneau MATIN")
        m_enabled = st.checkbox("Activer le Matin", value=morning_slot.get("enabled", True), key="chk_m")
        m_time = st.selectbox(
            "Heure du matin :", 
            heures_matin, 
            index=heures_matin.index(morning_slot.get("time", "08h00")) if morning_slot.get("time") in heures_matin else 2,
            disabled=not m_enabled,
            key="sel_m"
        )
        
    with col_slot2:
        st.markdown("##### ☀️ Créneau MIDI")
        d_enabled = st.checkbox("Activer le Midi", value=midday_slot.get("enabled", False), key="chk_d")
        d_time = st.selectbox(
            "Heure du midi :", 
            heures_midi, 
            index=heures_midi.index(midday_slot.get("time", "13h00")) if midday_slot.get("time") in heures_midi else 2,
            disabled=not d_enabled,
            key="sel_d"
        )

    with col_slot3:
        st.markdown("##### 🌙 Créneau SOIR")
        e_enabled = st.checkbox("Activer le Soir", value=evening_slot.get("enabled", True), key="chk_e")
        e_time = st.selectbox(
            "Heure du soir :", 
            heures_soir, 
            index=heures_soir.index(evening_slot.get("time", "19h00")) if evening_slot.get("time") in heures_soir else 2,
            disabled=not e_enabled,
            key="sel_e"
        )

    nb_creneaux_actifs = sum([1 for x in [m_enabled, d_enabled, e_enabled] if x])
    if nb_creneaux_actifs == 0:
        st.warning("⚠️ Aucun créneau n'est activé. L'agent sera en pause automatique.")
    else:
        st.success(f"✅ Configuration active : **{nb_creneaux_actifs} créneau(x) par jour** sélectionnés.")

    st.divider()

    # --- 2. DURÉE DE LA CAMPAGNE ---
    st.markdown("#### 2. Durée de la Campagne de Publication")
    st.caption("Combien de temps l'agent doit-il publier automatiquement ?")

    options_duree = ["7 jours (1 semaine)", "14 jours (2 semaines)", "30 jours (1 mois)", "Nombre de jours personnalisé"]
    saved_days = config.get("campaign_duration_days", 7)
    
    default_duree_idx = 0
    if saved_days == 14:
        default_duree_idx = 1
    elif saved_days == 30:
        default_duree_idx = 2
    elif saved_days not in [7, 14, 30]:
        default_duree_idx = 3

    choix_duree = st.radio("Sélectionne la durée souhaitée :", options_duree, index=default_duree_idx)

    if choix_duree == "7 jours (1 semaine)":
        final_days = 7
    elif choix_duree == "14 jours (2 semaines)":
        final_days = 14
    elif choix_duree == "30 jours (1 mois)":
        final_days = 30
    else:
        final_days = st.number_input("Indique le nombre exact de jours :", min_value=1, max_value=180, value=saved_days)

    # Calculs automatiques
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=final_days)
    total_posts = final_days * nb_creneaux_actifs

    col_calc1, col_calc2, col_calc3 = st.columns(3)
    with col_calc1:
        st.info(f"📅 **Date de début :** Aujourd'hui ({start_date.strftime('%d/%m/%Y')})")
    with col_calc2:
        st.info(f"🏁 **Date de fin :** {end_date.strftime('%d/%m/%Y')}")
    with col_calc3:
        st.info(f"📦 **Volume total prévu :** **{total_posts} publications** Facebook")

    st.divider()

    # --- 3. TYPE DE CONTENU PROGRAMMÉ ---
    st.markdown("#### 3. Stratégie de Contenu pour les Publications Automatiques")
    types_contenu = [
        "Mixte (Actualités le matin & Publicités/Offres le soir)",
        "Publicités & Vente uniquement (Campagne 100% commerciale)",
        "Actualités & Valeur uniquement (Croissance d'audience & Notoriété)"
    ]
    saved_content_type = config.get("campaign_content_type", types_contenu[0])
    selected_content_type = st.selectbox(
        "Comment répartir les publications ?", 
        types_contenu, 
        index=types_contenu.index(saved_content_type) if saved_content_type in types_contenu else 0
    )

    ad_topic_val = config.get("campaign_ad_topic", "Solutions, formations et opportunités professionnelles")
    if "Publicités" in selected_content_type or "Mixte" in selected_content_type:
        st.markdown("##### 📢 Offre ou Produit mis en avant dans les pubs programmées :")
        ad_topic_val = st.text_input(
            "Précise ton offre de référence pour que l'agent varie les angles publicitaires :", 
            value=ad_topic_val,
            placeholder="ex: Formation en Intelligence Artificielle et Coaching Business"
        )

    st.divider()

    # --- 4. THÉMATIQUE & STYLE ---
    st.markdown("#### 4. Thématique et Ton de Communication")
    col_th1, col_th2 = st.columns(2)
    with col_th1:
        niche_input = st.text_input("Niche / Thématique générale :", value=config.get("niche", "Intelligence Artificielle & Outils Tech"))
    with col_th2:
        tone_input = st.selectbox(
            "Ton général :",
            [
                "Professionnel, captivant et vulgarisé",
                "Persuasif, chaleureux et vendeur",
                "Inspirant, percutant et dynamique",
                "Accessible, pédagogique et amical"
            ],
            index=0
        )

    # --- 5. ENREGISTREMENT & VALIDATION ---
    st.divider()
    camp_active_toggle = st.toggle("🚀 Activer la campagne automatique maintenant", value=config.get("active_campaign", True))

    if st.button("💾 Enregistrer et Lancer cette Programmation", type="primary", use_container_width=True):
        config["schedule_slots"] = {
            "morning": {"enabled": m_enabled, "time": m_time, "label": "Matin"},
            "midday": {"enabled": d_enabled, "time": d_time, "label": "Midi"},
            "evening": {"enabled": e_enabled, "time": e_time, "label": "Soir"}
        }
        config["campaign_duration_days"] = final_days
        config["campaign_start_date"] = start_date.isoformat()
        config["campaign_end_date"] = end_date.isoformat()
        config["campaign_content_type"] = selected_content_type
        config["campaign_ad_topic"] = ad_topic_val
        config["niche"] = niche_input
        config["keywords"] = niche_input
        config["tone"] = tone_input
        config["active_campaign"] = camp_active_toggle
        
        agent.save_config(config)
        st.success(f"🎉 **PROGRAMMATION ENREGISTRÉE AVEC SUCCÈS !**\n\n- Période : du **{start_date.strftime('%d/%m/%Y')}** au **{end_date.strftime('%d/%m/%Y')}** ({final_days} jours)\n- Créneaux : **{nb_creneaux_actifs} publication(s) par jour**\n- Total : **{total_posts} publications programmées**.")
        st.rerun()

# ==========================================
# ONGLET 3 : CRÉATEUR DE PUBLICITÉS EXPRESS
# ==========================================
with tab_ads:
    st.subheader("📢 Créateur de Publicités & Promotions Express")
    st.caption("Conçois une publication publicitaire avec accroche vendeuse (Framework AIDA) et photo de studio commerciale 1080x1080.")

    col_ad1, col_ad2 = st.columns(2)
    with col_ad1:
        ad_prod = st.text_input("Produit ou Service :", placeholder="ex: Coaching IA, Formation E-commerce, Prestation Web...")
        ad_det = st.text_area("Offre & Avantages :", placeholder="ex: -30% ce mois-ci, places limitées à 10 personnes, accompagnement personnalisé...", height=110)
    with col_ad2:
        ad_cta_field = st.text_input("Appel à l'action (CTA) :", value="Écrivez-moi en message privé pour réserver votre place !")
        ad_aud_field = st.text_input("Public cible :", value="Entrepreneurs, créateurs et professionnels")

    if st.button("✨ Rédiger la Publicité & Générer la Photo Studio", type="primary", use_container_width=True):
        if not ad_prod.strip():
            st.warning("⚠️ Renseigne au moins le nom du produit ou service.")
        else:
            with st.spinner("🤖 Rédaction du copywriting AIDA et création de la photo studio..."):
                try:
                    res_ad = agent.generate_ad_post(ad_prod, ad_det, ad_cta_field, ad_aud_field, config)
                    img_bytes = agent.download_image(res_ad["image_prompt"])
                    if img_bytes:
                        st.session_state.ad_text = res_ad["post_text"]
                        st.session_state.ad_image = img_bytes
                        st.success(f"✨ Publicité prête : **{res_ad.get('headline', 'Campagne')}**")
                    else:
                        st.warning("Texte créé mais l'image n'a pas pu être chargée.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    if "ad_image" in st.session_state and st.session_state.ad_image:
        st.divider()
        col_ad_res1, col_ad_res2 = st.columns([1, 1])
        with col_ad_res1:
            st.image(st.session_state.ad_image, caption="Photo publicitaire (0 logo, 1080x1080)", use_column_width=True)
        with col_ad_res2:
            st.markdown("**Texte de la publicité :**")
            st.info(st.session_state.get("ad_text", ""))
            
            btn_fb_ad = st.button("🚀 Publier maintenant sur Facebook", type="primary", key="btn_fb_ad_act", use_container_width=True)
            btn_tg_ad = st.button("📲 M'envoyer sur Telegram", key="btn_tg_ad_act", use_container_width=True)
            
            if btn_fb_ad:
                with st.spinner("Publication sur Facebook..."):
                    ok, detail = agent.publish_to_facebook(st.session_state.ad_text, st.session_state.ad_image)
                    if ok:
                        agent.send_telegram_report(st.session_state.ad_text, st.session_state.ad_image, "Publicité")
                        st.success("✅ **PUBLICITÉ PUBLIÉE AVEC SUCCÈS SUR FACEBOOK !**")
                        st.markdown("[👉 Voir la pub sur Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
                    else:
                        st.error(f"❌ Erreur : {detail}")
                        
            if btn_tg_ad:
                with st.spinner("Envoi sur Telegram..."):
                    ok, detail = agent.send_telegram_preview(st.session_state.ad_text, st.session_state.ad_image, title="📢 NOUVELLE PUBLICITÉ")
                    if ok:
                        st.success("✅ Publicité envoyée sur ton Telegram !")
                    else:
                        st.error(f"❌ Erreur : {detail}")

# ==========================================
# ONGLET 4 : RADAR ET PUBLICATION DIRECTE
# ==========================================
with tab_live:
    st.subheader("⚡ Radar d'Actualités & Déclencheur Immédiat")
    st.write("Envie de publier un post d'actualité tout de suite sans attendre l'heure programmée ? Ce bouton lance l'agent en direct.")

    if st.button("🚀 Lancer une publication immédiate", type="primary", use_container_width=True):
        status_box = st.status("Démarrage du processus...", expanded=True)
        try:
            status_box.write("🔍 1. Consultation du radar d'actualités...")
            articles = agent.fetch_ai_news(config, force=True)
            if not articles:
                status_box.update(label="Aucun article trouvé", state="error")
                st.stop()
            status_box.write(f"💡 Article sélectionné : **{articles[0]['title']}**")
            
            status_box.write("🧠 2. Rédaction du post avec Gemini...")
            content = agent.generate_post(articles, config)
            status_box.write("📝 Post rédigé avec succès !")
            
            status_box.write("🎨 3. Création de l'image haute définition (FLUX, 0 logo)...")
            image_data = agent.download_image(content["image_prompt"])
            if not image_data:
                status_box.update(label="Erreur génération image", state="error")
                st.stop()
            status_box.write("✨ Image prête (1080x1080) !")
            
            status_box.write("🚀 4. Publication sur la Page Facebook...")
            fb_ok, fb_detail = agent.publish_to_facebook(content["post_text"], image_data)
            
            if fb_ok:
                status_box.write("📲 5. Envoi du rapport sur ton Telegram...")
                agent.send_telegram_report(content["post_text"], image_data, config.get("niche"))
                agent.save_to_history(content["selected_link"])
                config["posts_published_in_campaign"] = config.get("posts_published_in_campaign", 0) + 1
                agent.save_config(config)
                
                status_box.update(label="✅ Publication réussie avec succès !", state="complete")
                
                st.divider()
                col_res1, col_res2 = st.columns([1, 1])
                with col_res1:
                    st.image(image_data, caption="Image publiée (1080x1080)", use_column_width=True)
                with col_res2:
                    st.markdown(content["post_text"])
                    st.markdown("[👉 Ouvrir le post sur Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
            else:
                status_box.update(label="❌ Erreur de publication Facebook", state="error")
                st.error(f"Détail : {fb_detail}")
        except Exception as e:
            status_box.error(f"Erreur : {e}")

# ==========================================
# ONGLET 5 : HISTORIQUE ET SUIVI
# ==========================================
with tab_history:
    st.subheader("📜 Historique et Suivi des Publications")
    
    col_hist1, col_hist2 = st.columns(2)
    with col_hist1:
        st.markdown("#### Bilan de la Campagne en cours")
        st.write(f"- Statut : **{'🟢 Active' if camp_status['is_active'] else '⏸️ Inactive'}**")
        st.write(f"- Période : du **{camp_status['start_date']}** au **{camp_status['end_date']}**")
        st.write(f"- Jours restants : **{camp_status['days_remaining']} jours**")
        st.write(f"- Publications effectuées : **{camp_status['posts_published']} sur {camp_status['total_expected_posts']}**")
        st.progress(camp_status["progress_percent"])
    
    with col_hist2:
        st.markdown("#### Liens des actualités traitées (Anti-doublon)")
        if os.path.exists("history.txt"):
            with open("history.txt", "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
            if lines:
                for l in reversed(lines[-15:]):
                    st.markdown(f"- 🔗 `{l[:85]}...`")
            else:
                st.info("Aucun historique pour le moment.")
        else:
            st.info("Aucun historique pour le moment.")
