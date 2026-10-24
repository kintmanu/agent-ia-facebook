import os
import sys
import json
import io
import urllib.parse
import requests

# Imports tolérants aux pannes (ne plante jamais même si une librairie externe manque)
try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from google import genai
except ImportError:
    genai = None

# 1. Variables globales et clés
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61578925910517")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

CONFIG_FILE = "config.json"
HISTORY_FILE = "history.txt"

def load_config():
    default_config = {
        "niche": "Intelligence Artificielle & Outils Tech",
        "keywords": "intelligence artificielle IA",
        "tone": "Professionnel, captivant et vulgarisé",
        "schedule_time": "14h00",
        "frequency": "1 fois par jour"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                default_config.update(cfg)
                return default_config
        except Exception as e:
            print(f"Erreur lecture config: {e}")
    return default_config

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erreur sauvegarde config: {e}")
        return False

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(link):
    if not link:
        return
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

# 2. Appel robuste à Google Gemini (SDK officiel + repli REST automatique)
def call_gemini(prompt, api_key=None):
    key = (api_key or GEMINI_API_KEY or "").strip().replace('"', '').replace("'", "")
    if not key:
        raise Exception("Clé GEMINI_API_KEY manquante.")
    
    # 1. Tentative avec le SDK officiel google-genai si disponible
    if genai is not None:
        try:
            client = genai.Client(api_key=key)
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-flash-lite-latest",
                "gemini-3.0-flash"
            ]
            for model_name in models_to_try:
                try:
                    res = client.models.generate_content(model=model_name, contents=prompt)
                    if res and res.text:
                        return res.text
                except Exception as e:
                    print(f"SDK {model_name} : {e}")
        except Exception as e:
            print(f"Erreur init SDK genai : {e}")

    # 2. Repli par requête REST directe (ne dépend d'aucun package)
    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    return text
        except Exception as e:
            print(f"REST {model_name} : {e}")
            
    raise Exception("Impossible de contacter l'IA Gemini (vérifie ta clé GEMINI_API_KEY).")

# 3. Le Radar d'actualités (avec feedparser ou XML natif)
def fetch_ai_news(config, force=False):
    history = load_history()
    query = urllib.parse.quote(config.get("keywords", "intelligence artificielle IA"))
    rss_url = f"https://news.google.com/rss/search?q={query}+when:2d&hl=fr&gl=FR&ceid=FR:fr"
    
    fresh_articles = []
    
    # Méthode A : feedparser si installé
    if feedparser is not None:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                link = entry.get("link", "")
                title = entry.get("title", "")
                if (force or link not in history) and title:
                    fresh_articles.append({"title": title, "link": link})
                    if len(fresh_articles) >= 5:
                        break
        except Exception as e:
            print(f"Erreur feedparser : {e}")
            
    # Méthode B : Repli XML natif
    if not fresh_articles:
        try:
            import xml.etree.ElementTree as ET
            r = requests.get(rss_url, timeout=20)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:10]:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    title = title_elem.text if title_elem is not None else ""
                    link = link_elem.text if link_elem is not None else ""
                    if (force or link not in history) and title:
                        fresh_articles.append({"title": title, "link": link})
                        if len(fresh_articles) >= 5:
                            break
        except Exception as e:
            print(f"Erreur parsing XML natif : {e}")

    if not fresh_articles and force:
        fresh_articles = [{"title": f"Dernières avancées et tendances en {config.get('niche', 'IA')}", "link": "https://news.google.com"}]

    return fresh_articles

