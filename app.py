import streamlit as st
import json
import os
import requests
import io
import agent

st.set_page_config(
    page_title="Mon Agence IA - Privée & Sécurisée",
    page_icon="🔒",
    layout="wide"
)

# --- GESTION DES SECRETS & NETTOYAGE ---
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

# Injection dans le module agent
agent.GEMINI_API_KEY = GEMINI_KEY
agent.FB_PAGE_ID = FB_PAGE_ID
agent.FB_PAGE_ACCESS_TOKEN = FB_TOKEN
agent.TELEGRAM_BOT_TOKEN = TG_TOKEN
agent.TELEGRAM_CHAT_ID = TG_CHAT_ID

# --- AUTHENTIFICATION PRIVÉE ---
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

# --- CONFIGURATION ---
CONFIG_FILE = "config.json"
HISTORY_FILE = "history.txt"

def load_config():
    default_config = {
        "niche": "Intelligence Artificielle & Outils Tech",
        "keywords": "intelligence artificielle IA",
        "tone": "Professionnel et engageant",
        "schedule_time": "14h00",
        "frequency": "1 fois par jour"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default_config

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

config = load_config()

# BARRE LATÉRALE
with st.sidebar:
    st.title("🤖 Mon Agence IA")
    st.success("🟢 Connecté : Emmanuel Kint")
    
    st.divider()
    st.subheader("🔔 Test Direct Telegram")
    
    if st.button("Envoyer un test sur mon Telegram", use_container_width=True):
        if not TG_TOKEN or not TG_CHAT_ID:
            st.warning("⚠️ Clés Telegram non configurées.")
        else:
            with st.spinner("Envoi du message..."):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                headers = {"User-Agent": "Mozilla/5.0"}
                payload = {
                    "chat_id": TG_CHAT_ID,
                    "text": "🔔 **BINGO !**\nTon application en ligne Streamlit est connectée avec succès à ton Telegram !",
                    "parse_mode": "Markdown"
                }
                try:
                    r = requests.post(url, headers=headers, json=payload, timeout=30)
                    if r.status_code == 200:
                        st.success("✅ Reçu sur ton Telegram !")
                    else:
                        st.error(f"❌ Erreur Telegram : {r.text}")
                except Exception as e:
                    st.error(f"❌ Erreur réseau : {e}")
                
    st.divider()
    if st.button("Se déconnecter 🔒", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# CONTENU PRINCIPAL
st.title("📊 Tableau de Bord - Publication Facebook & Telegram")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Page Facebook", "Emmanuel kint", "Active")
with col2:
    current_time_display = config.get("schedule_time", "14h00")
    current_freq_display = config.get("frequency", "1x / jour")
    st.metric("Planification Choisi", f"{current_time_display}", current_freq_display)
with col3:
    st.metric("Sécurité", "Privé (kint2026)", "Verrouillé")

st.divider()

tab1, tab2, tab3 = st.tabs(["🎯 Définir Niche & Horaires", "⚡ Publier Maintenant", "📜 Historique"])

with tab1:
    st.subheader("1. Thématique et Niche de travail")
    
    niches_predefinies = [
        "Intelligence Artificielle & Outils Tech",
        "Business en ligne, E-commerce & Marketing Digital",
        "Cryptomonnaies, Finance & Web3",
        "Motivation, Entrepreneuriat & Mindset de Succès",
        "Santé, Longévité & Biohacking",
        "Cybersécurité & Nouveautés Informatiques",
        "Autre (Personnalisée)"
    ]
    
    current_niche = config.get("niche", niches_predefinies[0])
    idx = niches_predefinies.index(current_niche) if current_niche in niches_predefinies else 0
    
    chosen = st.selectbox("Thématique principale :", niches_predefinies, index=idx)
    if chosen == "Autre (Personnalisée)":
        final_niche = st.text_input("Écris ta thématique sur-mesure :", value=current_niche)
    else:
        final_niche = chosen

    keywords = st.text_input(
        "Mots-clés de recherche Google News (ex: IA business outils) :",
        value=config.get("keywords", "intelligence artificielle IA")
    )
    
    tone_options = [
        "Simple et vulgarisé",
        "Professionnel et engageant",
        "Humoristique et percutant",
        "Analytique et expert"
    ]
    saved_tone = config.get("tone", tone_options[1])
    current_tone = saved_tone if saved_tone in tone_options else tone_options[1]
    tone = st.select_slider("Style d'écriture :", options=tone_options, value=current_tone)
    
    st.divider()
    st.subheader("2. Choisir l'Heure et la Fréquence de Publication")
    col_h1, col_h2 = st.columns(2)
    
    heures_possibles = ["07h00", "08h00", "09h00", "10h00", "12h00", "14h00", "16h00", "18h00", "20h00", "22h00"]
    saved_h = config.get("schedule_time", "14h00")
    h_idx = heures_possibles.index(saved_h) if saved_h in heures_possibles else 5
    
    with col_h1:
        chosen_time = st.selectbox("Heure de publication automatique :", heures_possibles, index=h_idx)
    with col_h2:
        frequences = ["1 fois par jour", "2 fois par jour (Matin & Soir)", "Sur demande uniquement (Pas d'auto)"]
        saved_f = config.get("frequency", "1 fois par jour")
        f_idx = frequences.index(saved_f) if saved_f in frequences else 0
        chosen_freq = st.selectbox("Fréquence :", frequences, index=f_idx)
    
    if st.button("💾 Enregistrer la Niche et les Nouveaux Horaires", type="primary"):
        new_cfg = {
            "niche": final_niche,
            "keywords": keywords,
            "tone": tone,
            "schedule_time": chosen_time,
            "frequency": chosen_freq
        }
        save_config(new_cfg)
        st.success(f"✅ Enregistré ! Thématique : **{final_niche}** | Heure choisie : **{chosen_time}** ({chosen_freq})")
        st.rerun()

with tab2:
    st.subheader("Publication Instantanée en Direct")
    st.write("Ce bouton lance l'agent en direct sous tes yeux : recherche de tendance, rédaction Gemini, image FLUX, publication Facebook et envoi Telegram.")
    
    if st.button("🚀 Lancer la Publication Immédiate", type="primary", use_container_width=True):
        status_box = st.status("🤖 L'agent se met au travail...", expanded=True)
        
        try:
            status_box.write("🔍 1. Recherche des tendances d'actualités...")
            articles = agent.fetch_ai_news(config, force=True)
            if not articles:
                status_box.error("Aucun article trouvé.")
                st.stop()
                
            status_box.write(f"📝 2. Rédaction du post par Gemini pour la niche '{config.get('niche')}'...")
            content = agent.generate_post(articles, config)
            
            status_box.write("🎨 3. Création de la photo haute résolution (0 filigrane)...")
            image_data = agent.download_image(content["image_prompt"])
            if not image_data:
                status_box.error("Échec de la génération d'image.")
                st.stop()
                
            status_box.write("🚀 4. Publication officielle sur la page Facebook 'Emmanuel kint'...")
            fb_ok, fb_detail = agent.publish_to_facebook(content["post_text"], image_data)
            
            if fb_ok:
                status_box.write("📲 5. Envoi du rapport en direct sur ton Telegram...")
                agent.send_telegram_report(content["post_text"], image_data, config.get("niche"))
                agent.save_to_history(content["selected_link"])
                status_box.update(label="🎉 SUCCÈS TOTAL ! Publié sur Facebook & Reçu sur Telegram !", state="complete")
                st.balloons()
                
                col_res1, col_res2 = st.columns([1, 1])
                with col_res1:
                    st.image(image_data, caption="Photo publiée sur Facebook", use_container_width=True)
                with col_res2:
                    st.success("✅ Post en ligne sur Facebook !")
                    st.markdown(content["post_text"])
                    st.markdown("[👉 Ouvrir le post sur Facebook](https://www.facebook.com/profile.php?id=61578925910517)")
            else:
                status_box.error(f"❌ Détail de l'erreur Facebook : {fb_detail}")
                
        except Exception as e:
            status_box.error(f"Erreur : {e}")

with tab3:
    st.subheader("Historique des publications")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        st.write(f"📈 Total d'articles mémorisés : **{len(lines)}**")
        for l in lines[-10:]:
            st.markdown(f"- 🔗 `{l[:85]}...`")
    else:
        st.info("Aucun historique pour le moment.")
