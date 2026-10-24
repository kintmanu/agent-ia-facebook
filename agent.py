import os
import sys
import json
import io
import urllib.parse
import requests
import feedparser
from PIL import Image
from google import genai

# 1. Récupération des clés secrètes
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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
        except Exception as e:
            print(f"Erreur lecture config: {e}")
    return default_config

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

# 2. Le Radar : Recherche des tendances selon la niche configurée
def fetch_ai_news(config, force=False):
    history = load_history()
    query = urllib.parse.quote(config.get("keywords", "intelligence artificielle IA"))
    rss_url = f"https://news.google.com/rss/search?q={query}+when:2d&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(rss_url)
    
    fresh_articles = []
    for entry in feed.entries[:10]:
        link = entry.get("link", "")
        title = entry.get("title", "")
        if (force or link not in history) and title:
            fresh_articles.append({"title": title, "link": link})
            if len(fresh_articles) >= 5:
                break
                
    if not fresh_articles and force and feed.entries:
        fresh_articles = [{"title": feed.entries[0].get("title", ""), "link": feed.entries[0].get("link", "")}]
        
    return fresh_articles

# 3. Le Cerveau : Appel au SDK officiel Google Gen AI
def call_gemini(prompt):
    client = genai.Client(api_key=GEMINI_API_KEY)
    models_to_try = [
        "gemini-flash-lite-latest",
        "gemini-3.0-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash"
    ]
    
    last_err = ""
    for model_name in models_to_try:
        try:
            print(f"Tentative avec le modèle : {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response.text:
                print(f"✅ Succès avec {model_name} !")
                return response.text
        except Exception as e:
            last_err = str(e)
            print(f"⚠️ {model_name} : {e}")
            
    raise Exception(f"Impossible de contacter Gemini : {last_err}")

def generate_post(articles, config):
    articles_text = "\n".join([f"- {a['title']} (Lien: {a['link']})" for a in articles])
    niche = config.get("niche", "Intelligence Artificielle")
    tone = config.get("tone", "Professionnel et engageant")
    
    prompt = f"""Tu es un Community Manager expert et passionné.
Ta niche actuelle est : {niche}
Ton ton de communication : {tone}

Voici les actualités récentes détectées aujourd'hui :
{articles_text}

TÂCHE :
1. Choisis la nouvelle la plus fascinante, concrète et intéressante pour le grand public.
2. Rédige un post Facebook percutant et engageant en français :
- Une phrase d'accroche captivante avec des émojis.
- Un résumé simple et vulgarisé de ce qui vient de se passer (3-4 phrases).
- Pourquoi c'est important ou ce que ça change pour l'avenir.
- Une question ouverte à la fin pour inciter les gens à commenter.
- 4 ou 5 hashtags pertinents adaptés à la niche.
3. Rédige un prompt visuel en anglais TRÈS PRÉCIS pour une superbe photographie professionnelle :
- Décris une scène concrète et épurée (ex: "High-tech modern server room with sleek glowing fiber optics, cinematic depth of field, sharp 8k photo", ou "Close-up macro of a futuristic golden microchip on circuit board, professional studio lighting").
- INTERDIT : Pas de visages bizarres, pas de monstres, pas de texte écrit sur l'image.

FORMAT DE RÉPONSE OBLIGATOIRE (en JSON strict) :
{{
  "selected_link": "lien exact de l'article choisi",
  "post_text": "le texte complet du post Facebook avec émojis et hashtags",
  "image_prompt": "la description concrète de la photo en anglais"
}}
Ne renvoie rien d'autre que ce JSON."""

    raw_output = call_gemini(prompt)
    clean_json = raw_output.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

# 4. L'Artiste : Génération d'images haute qualité SANS AUCUN FILIGRANE
def download_image(prompt):
    import random
    clean_prompt = prompt.strip().replace('"', '').replace("'", "")
    full_prompt = f"{clean_prompt}, clean professional tech photography, crisp focus, studio lighting, award winning 8k"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(1000, 999999)
    
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1120&model=flux&nologo=true&seed={seed}"
    print("🎨 Génération de l'image haute définition...")
    
    try:
        res = requests.get(url, timeout=60)
        if res.status_code == 200 and len(res.content) > 15000:
            raw_img = Image.open(io.BytesIO(res.content))
            width, height = raw_img.size
            clean_img = raw_img.crop((0, 0, width, height - 40)).resize((1080, 1080), Image.Resampling.LANCZOS)
            output_bytes = io.BytesIO()
            clean_img.save(output_bytes, format="JPEG", quality=95)
            print("✨ SUCCÈS : Image nettoyée, 0 filigrane, format carré 1080x1080 !")
            return output_bytes.getvalue()
    except Exception as e:
        print(f"Erreur traitement image : {e}")

    try:
        url_fb = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1120&model=turbo&seed={seed}"
        res = requests.get(url_fb, timeout=40)
        if res.status_code == 200:
            raw_img = Image.open(io.BytesIO(res.content))
            width, height = raw_img.size
            clean_img = raw_img.crop((0, 0, width, height - 40)).resize((1080, 1080), Image.Resampling.LANCZOS)
            output_bytes = io.BytesIO()
            clean_img.save(output_bytes, format="JPEG", quality=92)
            return output_bytes.getvalue()
    except Exception as e:
        print(f"Erreur de repli : {e}")

    return None

# 5. Le Facteur : Publication sur Facebook
def get_page_access_token():
    url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={FB_PAGE_ACCESS_TOKEN}"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            pages = res.json().get("data", [])
            print("📄 Pages détectées :")
            for p in pages:
                print(f"  - Nom: {p.get('name')} | ID: {p.get('id')}")
            
            for p in pages:
                name = p.get("name", "").strip().lower()
                pid = str(p.get("id"))
                if "emmanuel" in name or pid == str(FB_PAGE_ID):
                    print(f"🎯 Page cible sélectionnée : {p.get('name')} (ID: {pid})")
                    return p.get("access_token"), pid
                    
            if pages:
                first = pages[0]
                return first.get("access_token"), first.get("id")
    except Exception as e:
        print(f"Erreur recherche page : {e}")
        
    return FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID

def publish_to_facebook(text, image_bytes):
    print("🚀 Préparation de la publication sur Facebook...")
    token, target_page_id = get_page_access_token()
    
    url = f"https://graph.facebook.com/v19.0/{target_page_id}/photos"
    data = {
        "caption": text,
        "access_token": token
    }
    files = {
        "source": ("image.jpg", image_bytes, "image/jpeg")
    }
    res = requests.post(url, data=data, files=files, timeout=40)
    if res.status_code == 200:
        print("✅ SUCCÈS TOTAL ! Publié sur ta page Facebook !")
        return True, "Publication réussie !"
    else:
        err = res.text
        print(f"❌ Erreur Facebook : {err}")
        return False, err

# 6. Le Messager : Envoi du rapport instantané sur Telegram
def send_telegram_report(text, image_bytes, niche):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram non configuré, rapport ignoré.")
        return
        
    print("📲 Envoi du rapport en direct sur ton Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"🚀 **NOUVEAU POST FACEBOOK PUBLIÉ !**\n📌 *Niche : {niche}*\n\n{text[:800]}...\n\n👉 [Voir sur Facebook](https://www.facebook.com/profile.php?id=61578925910517)"
    
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    files = {
        "photo": ("report.jpg", image_bytes, "image/jpeg")
    }
    try:
        r = requests.post(url, data=data, files=files, timeout=30)
        if r.status_code == 200:
            print("✅ Rapport Telegram envoyé avec succès sur ton téléphone !")
        else:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": f"🚀 NOUVEAU POST FACEBOOK PUBLIÉ !\nNiche : {niche}\n\n{text}\n\nhttps://www.facebook.com/profile.php?id=61578925910517"
                },
                timeout=20
            )
            print("✅ Rapport Telegram envoyé (texte) !")
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def test_telegram_connection():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID manquant.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "🔔 **Connexion Réussie !**\nTon bot Telegram est officiellement relié à ton Agent IA Facebook ! Tu recevras ici un rapport complet avec photo à chaque publication.",
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code == 200:
            print("✅ Message de test Telegram envoyé avec succès !")
            return True
        else:
            print(f"❌ Erreur Telegram ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Exception Telegram : {e}")
    return False

# Orchestration
def main():
    if "--test-telegram" in sys.argv:
        test_telegram_connection()
        return

    force = "--force" in sys.argv
    config = load_config()
    print(f"📌 Niche active : {config.get('niche')}")
    print(f"🔍 Recherche des tendances (mode forcé: {force})...")
    articles = fetch_ai_news(config, force=force)
    if not articles:
        print("ℹ️ Aucune nouvelle actualité détectée pour le moment.")
        return

    print(f"💡 {len(articles)} actualités trouvées. Choix et rédaction...")
    content = generate_post(articles, config)
    
    print("📝 Post rédigé avec succès !")
    print("--- APERÇU DU POST ---")
    print(content["post_text"])
    print("----------------------")
    
    image_data = download_image(content["image_prompt"])
    if image_data:
        success = publish_to_facebook(content["post_text"], image_data)
        if success:
            save_to_history(content["selected_link"])
            send_telegram_report(content["post_text"], image_data, config.get("niche"))
    else:
        print("⚠️ Impossible de récupérer l'image, publication annulée.")

if __name__ == "__main__":
    main()