# 4. Rédacteur de post d'actualité
def generate_post(articles, config):
    articles_text = "\n".join([f"- {a['title']} (Lien: {a['link']})" for a in articles])
    niche = config.get("niche", "Intelligence Artificielle")
    tone = config.get("tone", "Professionnel et engageant")
    
    prompt = f"""Tu es le Community Manager officiel d'Emmanuel Kint.
Niche active : {niche}
Ton de communication : {tone}

Voici les actualités récentes détectées :
{articles_text}

TÂCHE :
1. Choisis la nouvelle la plus captivante pour l'audience d'Emmanuel.
2. Rédige un post Facebook percutant en français :
- Accroche captivante avec émojis.
- Résumé clair et vulgarisé (3-4 phrases).
- Pourquoi c'est important ou ce que ça change.
- Question ouverte engageante à la fin pour stimuler les commentaires.
- 4 ou 5 hashtags pertinents.
3. Rédige un prompt visuel en anglais TRÈS PRÉCIS pour une photographie professionnelle (1080x1080, studio lighting, clean, crisp focus, 8k photo).
- INTERDIT : Pas de texte déformé sur l'image, pas de monstres, pas de visages bizarres.

FORMAT DE RÉPONSE OBLIGATOIRE (JSON strict) :
{{
  "selected_link": "lien exact de l'article choisi",
  "post_text": "le texte complet du post Facebook avec émojis et hashtags",
  "image_prompt": "la description concrète de la photo en anglais"
}}
Ne renvoie rien d'autre que ce JSON."""

    raw_output = call_gemini(prompt)
    clean_json = raw_output.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

# 5. Rédacteur de Publicité / Promotion sur-mesure (Demande explicite d'Emmanuel)
def generate_ad_post(product_name, offer_details, cta, audience="Grand public", config=None):
    cfg = config or load_config()
    tone = cfg.get("tone", "Persuasif et professionnel")
    
    prompt = f"""Tu es un Copywriter publicitaire d'élite et expert marketing digital sur Facebook pour Emmanuel Kint.
Tu dois concevoir une publication promotionnelle/publicitaire ultra-vendeuse et captivante.

OFFRE ET PRODUIT :
- Produit / Service : {product_name}
- Offre & Avantages : {offer_details}
- Appel à l'action (CTA) : {cta}
- Public ciblé : {audience}
- Ton : {tone}

STRUCTURE MARKETING (Framework AIDA) :
1. [ATTENTION] Accroche percutante qui stoppe le scroll.
2. [INTÉRÊT] Explication concrète du bénéfice majeur apporté.
3. [DÉSIR] Puces démontrant pourquoi c'est la meilleure opportunité dès maintenant.
4. [ACTION] Appel à l'action clair et sans détour ({cta}).
5. Émojis modernes et professionnels.
6. 4 ou 5 hashtags ciblés.

PROMPT PHOTO PUBLICITAIRE :
- Rédige en anglais un prompt TRÈS PRÉCIS pour une photographie publicitaire studio haut de gamme, moderne et lumineuse (commercial photography, award winning studio lighting, sleek aesthetic, 8k).
- AUCUN texte ou logo écrit sur l'image, style ultra-pro.

FORMAT DE RÉPONSE STRICTEMENT JSON :
{{
  "post_text": "le texte publicitaire complet avec émojis, puces et CTA",
  "image_prompt": "description de la photo publicitaire en anglais",
  "headline": "titre court de la campagne"
}}
Ne renvoie rien d'autre que ce JSON."""

    raw_output = call_gemini(prompt)
    clean_json = raw_output.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

# 6. Prompt image à partir d'un texte libre
def create_image_prompt_from_text(post_text):
    prompt = f"""À partir du texte de publication suivant, rédige une description visuelle (prompt en anglais de 15 à 25 mots) pour générer une photographie professionnelle ou publicitaire remarquable (style 8k studio photo, commercial lighting, clean aesthetics) :

POST :
{post_text}

Règles :
- En anglais uniquement.
- Pas de texte ou de mots écrits dans l'image.
- Renvoie UNIQUEMENT la description en anglais, rien d'autre."""
    try:
        res = call_gemini(prompt)
        return res.strip().replace('"', '').replace("```", "")
    except Exception:
        return "modern high-tech clean studio photography, cinematic lighting, crisp focus, 8k photo"

