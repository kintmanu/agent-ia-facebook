import streamlit as st
import json
import os
import subprocess
import requests

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
    # Nettoyage des espaces ou guillemets accidentels
    return str(val).strip().replace('"', '').replace("'", "")

APP_PASSWORD = get_secret("APP_PASSWORD", "kint2026")
GEMINI_KEY = get_secret("GEMINI_API_KEY")
FB_TOKEN = get_secret("FB_PAGE_ACCESS_TOKEN")
TG_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

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
        "tone": "Professionnel et engageant"
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

# BARRE LATÉRALE
with st.sidebar:
    st.title("🤖 Mon Agence IA")
    st.success("🟢 Connecté : Emmanuel Kint")
    
    st.divider()
    st.subheader("🔔 Test Direct Telegram")
    
    if st.button("Envoyer un test sur mon Telegram", use_container_width=True):
        if not TG_TOKEN or not TG_CHAT_ID:
            st.warning("⚠️ Clés Telegram manquantes.")
        else:
            with st.spinner("Connexion sécurisée à Telegram en cours..."):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                payload = {
                    "chat_id": TG_CHAT_ID,
                    "text": "🔔 **BINGO !**\nTon application en ligne Streamlit est connectée avec succès à ton Telegram !",
                    "parse_mode": "Markdown"
                }
                try:
                    r = requests.post(url, headers=headers, json=payload, timeout=30)
                    if r.status_code == 200:
                        st.success("✅ Reçu sur ton Telegram ! Regarde ton téléphone !")
                    else:
                        st.error(f"❌ Réponse Telegram ({r.status_code}) : {r.text}")
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
    st.metric("Planification", "Chaque matin (09h00)", "Automatique")
with col3:
    st.metric("Sécurité", "Privé (kint2026)", "Verrouillé")

st.divider()

tab1, tab2, tab3 = st.tabs(["🎯 Définir la Niche", "⚡ Publier Maintenant (Forcé)", "📜 Historique"])

config = load_config()

with tab1:
    st.subheader("Sur quelle thématique l'agent doit-il travailler ?")
    
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
    
    if st.button("💾 Sauvegarder et Synchroniser la Niche", type="primary"):
        new_cfg = {"niche": final_niche, "keywords": keywords, "tone": tone}
        save_config(new_cfg)
        st.success(f"✅ Niche enregistrée : **{final_niche}** ! Tous les prochains posts cibleront ce sujet.")

with tab2:
    st.subheader("Déclencher une publication immédiate")
    st.write("Ce bouton force l'agent à rédiger un article sur la niche active, à créer la photo et à publier sur Facebook **tout en t'envoyant le rapport complet sur Telegram**.")
    
    if st.button("🚀 Forcer la publication immédiate", type="primary"):
        env = dict(os.environ)
        if hasattr(st, "secrets"):
            try:
                for k, v in st.secrets.items():
                    env[k] = str(v)
            except Exception:
                pass
                
        with st.spinner("🤖 Recherche des tendances, rédaction Gemini, image FLUX et publication Facebook en cours..."):
            res = subprocess.run(["python", "agent.py", "--force"], env=env, capture_output=True, text=True, timeout=120)
            st.code(res.stdout)
            if "SUCCÈS TOTAL" in res.stdout:
                st.balloons()
                st.success("🎉 C'est fait ! Va voir ta page Facebook et ton Telegram !")
            else:
                st.info("Traitement terminé. Regarde le journal ci-dessus.")

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
