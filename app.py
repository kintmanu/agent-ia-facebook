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

# --- SÉCURITÉ & AUTHENTIFICATION PRIVÉE ---
APP_PASSWORD = os.environ.get("APP_PASSWORD", "kint2026")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        st.markdown("<h2 style='text-align: center;'>🔒 Espace Privé - Emmanuel Kint</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Cette application est privée. Veuillez entrer votre mot de passe pour accéder au tableau de bord.</p>", unsafe_allow_html=True)
        
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

# --- APPLICATION PRINCIPALE (ACCÈS AUTORISÉ) ---
CONFIG_FILE = "config.json"
HISTORY_FILE = "history.txt"

def load_config():
    default_config = {
        "niche": "Intelligence Artificielle & Outils Tech",
        "keywords": "intelligence artificielle IA",
        "tone": "Professionnel, captivant et vulgarisé"
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
    try:
        subprocess.run(["git", "add", "config.json"], check=False)
        subprocess.run(["git", "commit", "-m", "Mise a jour niche depuis dashboard"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception:
        pass

# BARRE LATÉRALE
with st.sidebar:
    st.title("🤖 Mon Agence IA")
    st.success("🟢 Connecté : Emmanuel Kint")
    st.caption("Application 100% en ligne et sécurisée.")
    
    st.divider()
    st.subheader("🔔 Test Rapide Telegram")
    if st.button("Envoyer un test sur mon Telegram"):
        with st.spinner("Envoi du test..."):
            res = subprocess.run(["python", "agent.py", "--test-telegram"], capture_output=True, text=True)
            if "succès" in res.stdout:
                st.success("✅ Reçu sur ton Telegram !")
            else:
                st.info(res.stdout)
                
    st.divider()
    if st.button("Se déconnecter 🔒"):
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
    idx = niches_predefinies.index(current_niche) if current_niche in niches_predefinies else 6
    
    chosen = st.selectbox("Thématique principale :", niches_predefinies, index=idx)
    if chosen == "Autre (Personnalisée)":
        final_niche = st.text_input("Écris ta thématique sur-mesure :", value=current_niche)
    else:
        final_niche = chosen

    keywords = st.text_input(
        "Mots-clés de recherche Google News (ex: IA business outils) :",
        value=config.get("keywords", "intelligence artificielle IA")
    )
    
    tone = st.select_slider(
        "Style d'écriture :",
        options=["Simple et vulgarisé", "Professionnel et engageant", "Humoristique et percutant", "Analytique et expert"],
        value=config.get("tone", "Professionnel et engageant")
    )
    
    if st.button("💾 Sauvegarder et Synchroniser", type="primary"):
        new_cfg = {"niche": final_niche, "keywords": keywords, "tone": tone}
        save_config(new_cfg)
        st.success(f"✅ Niche enregistrée : **{final_niche}** ! Tous les prochains posts cibleront ce sujet.")

with tab2:
    st.subheader("Déclencher une publication immédiate")
    st.write("Ce bouton force l'agent à rédiger un article sur la niche active, à créer la photo et à publier sur Facebook **tout en t'envoyant le rapport complet sur Telegram**.")
    
    if st.button("🚀 Forcer la publication immédiate", type="primary"):
        with st.spinner("🤖 Recherche des tendances, rédaction Gemini, image FLUX et publication Facebook en cours..."):
            res = subprocess.run(["python", "agent.py", "--force"], capture_output=True, text=True, timeout=120)
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