# 7. Téléchargement et découpage anti-filigrane de l'image (0 LOGO GARANTI)
def download_image(prompt):
    import random
    clean_prompt = prompt.strip().replace('"', '').replace("'", "")
    full_prompt = f"{clean_prompt}, clean professional photography, crisp focus, studio lighting, award winning 8k"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(1000, 999999)
    
    # 1. Modèle FLUX
    url_flux = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1120&model=flux&nologo=true&seed={seed}"
    try:
        res = requests.get(url_flux, timeout=50)
        if res.status_code == 200 and len(res.content) > 15000:
            if Image is not None:
                raw_img = Image.open(io.BytesIO(res.content))
                w, h = raw_img.size
                # Découpage chirurgical des 40 pixels du bas pour supprimer tout logo/filigrane
                clean_img = raw_img.crop((0, 0, w, h - 40)).resize((1080, 1080), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                clean_img.save(out, format="JPEG", quality=95)
                return out.getvalue()
            return res.content
    except Exception as e:
        print(f"Erreur FLUX : {e}")

    # 2. Repli Turbo
    url_turbo = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1120&model=turbo&nologo=true&seed={seed}"
    try:
        res = requests.get(url_turbo, timeout=40)
        if res.status_code == 200 and len(res.content) > 10000:
            if Image is not None:
                raw_img = Image.open(io.BytesIO(res.content))
                w, h = raw_img.size
                clean_img = raw_img.crop((0, 0, w, h - 40)).resize((1080, 1080), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                clean_img.save(out, format="JPEG", quality=92)
                return out.getvalue()
            return res.content
    except Exception as e:
        print(f"Erreur Turbo : {e}")

    return None

# 8. Résolution et publication sur Facebook
def get_page_access_token(token_to_use=None, target_page_id=None):
    token = token_to_use or FB_PAGE_ACCESS_TOKEN
    page_id = str(target_page_id or FB_PAGE_ID or "61578925910517")
    
    if not token:
        return token, page_id

    url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={token}"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            pages = res.json().get("data", [])
            for p in pages:
                pid = str(p.get("id"))
                name = p.get("name", "").strip().lower()
                if pid == page_id or "emmanuel" in name:
                    return p.get("access_token"), pid
            if pages:
                first = pages[0]
                return first.get("access_token"), first.get("id")
    except Exception as e:
        print(f"Erreur get_page_access_token : {e}")
        
    return token, page_id

def publish_to_facebook(text, image_bytes, page_id=None, access_token=None):
    token, target_id = get_page_access_token(access_token, page_id)
    if not token:
        return False, "Jeton Facebook manquant (FB_PAGE_ACCESS_TOKEN)."

    url = f"https://graph.facebook.com/v19.0/{target_id}/photos"
    data = {
        "caption": text,
        "access_token": token
    }
    files = {
        "source": ("image.jpg", image_bytes, "image/jpeg")
    }
    try:
        res = requests.post(url, data=data, files=files, timeout=45)
        if res.status_code == 200:
            return True, "Publication réussie avec succès sur la Page Facebook !"
        else:
            return False, res.text
    except Exception as e:
        return False, str(e)

# 9. Envoi de rapports et aperçus sur Telegram
def send_telegram_report(text, image_bytes, niche="Actualités"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"🚀 **NOUVEAU POST FACEBOOK PUBLIÉ !**\n📌 *Thème : {niche}*\n\n{text[:750]}...\n\n👉 [Voir sur Facebook](https://www.facebook.com/profile.php?id={FB_PAGE_ID})"
    
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
    files = {"photo": ("report.jpg", image_bytes, "image/jpeg")}
    try:
        r = requests.post(url, data=data, files=files, timeout=30)
        return r.status_code == 200
    except Exception:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🚀 POST FACEBOOK PUBLIÉ !\n\n{text}\n\nhttps://www.facebook.com/profile.php?id={FB_PAGE_ID}"},
                timeout=20
            )
            return r.status_code == 200
        except Exception:
            return False

def send_telegram_preview(text, image_bytes=None, title="👁️ APERÇU DE POST"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram non configuré"
    
    if image_bytes:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        caption = f"{title}\n\n{text[:800]}"
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        files = {"photo": ("preview.jpg", image_bytes, "image/jpeg")}
        try:
            r = requests.post(url, data=data, files=files, timeout=30)
            if r.status_code == 200:
                return True, "Aperçu avec photo envoyé sur ton Telegram !"
        except Exception as e:
            return False, str(e)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"{title}\n\n{text}"}
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code == 200:
            return True, "Aperçu texte envoyé sur ton Telegram !"
        return False, r.text
    except Exception as e:
        return False, str(e)

def test_telegram_connection():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "🔔 **Connexion Réussie !**\nTon bot Telegram est officiellement relié à ton Agent IA Facebook ! Tu recevras ici un rapport complet avec photo à chaque publication.",
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=25)
        return r.status_code == 200
    except Exception as e:
        print(f"Exception test Telegram : {e}")
        return False

# 10. Dialogue interactif avec le Community Manager IA
def chat_with_agent(user_message, history=None):
    config = load_config()
    niche = config.get("niche", "Tech & IA")
    tone = config.get("tone", "Professionnel et engageant")
    
    system_prompt = f"""Tu es l'assistant IA officiel et le Community Manager personnel d'Emmanuel Kint.
Tu es chargé de piloter sa page Facebook professionnelle ("Emmanuel kint").
Niche active : {niche}
Ton de communication : {tone}

TES SUPER-POUVOIRS :
1. Rédiger des posts Facebook percutants (actualités, vulgarisation, conseils, débats).
2. Concevoir des publicités et offres promotionnelles qui convertissent pour ses services, produits, formations.
3. Proposer des idées de sujets tendances et de stratégies pour faire grandir la page.
4. Générer des descriptions visuelles pour des images de qualité studio.

INSTRUCTIONS :
- Réponds toujours en français chaleureux, énergique et professionnel.
- Utilise des émojis pertinents.
- Si Emmanuel te demande de rédiger un post ou une pub, donne-lui directement le texte complet prêt à être posté (avec accroche, corps, appel à l'action et hashtags).
- Propose-lui à la fin de créer l'image et de publier sur Facebook en 1 clic !"""

    prompt_lines = [system_prompt, "---"]
    if history:
        for m in history[-6:]:
            role_label = "Emmanuel" if m.get("role") == "user" else "Assistant IA"
            prompt_lines.append(f"{role_label} : {m.get('content')}")
    prompt_lines.append(f"Emmanuel : {user_message}")
    prompt_lines.append("Assistant IA :")
    
    return call_gemini("\n\n".join(prompt_lines))

# 11. Point d'entrée pour exécution autonome (GitHub Actions ou CLI)
def main():
    if "--test-telegram" in sys.argv:
        ok = test_telegram_connection()
        print("Test Telegram réussi" if ok else "Échec test Telegram")
        return

    force = "--force" in sys.argv
    config = load_config()
    print(f"📌 Niche active : {config.get('niche')}")
    articles = fetch_ai_news(config, force=force)
    if not articles:
        print("ℹ️ Aucune nouvelle actualité détectée pour le moment.")
        return

    print(f"💡 {len(articles)} actualités trouvées. Rédaction du post...")
    content = generate_post(articles, config)
    print("📝 Post rédigé !")
    
    img = download_image(content["image_prompt"])
    if img:
        ok, msg = publish_to_facebook(content["post_text"], img)
        if ok:
            save_to_history(content["selected_link"])
            send_telegram_report(content["post_text"], img, config.get("niche"))
            print("✅ Publication Facebook et rapport Telegram effectués avec succès !")
        else:
            print(f"❌ Erreur Facebook : {msg}")
    else:
        print("⚠️ Impossible de télécharger l'image.")

if __name__ == "__main__":
    main()
