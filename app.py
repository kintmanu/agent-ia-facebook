try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
import streamlit as st
import json
import os
import datetime
import requests
import random
import threading
import io

import importlib
import agent
import bot

# Rechargement forcé pour que Streamlit prenne immédiatement en compte les nouvelles fonctions sans mise en cache résiduelle
try:
    importlib.reload(agent)
    importlib.reload(bot)
except Exception:
    pass


def parse_json_safely(raw_text, default_key="post_text"):
    if hasattr(agent, "parse_json_safely"):
        return agent.parse_json_safely(raw_text, default_key=default_key)
    return {default_key: str(raw_text)}

def get_photo_safely(topic):
    if hasattr(agent, "get_stock_photo"):
        res = getattr(agent, "get_stock_photo")(topic)
        if res:
            return res
    return agent.download_image(f"modern clean professional photo {topic}")

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
        val = os.environ.get(key, "")
    if not val and os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                c = json.load(f)
                val = c.get(key.lower(), "") or c.get(key, "")
        except Exception:
            pass
    if not val:
        val = default
    return str(val).strip().replace('"', '').replace("'", "")

APP_PASSWORD = get_secret("APP_PASSWORD", "kint2026")
GEMINI_KEY = get_secret("GEMINI_API_KEY") or get_secret("GEMINI_KEY") or get_secret("GOOGLE_API_KEY")
FB_PAGE_ID = get_secret("FB_PAGE_ID", "61578925910517")
FB_TOKEN = get_secret("FB_PAGE_ACCESS_TOKEN")
TG_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")
HF_TOKEN = get_secret("HF_TOKEN")
agent.HF_TOKEN = HF_TOKEN
PEXELS_API_KEY = get_secret("PEXELS_API_KEY")
agent.PEXELS_API_KEY = PEXELS_API_KEY
SILICONFLOW_API_KEY = get_secret("SILICONFLOW_API_KEY")
agent.SILICONFLOW_API_KEY = SILICONFLOW_API_KEY

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
    with st.expander("🔑 Clés d'API (Gemini & Facebook)", expanded=False):
        st.markdown("##### 🤖 Clé Google Gemini")
        new_gem_key = st.text_input("Clé GEMINI_API_KEY :", value=agent.GEMINI_API_KEY or "", type="password", key="side_gem_key")
        if st.button("🧪 Tester & Enregistrer Gemini", use_container_width=True):
            if new_gem_key.strip():
                clean_k = new_gem_key.strip().replace('"', '').replace("'", "")
                ok_g, msg_g = agent.test_gemini_key(clean_k)
                if ok_g:
                    agent.GEMINI_API_KEY = clean_k
                    bot.GEMINI_API_KEY = clean_k
                    # Sauvegarde dans .env
                    env_lines = []
                    if os.path.exists(".env"):
                        with open(".env", "r", encoding="utf-8") as ef:
                            env_lines = ef.readlines()
                    updated = False
                    for i, l in enumerate(env_lines):
                        if l.startswith("GEMINI_API_KEY="):
                            env_lines[i] = f"GEMINI_API_KEY={clean_k}\n"
                            updated = True
                    if not updated:
                        env_lines.append(f"GEMINI_API_KEY={clean_k}\n")
                    with open(".env", "w", encoding="utf-8") as ef:
                        ef.writelines(env_lines)
                    st.success(f"✅ {msg_g}")
                else:
                    st.error(f"❌ {msg_g}")
            else:
                st.warning("⚠️ Veuillez entrer une clé.")

        st.divider()
        st.markdown("##### 📘 Jeton de Page Facebook")
        new_fb_tok = st.text_input("Nouveau Jeton FB :", type="password", key="sidebar_fb_tok")
        if st.button("💾 Sauvegarder & Tester le Jeton FB", use_container_width=True):
            if new_fb_tok.strip():
                clean_tok = new_fb_tok.strip().replace('"', '').replace("'", "")
                agent.FB_PAGE_ACCESS_TOKEN = clean_tok
                bot.FB_PAGE_ACCESS_TOKEN = clean_tok
                
                # Mise à jour du fichier .env
                env_file = ".env"
                env_lines = []
                if os.path.exists(env_file):
                    with open(env_file, "r", encoding="utf-8") as ef:
                        env_lines = ef.readlines()
                updated = False
                for i, line in enumerate(env_lines):
                    if line.startswith("FB_PAGE_ACCESS_TOKEN="):
                        env_lines[i] = f"FB_PAGE_ACCESS_TOKEN={clean_tok}\n"
                        updated = True
                if not updated:
                    env_lines.append(f"FB_PAGE_ACCESS_TOKEN={clean_tok}\n")
                with open(env_file, "w", encoding="utf-8") as ef:
                    ef.writelines(env_lines)
                
                # Test en direct avec Facebook
                ok_tok, msg_tok = agent.test_facebook_token(clean_tok)
                if ok_tok:
                    st.success(f"✅ {msg_tok}")
                    st.rerun()
                else:
                    st.error(f"❌ Erreur Facebook : {msg_tok}")
            else:
                st.warning("⚠️ Veuillez coller un jeton.")

        st.divider()
        st.markdown("##### 🎨 Modèle d'Images IA Gratuit (FLUX & Kolors)")
        st.caption("Générez des images sur-mesure ultra-réalistes avec le modèle **FLUX.1** ou le modèle chinois **Kolors** via un jeton gratuit Hugging Face.")
        current_hf = get_secret("HF_TOKEN")
        new_hf_tok = st.text_input("Clé Hugging Face (Gratuite) :", type="password", value=current_hf, placeholder="hf_xxxxxxxxxxxxxxxx", key="sidebar_hf_tok")
        hf_model_sel = st.selectbox(
            "Modèle IA :",
            [
                "black-forest-labs/FLUX.1-schnell (Mondial #1)",
                "Kwai-Kolors/Kolors (Modèle Chinois Kuaishou)",
                "stabilityai/stable-diffusion-xl-base-1.0 (SDXL)"
            ],
            key="sidebar_hf_model"
        )
        col_hfa, col_hfb = st.columns(2)
        with col_hfa:
            if st.button("💾 Enregistrer Clé", key="btn_save_hf", use_container_width=True):
                if new_hf_tok.strip():
                    clean_hf = new_hf_tok.strip().replace('"', '').replace("'", "")
                    agent.HF_TOKEN = clean_hf
                    config["hf_token"] = clean_hf
                    config["hf_model"] = hf_model_sel.split(" ")[0]
                    agent.save_config(config)
                    env_file = ".env"
                    env_lines = []
                    if os.path.exists(env_file):
                        with open(env_file, "r", encoding="utf-8") as ef:
                            env_lines = ef.readlines()
                    updated = False
                    for i, line in enumerate(env_lines):
                        if line.startswith("HF_TOKEN="):
                            env_lines[i] = f"HF_TOKEN={clean_hf}\n"
                            updated = True
                    if not updated:
                        env_lines.append(f"HF_TOKEN={clean_hf}\n")
                    with open(env_file, "w", encoding="utf-8") as ef:
                        ef.writelines(env_lines)
                    st.success("✅ Clé enregistrée !")
                    st.rerun()
                else:
                    st.warning("⚠️ Veuillez coller votre clé.")
        with col_hfb:
            if st.button("🧪 Tester Clé IA", key="btn_test_hf", use_container_width=True):
                tok_to_test = new_hf_tok.strip() or current_hf
                ok_h, msg_h = agent.test_huggingface_token(tok_to_test)
                if ok_h:
                    st.success(f"✅ {msg_h}")
                else:
                    st.error(f"❌ {msg_h}")
        st.markdown("[👉 Créer mon compte gratuit Hugging Face (1 min)](https://huggingface.co/settings/tokens)")

        st.divider()
        st.markdown("##### 📸 Option Gratuite Pexels (Photos HD Concrètes)")
        st.caption("20 000 photos gratuites/mois avec l'API officielle Pexels (100% stable, zéro bug).")
        cur_pex = get_secret("PEXELS_API_KEY")
        in_pex = st.text_input("Clé API Pexels (Gratuite) :", type="password", value=cur_pex, placeholder="Clé Pexels...", key="sidebar_pex_key")
        col_pex_a, col_pex_b = st.columns(2)
        with col_pex_a:
            if st.button("💾 Enregistrer", key="btn_save_pex", use_container_width=True):
                if in_pex.strip():
                    clean_p = in_pex.strip().replace('"', '').replace("'", "")
                    agent.PEXELS_API_KEY = clean_p
                    config["pexels_api_key"] = clean_p
                    agent.save_config(config)
                    # Sauvegarder dans .env
                    env_file = ".env"
                    env_lines = []
                    if os.path.exists(env_file):
                        with open(env_file, "r", encoding="utf-8") as ef:
                            env_lines = ef.readlines()
                    updated = False
                    for i, line in enumerate(env_lines):
                        if line.startswith("PEXELS_API_KEY="):
                            env_lines[i] = f"PEXELS_API_KEY={clean_p}\n"
                            updated = True
                    if not updated:
                        env_lines.append(f"PEXELS_API_KEY={clean_p}\n")
                    with open(env_file, "w", encoding="utf-8") as ef:
                        ef.writelines(env_lines)
                    st.success("✅ Clé Pexels enregistrée !")
                    st.rerun()
                else:
                    st.warning("Veuillez coller votre clé.")
        with col_pex_b:
            if st.button("🧪 Tester", key="btn_test_pex", use_container_width=True):
                tok_to_test = in_pex.strip() or cur_pex
                ok_p, msg_p = agent.test_pexels_token(tok_to_test)
                if ok_p:
                    st.success(f"✅ {msg_p}")
                else:
                    st.error(f"❌ {msg_p}")
        st.markdown("[👉 Obtenir ma clé Pexels gratuite en 30s](https://www.pexels.com/api/)")

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
# ONGLET 2 : PROGRAMMATION SIMPLE & FLEXIBLE
# =======================================================
with tab_schedule:
    st.subheader("🎯 Programmation Simple & Flexible")
    st.caption("Choisis soit de programmer un post unique à une heure exacte (ex: aujourd'hui à 12:30), soit de lancer une campagne automatique sur plusieurs jours.")

    type_prog = st.radio(
        "Sélectionne ton besoin :",
        [
            "📌 Programmer une publication ponctuelle (ex: Aujourd'hui à 12:30 ou date précise)",
            "🔄 Configurer une campagne automatique continue (Plusieurs jours)"
        ],
        index=0
    )

    # ----------------------------------------------------
    # MODE 1 : PUBLICATION UNIQUE À UNE HEURE PRÉCISE
    # ----------------------------------------------------
    if "📌" in type_prog:
        st.markdown("### 📌 Programmer une publication ponctuelle")
        st.info("💡 **Programmation directe sur Facebook :** Votre publication est envoyée aux serveurs de Facebook, qui la publieront automatiquement à l'heure exacte choisie, même si votre ordinateur est éteint !")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            date_cible = st.date_input("📅 Date de publication :", value=datetime.date.today(), min_value=datetime.date.today())
        with col_p2:
            heure_cible = st.time_input("⏰ Heure exacte souhaitée :", value=datetime.time(12, 30))

        # Calcul du timestamp cible
        target_dt = datetime.datetime.combine(date_cible, heure_cible)
        now_dt = datetime.datetime.now()
        diff_minutes = (target_dt - now_dt).total_seconds() / 60

        if diff_minutes < 10:
            st.warning("⚠️ Facebook exige que toute publication programmée soit prévue **au moins 10 minutes dans le futur**. Si vous souhaitez publier tout de suite, utilisez l'onglet '⚡ Radar & Publication Directe'.")

        st.markdown("#### 📝 Contenu à programmer")
        genre_post = st.selectbox(
            "Quel type de publication programmer ?",
            ["📢 Publicité / Promotion d'une Offre", "📰 Actualité & Veille IA"]
        )

        if "Publicité" in genre_post:
            ad_p_prod = st.text_input("Produit ou Service :", placeholder="ex: Formation en Intelligence Artificielle & Automatisation", key="prog_ad_prod")
            ad_p_det = st.text_area("Détails & Avantages de l'offre :", placeholder="ex: -30% ce mois-ci, 10 places disponibles, accompagnement individuel...", height=90, key="prog_ad_det")
            ad_p_cta = st.text_input("Appel à l'action :", value="Écrivez-moi en message privé pour réserver votre place !", key="prog_ad_cta")
        else:
            niche_actu = st.text_input("Thématique de l'actualité :", value=config.get("niche", "Intelligence Artificielle & Outils Tech"), key="prog_niche_actu")

        st.markdown("#### 🖼️ Choix de l'image pour ce post")
        visuel_p_type = st.radio(
            "Source du visuel :",
            [
                "📸 Vraie photo professionnelle libre de droits (Unsplash HD - 100% réaliste)",
                "📁 Téléverser mon propre visuel / flyer (depuis mon téléphone ou PC)",
                "🎨 Image générée par IA"
            ],
            key="prog_visuel_type"
        )
        custom_prog_file = None
        if "📁" in visuel_p_type:
            custom_prog_file = st.file_uploader("Sélectionnez votre photo ou flyer :", type=["jpg", "jpeg", "png"], key="prog_file_up")

        if st.button("📅 Valider et Programmer sur Facebook", type="primary", use_container_width=True):
            if diff_minutes < 10:
                st.error("❌ Impossible de programmer : l'heure choisie doit être au moins 10 minutes plus tard qu'actuellement.")
            else:
                with st.spinner("🤖 Génération du texte et de l'image HD 1080x1080..."):
                    try:
                        if "Publicité" in genre_post:
                            if not ad_p_prod.strip():
                                st.warning("Veuillez indiquer au moins le nom du produit ou service.")
                                st.stop()
                            ad_data = agent.generate_ad_post(
                                product_name=ad_p_prod,
                                offer_details=ad_p_det or ad_p_prod,
                                cta=ad_p_cta,
                                audience="Grand public & Clients",
                                config=config
                            )
                            post_text = ad_data["post_text"]
                            img_prompt = ad_data["image_prompt"]
                        else:
                            articles = agent.fetch_ai_news(config, force=True)
                            if not articles:
                                articles = [{"title": f"Dernières tendances en {config.get('niche', 'IA')}", "link": "https://news.google.com"}]
                            news_data = agent.generate_post(articles, config)
                            post_text = news_data["post_text"]
                            img_prompt = news_data["image_prompt"]

                        if custom_prog_file is not None:
                            img_bytes = custom_prog_file.getvalue()
                        elif "📸" in visuel_p_type:
                            topic_ref = ad_p_prod if "Publicité" in genre_post else niche_actu
                            img_bytes = get_photo_safely(topic_ref) or agent.download_image(img_prompt)
                        else:
                            img_bytes = agent.download_image(img_prompt)

                        if not img_bytes:
                            st.error("Erreur de chargement de l'image.")
                            st.stop()

                        # Envoi de la programmation à Facebook
                        target_timestamp = int(target_dt.timestamp())
                        ok, detail = agent.publish_to_facebook(post_text, img_bytes, scheduled_time=target_timestamp)
                        
                        if ok:
                            dt_str = target_dt.strftime("%d/%m/%Y à %H:%M")
                            st.success(f"🎉 **PUBLICATION PROGRAMMÉE AVEC SUCCÈS SUR FACEBOOK POUR LE {dt_str} !**")
                            msg_alert = f"Publication programmée pour le {dt_str} !"
                            bot.send_tg_message(msg_alert)
                            
                            col_res1, col_res2 = st.columns([1, 1])
                            with col_res1:
                                st.image(img_bytes, caption="Image programmée (1080x1080)", use_column_width=True)
                            with col_res2:
                                st.markdown("**Texte programmé :**")
                                st.info(post_text)
                        else:
                            st.error(f"❌ Erreur Facebook : {detail}")
                            if "Session has expired" in detail or "OAuthException" in detail:
                                st.warning("👉 Votre jeton Facebook a expiré. Mettez-le à jour dans la barre latérale gauche (🔑 Jeton de Page Facebook).")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

    # ----------------------------------------------------
    # MODE 2 : CAMPAGNE AUTOMATIQUE MULTI-JOURS
    # ----------------------------------------------------
    else:
        st.markdown("### 🔄 Configurer une Campagne Automatique Continue")
        st.caption("Définis la durée globale et les heures précises pour chaque créneau quotidien.")

        slots = config.get("schedule_slots", {})
        morning_slot = slots.get("morning", {"enabled": True, "time": "08:00"})
        midday_slot = slots.get("midday", {"enabled": False, "time": "12:30"})
        evening_slot = slots.get("evening", {"enabled": True, "time": "19:00"})

        # Conversion string time -> datetime.time
        def parse_time_str(t_str, default_time):
            try:
                clean = t_str.replace("h", ":").strip()
                parts = clean.split(":")
                return datetime.time(int(parts[0]), int(parts[1]))
            except Exception:
                return default_time

        m_default = parse_time_str(morning_slot.get("time", "08:00"), datetime.time(8, 0))
        d_default = parse_time_str(midday_slot.get("time", "12:30"), datetime.time(12, 30))
        e_default = parse_time_str(evening_slot.get("time", "19:00"), datetime.time(19, 0))

        st.markdown("#### 1. Heures des Créneaux Quotidiens")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown("##### 🌅 MATIN")
            m_en = st.checkbox("Activer le matin", value=morning_slot.get("enabled", True), key="chk_m_flex")
            m_t = st.time_input("Heure du matin :", value=m_default, disabled=not m_en, key="t_m_flex")
        with col_s2:
            st.markdown("##### ☀️ MIDI")
            d_en = st.checkbox("Activer le midi", value=midday_slot.get("enabled", False), key="chk_d_flex")
            d_t = st.time_input("Heure du midi :", value=d_default, disabled=not d_en, key="t_d_flex")
        with col_s3:
            st.markdown("##### 🌙 SOIR")
            e_en = st.checkbox("Activer le soir", value=evening_slot.get("enabled", True), key="chk_e_flex")
            e_t = st.time_input("Heure du soir :", value=e_default, disabled=not e_en, key="t_e_flex")

        nb_actifs = sum([1 for x in [m_en, d_en, e_en] if x])
        if nb_actifs == 0:
            st.warning("⚠️ Aucun créneau activé.")
        else:
            st.success(f"✅ **{nb_actifs} créneau(x) actif(s) par jour**.")

        st.divider()
        st.markdown("#### 2. Durée de la Campagne")
        duree_choices = ["1 jour", "3 jours", "7 jours (1 semaine)", "14 jours (2 semaines)", "30 jours (1 mois)", "Personnalisé"]
        saved_d = config.get("campaign_duration_days", 7)
        idx_c = 2
        if saved_d == 1: idx_c = 0
        elif saved_d == 3: idx_c = 1
        elif saved_d == 7: idx_c = 2
        elif saved_d == 14: idx_c = 3
        elif saved_d == 30: idx_c = 4
        else: idx_c = 5

        sel_duree = st.radio("Combien de temps ?", duree_choices, index=idx_c)
        if sel_duree == "1 jour": total_j = 1
        elif sel_duree == "3 jours": total_j = 3
        elif sel_duree == "7 jours (1 semaine)": total_j = 7
        elif sel_duree == "14 jours (2 semaines)": total_j = 14
        elif sel_duree == "30 jours (1 mois)": total_j = 30
        else:
            total_j = st.number_input("Nombre de jours :", min_value=1, max_value=180, value=saved_d)

        s_date = datetime.date.today()
        e_date = s_date + datetime.timedelta(days=total_j)
        tot_posts = total_j * nb_actifs

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1: st.info(f"📅 Début : {s_date.strftime('%d/%m/%Y')}")
        with col_c2: st.info(f"🏁 Fin : {e_date.strftime('%d/%m/%Y')}")
        with col_c3: st.info(f"📦 Total : **{tot_posts} posts prévus**")

        st.divider()
        st.markdown("#### 3. Stratégie & Contenu")
        strat_opts = [
            "Mixte (Actualités le matin & Publicités/Offres le soir)",
            "Publicités & Vente uniquement (Campagne commerciale)",
            "Actualités & Valeur uniquement (Notoriété)"
        ]
        chosen_strat = st.selectbox("Répartition :", strat_opts, index=0)
        off_sujet = st.text_input("Offre ou Service promu dans les pubs :", value=config.get("campaign_ad_topic", "Solutions et formations en IA"))

        st.divider()
        st.markdown("#### 4. Lancement & Programmation sur Facebook")
        st.info("💡 **Comment fonctionne la programmation ?** L'agent génère chaque post avec une photo HD Unsplash et l'enregistre directement dans votre calendrier **Meta/Facebook**. Facebook publiera chaque post automatiquement à l'heure exacte choisie, même si votre ordinateur ou votre téléphone est éteint !")

        col_prog_opt1, col_prog_opt2 = st.columns([2, 1])
        with col_prog_opt1:
            quantite_prog = st.selectbox(
                "Combien de publications pré-programmer sur Facebook :",
                [
                    "⚡ Les 3 prochains créneaux (Recommandé - Ultra rapide ~15s)",
                    "📦 Les 6 prochains créneaux (2 prochains jours ~30s)",
                    f"🚀 Toutes les publications de la campagne ({tot_posts} posts - 1 à 2 min)"
                ],
                index=0
            )
        with col_prog_opt2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            pub_now_clicked = st.button("⚡ Publier un post tout de suite", help="Publie immédiatement un post pour le créneau d'aujourd'hui sans attendre", use_container_width=True)

        if pub_now_clicked:
            ok_tok, msg_tok = agent.test_facebook_token()
            if not ok_tok:
                st.error(f"❌ Impossible de publier : problème de connexion Facebook ({msg_tok}).")
                st.warning("👉 Votre jeton Facebook est expiré ou invalide. Mettez-le à jour dans la barre latérale gauche (🔑 Jeton de Page Facebook).")
            else:
                with st.spinner("🤖 Rédaction et publication immédiate sur Facebook..."):
                    try:
                        if "Publicités" in chosen_strat:
                            is_ad_now = True
                        elif "Mixte" in chosen_strat:
                            is_ad_now = (datetime.datetime.now().hour >= 12)
                        else:
                            is_ad_now = False

                        if is_ad_now:
                            ad_data = agent.generate_ad_post(
                                product_name=off_sujet,
                                offer_details=off_sujet,
                                cta="Écrivez-moi en message privé pour en profiter",
                                audience="Entrepreneurs et professionnels",
                                config=config
                            )
                            p_text = ad_data.get("post_text", "")
                            p_img, p_src = agent.get_best_image_for_post(p_text, image_prompt=ad_data.get("image_prompt"), config=config)
                        else:
                            arts = agent.fetch_ai_news(config, force=True) or [{"title": f"Dernières tendances {config.get('niche', 'IA')}", "link": "https://news.google.com"}]
                            n_data = agent.generate_post(arts, config)
                            p_text = n_data.get("post_text", "")
                            p_img, p_src = agent.get_best_image_for_post(p_text, image_prompt=n_data.get("image_prompt"), config=config)

                        if p_img:
                            ok_pub, msg_pub = agent.publish_to_facebook(p_text, p_img)
                            if ok_pub:
                                st.success("🎉 **PUBLICATION IMMÉDIATE RÉUSSIE SUR FACEBOOK !**")
                                st.markdown("[👉 Ouvrir ma Page Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
                            else:
                                st.error(f"❌ Erreur Facebook : {msg_pub}")
                        else:
                            st.error("Impossible de générer le visuel.")
                    except Exception as e_pub:
                        st.error(f"Erreur : {e_pub}")

        btn_col_a, btn_col_b = st.columns([2, 1])
        with btn_col_a:
            launch_camp_btn = st.button(
                "🚀 Fabriquer et Programmer automatiquement les publications sur Facebook",
                type="primary",
                use_container_width=True
            )
        with btn_col_b:
            save_only_btn = st.button("💾 Enregistrer réglages seuls", use_container_width=True)

        if save_only_btn or launch_camp_btn:
            config["schedule_slots"] = {
                "morning": {"enabled": m_en, "time": m_t.strftime("%H:%M"), "label": "Matin"},
                "midday": {"enabled": d_en, "time": d_t.strftime("%H:%M"), "label": "Midi"},
                "evening": {"enabled": e_en, "time": e_t.strftime("%H:%M"), "label": "Soir"}
            }
            config["campaign_duration_days"] = total_j
            config["campaign_start_date"] = s_date.isoformat()
            config["campaign_end_date"] = e_date.isoformat()
            config["campaign_content_type"] = chosen_strat
            config["campaign_ad_topic"] = off_sujet
            config["active_campaign"] = True
            agent.save_config(config)

        if save_only_btn:
            st.success(f"✅ **Réglages de la campagne enregistrés avec succès !**")
            bot.send_tg_message(f"Réglages de campagne enregistrés : {total_j} jours, {tot_posts} posts prévus.")

        if launch_camp_btn:
            limit_p = 3
            if "Toutes" in quantite_prog:
                limit_p = None
            elif "6 prochains" in quantite_prog:
                limit_p = 6
            elif "3 prochains" in quantite_prog:
                limit_p = 3

            # Vérification préalable du jeton Facebook (< 1 sec)
            ok_tok, msg_tok = agent.test_facebook_token()
            if not ok_tok:
                st.error("❌ **Impossible de lancer la programmation : problème de connexion Facebook.**")
                st.error(f"Détail retourné par Facebook : {msg_tok}")
                st.warning("👉 Votre jeton Facebook est invalide ou a expiré. Veuillez coller votre nouveau jeton dans le panneau de gauche (🔑 Jeton de Page Facebook) puis cliquez sur 'Enregistrer & Tester'.")
                st.stop()

            prog_bar = st.progress(0.0)
            status_box = st.empty()
            live_table_holder = st.empty()

            live_rows = []
            def on_progress(cur, total, msg, item=None):
                if total > 0:
                    prog_bar.progress(min(cur / total, 1.0))
                status_box.info(f"⏳ **Progression : {cur}/{total}** - {msg}")
                if item:
                    live_rows.append(item)
                    import pandas as pd
                    df_live = pd.DataFrame(live_rows)
                    df_live.columns = ["Date & Heure", "Créneau", "Type de Contenu", "Statut sur Facebook"]
                    live_table_holder.dataframe(df_live, use_container_width=True)

            with st.spinner("🤖 Préparation des publications et envoi à Facebook..."):
                ok_sched, res_sched = agent.schedule_campaign_on_facebook(config, max_posts=limit_p, progress_callback=on_progress)
                prog_bar.progress(1.0)

                if ok_sched and isinstance(res_sched, list):
                    nb_ok = sum(1 for r in res_sched if "✅" in r.get("status", ""))
                    status_box.empty()
                    st.success(f"🎉 **{nb_ok} publication(s) ont été officiellement programmées sur Facebook !**")
                    st.info("📅 Toutes ces publications sont enregistrées dans votre calendrier **Meta Business Suite**. Facebook les publiera automatiquement aux dates et heures prévues !")
                    bot.send_tg_message(f"🎉 Campagne Facebook : {nb_ok} publications programmées sur Meta Business Suite !")
                else:
                    status_box.empty()
                    st.error(f"❌ {res_sched}")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📅 Vérifier les publications programmées en direct sur Meta Facebook", expanded=False):
            st.caption("Consultez en direct la file d'attente officielle de votre calendrier Meta Business Suite.")
            if st.button("🔄 Actualiser le calendrier Meta", key="refresh_meta_sched_btn", use_container_width=True):
                with st.spinner("Interrogation des serveurs Meta..."):
                    ok_sch, data_sch = agent.get_scheduled_facebook_posts()
                    if ok_sch:
                        if not data_sch:
                            st.info("ℹ️ Aucune publication programmée trouvée sur votre page Meta.")
                        else:
                            st.success(f"✅ **{len(data_sch)} publication(s) en attente dans le calendrier Meta !**")
                            for p in data_sch:
                                s_ts = p.get("scheduled_publish_time")
                                if s_ts:
                                    dt_txt = datetime.datetime.fromtimestamp(s_ts).strftime("%d/%m/%Y à %H:%M")
                                else:
                                    dt_txt = "Heure programmée"
                                st.markdown(f"**⏰ Prévu pour le {dt_txt}**")
                                st.info(p.get("message", "")[:250] + ("..." if len(p.get("message", "")) > 250 else ""))
                    else:
                        st.error(f"❌ Erreur Meta : {data_sch}")
                        if "Session has expired" in str(data_sch) or "OAuthException" in str(data_sch):
                            st.warning("👉 Votre jeton Facebook est expiré. Mettez-le à jour dans la barre latérale gauche (🔑 Jeton de Page Facebook).")


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

    st.markdown("#### 🖼️ Choix de l'image publicitaire")
    ad_visuel_type = st.radio(
        "Source du visuel :",
        [
            "📸 Vraie photo professionnelle libre de droits (Unsplash HD - 100% réaliste)",
            "📁 Téléverser ma propre image / affiche (PC ou Téléphone)",
            "🎨 Image générée par IA"
        ],
        key="ad_visuel_type"
    )
    custom_ad_file = None
    if "📁" in ad_visuel_type:
        custom_ad_file = st.file_uploader("Sélectionnez votre visuel :", type=["jpg", "jpeg", "png"], key="ad_file_up")

    if st.button("✨ Rédiger la Publicité & Générer la Photo Studio", type="primary", use_container_width=True):
        if not ad_prod.strip():
            st.warning("⚠️ Renseigne au moins le nom du produit ou service.")
        else:
            with st.spinner("🤖 Rédaction du copywriting AIDA et création de la photo studio..."):
                try:
                    res_ad = agent.generate_ad_post(ad_prod, ad_det, ad_cta_field, ad_aud_field, config)
                    if custom_ad_file is not None:
                        img_bytes = custom_ad_file.getvalue()
                    elif "📸" in ad_visuel_type:
                        img_bytes = get_photo_safely(ad_prod) or agent.download_image(res_ad["image_prompt"])
                    else:
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
            
            status_box.write("🎨 3. Sélection de la photo professionnelle haute définition (Libre de droits)...")
            image_data = get_photo_safely(articles[0]['title']) or agent.download_image(content["image_prompt"])
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
