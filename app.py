import streamlit as st
import json
import os
import subprocess
import requests

st.set_page_config(
    page_title="Mon Agence IA - Facebook & Telegram",
    page_icon="🤖",
    layout="wide"
)

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
    # Tente de synchroniser avec GitHub si git est présent
    try:
        subprocess.run(["git", "add", "config.json"], check=False)
        subprocess.run(["git", "commit", "-m", "Mise a jour de la niche via la mini-app"], check=False)
        subprocess.run(["git", "push", "origin", "main"], check=False)
    except Exception:
        pass

# --- HEADER ---
st.title("🤖 Mon Agence IA Autonome")
st.caption("Pilote ta page Facebook et tes rapports Telegram du bout des doigts, sans coder.")

col1, col2, col3 = st.columns(3)
with col1:
    st.success("📱 **Page connectée :** Emmanuel kint")
with col2:
    st.info("⏰ **Publication automatique :** Tous les matins (09h00)")
with col3:
    st.warning("🔔 **Rapports :** Bot Telegram activé")

st.divider()

# --- NAVIGATION ONGLETS ---
tab1, tab2, tab3 = st.tabs(["🎯 Piloter la Niche & l'Agent", "🚀 Déclencher une Publication", "📜 Historique & Mémoire"])

config = load_config()

with tab1:
    st.subheader("1. Choisir sur quelle niche l'agent doit travailler")
    
    niches_predefinies = [
        "Intelligence Artificielle & Outils Tech",
        "Business en ligne, E-commerce & Marketing",
        "Cryptomonnaies, Finance & Web3",
        "Motivation, Entrepreneuriat & Mindset",
        "Santé, Bien-être & Longévité",
        "Cybersécurité & Nouveaux Métiers de la Tech",
        "Autre (Personnalisée)"
    ]
    
    current_niche = config.get("niche", niches_predefinies[0])
    index = niches_predefinies.index(current_niche) if current_niche in niches_predefinies else 6
    
    selected_niche = st.selectbox("Sélectionne la thématique :", niches_predefinies, index=index)
    
    if selected_niche == "Autre (Personnalisée)":
        final_niche = st.text_input("Écris ta niche personnalisée :", value=current_niche)
    else:
        final_niche = selected_niche

    keywords = st.text_input(
        "Mots-clés pour la recherche d'actualités (séparés par un espace) :",
        value=config.get("keywords", "intelligence artificielle IA")
    )
    
    tone = st.select_slider(
        "Ton de la rédaction :",
        options=["Simple et vulgarisé", "Professionnel et engageant", "Humoristique et percutant", "Analytique et expert"],
        value=config.get("tone", "Professionnel et engageant")
    )
    
    if st.button("💾 Enregistrer et Synchroniser la Niche", type="primary"):
        new_cfg = {
            "niche": final_niche,
            "keywords": keywords,
            "tone": tone
        }
        save_config(new_cfg)
        st.success(f"✅ Niche mise à jour avec succès : **{final_niche}** ! L'agent utilisera ce sujet pour ses prochains posts.")

with tab2:
    st.subheader("2. Lancer une publication immédiate")
    st.write("Tu peux déclencher manuellement une publication en direct sur ta page Facebook avec rapport instantané sur ton Telegram.")
    
    if st.button("⚡ Publier maintenant sur Facebook & Telegram", type="primary"):
        with st.spinner("🤖 L'agent scanne le web, rédige le post, génère la photo et publie..."):
            try:
                res = subprocess.run(["python", "agent.py"], capture_output=True, text=True, timeout=120)
                st.code(res.stdout)
                if "SUCCÈS TOTAL" in res.stdout:
                    st.balloons()
                    st.success("🎉 Publication réussie ! Regarde ta page Facebook et ton Telegram !")
                else:
                    st.warning("Publication terminée. Vérifie le compte-rendu ci-dessus.")
            except Exception as e:
                st.error(f"Erreur d'exécution : {e}")

with tab3:
    st.subheader("3. Historique des articles déjà traités")
    st.caption("L'agent se souvient de ces liens pour ne jamais poster deux fois le même sujet.")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        st.write(f"📊 **Nombre d'articles dans la mémoire :** {len(lines)}")
        for l in lines[-10:]:
            st.markdown(f"- 🔗 `{l[:80]}...`")
    else:
        st.info("Aucun historique pour le moment.")
