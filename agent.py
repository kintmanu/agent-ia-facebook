import os
import sys
import json
import urllib.parse
import requests
import feedparser

# 1. Récupération des clés secrètes
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

if not all([GEMINI_API_KEY, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN]):
    print("❌ Erreur : Une ou plusieurs clés secrètes sont manquantes dans GitHub Secrets.")
    print(f"GEMINI_API_KEY présente: {bool(GEMINI_API_KEY)}")
    print(f"FB_PAGE_ID présente: {bool(FB_PAGE_ID)}")
    print(f"FB_PAGE_ACCESS_TOKEN présente: {bool(FB_PAGE_ACCESS_TOKEN)}")
    sys.exit(1)

HISTORY_FILE = "history.txt"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

# 2. Le Radar : Recherche des tendances IA du jour
def fetch_ai_news():
    history = load_history()
    # Flux RSS Google News sur l'actualité de l'intelligence artificielle
    rss_url = "https://news.google.com/rss/search?q=intelligence+artificielle+IA+when:2d&hl=fr&gl=FR&ceid=FR:fr"
    feed = feedparser.parse(rss_url)
    
    fresh_articles = []
    for entry in feed.entries[:10]:
        link = entry.get("link", "")
        title = entry.get("title", "")
        if link not in history and title:
            fresh_articles.append({"title": title, "link": link})
            if len(fresh_articles) >= 5:
                break
                
    return fresh_articles

# 3. Le Cerveau : Appel à Gemini
def call_gemini(prompt):
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = ""
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                last_err = response.text
                print(f"Modèle {model} indisponible ({response.status_code}), essai du suivant...")
        except Exception as e:
            last_err = str(e)
            print(f"Erreur sur {model}: {e}")
            
    raise Exception(f"Impossible de contacter Gemini : {last_err}")

def generate_post(articles):
    articles_text = "\n".join([f"- {a['title']} (Lien: {a['link']})" for a in articles])
    
    prompt = f"""Tu es un Community Manager expert et passionné par l'Intelligence Artificielle.
Voici les actualités IA récentes détectées aujourd'hui :
{articles_text}

TÂCHE :
1. Choisis la nouvelle la plus fascinante, concrète et intéressante pour le grand public.
2. Rédige un post Facebook percutant et engageant en français :
- Une phrase d'accroche captivante avec des émojis.
- Un résumé simple et vulgarisé de ce qui vient de se passer (3-4 phrases).
- Pourquoi c'est important ou ce que ça change pour l'avenir.
- Une question ouverte à la fin pour inciter les gens à commenter.
- 4 ou 5 hashtags pertinents (ex: #IntelligenceArtificielle #IA #TechNews #Innovation).
3. Donne un prompt court en anglais pour générer une illustration 3D futuriste adaptée à ce sujet.

FORMAT DE RÉPONSE OBLIGATOIRE (en JSON strict) :
{{
  "selected_link": "lien de l'article choisi parmi la liste",
  "post_text": "le texte complet du post Facebook avec émojis et hashtags",
  "image_prompt": "description visuelle en anglais pour l'image (ex: futuristic glowing AI robot processor, 3d render, neon style, 8k resolution)"
}}
Ne renvoie rien d'autre que ce JSON."""

    raw_output = call_gemini(prompt)
    clean_json = raw_output.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

# 4. L'Artiste : Téléchargement de l'image Pollinations
def download_image(prompt):
    encoded = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true&seed=42"
    print(f"🎨 Génération de l'image avec Pollinations.ai...")
    res = requests.get(image_url, timeout=40)
    if res.status_code == 200:
        return res.content
    return None

# 5. Le Facteur : Publication sur Facebook
def publish_to_facebook(text, image_bytes):
    print("🚀 Publication sur Facebook...")
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    data = {
        "caption": text,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }
    files = {
        "source": ("image.jpg", image_bytes, "image/jpeg")
    }
    res = requests.post(url, data=data, files=files, timeout=40)
    if res.status_code == 200:
        print("✅ SUCCÈS ! Le post a été publié sur ta page Facebook !")
        return True
    else:
        print(f"❌ Erreur Facebook : {res.text}")
        return False

# Orchestration
def main():
    print("🔍 Recherche des tendances IA du jour...")
    articles = fetch_ai_news()
    if not articles:
        print("ℹ️ Aucune nouvelle actualité détectée pour le moment.")
        return

    print(f"💡 {len(articles)} actualités trouvées. Choix de la meilleure et rédaction...")
    content = generate_post(articles)
    
    print("📝 Post rédigé avec succès !")
    print("--- APERÇU DU POST ---")
    print(content["post_text"])
    print("----------------------")
    
    image_data = download_image(content["image_prompt"])
    if image_data:
        success = publish_to_facebook(content["post_text"], image_data)
        if success:
            save_to_history(content["selected_link"])
    else:
        print("⚠️ Impossible de récupérer l'image, publication annulée.")

if __name__ == "__main__":
    main()
