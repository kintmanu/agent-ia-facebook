import random
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
import os
import sys
import json
import io
import urllib.parse
import datetime
import requests

# Imports tolérants aux pannes
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

# Variables d'environnement
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "61578925910517")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

CONFIG_FILE = "config.json"
HISTORY_FILE = "history.txt"

def get_today_str():
    return datetime.date.today().isoformat()

def load_config():
    today = get_today_str()
    seven_days_later = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    
    default_config = {
        "niche": "Intelligence Artificielle & Outils Tech",
        "keywords": "intelligence artificielle IA",
        "tone": "Professionnel, captivant et vulgarisé",
        "schedule_slots": {
            "morning": {"enabled": True, "time": "08h00", "label": "Matin"},
            "midday": {"enabled": False, "time": "13h00", "label": "Midi"},
            "evening": {"enabled": True, "time": "19h00", "label": "Soir"}
        },
        "frequency_label": "2 fois par jour (Matin & Soir)",
        "campaign_duration_days": 7,
        "campaign_start_date": today,
        "campaign_end_date": seven_days_later,
        "campaign_content_type": "Mixte (Actualités & Publicités)",
        "campaign_ad_topic": "Offres de formation, consulting et outils innovants",
        "active_campaign": True,
        "posts_published_in_campaign": 0,
        "last_updated": today
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Fusion propre avec les valeurs par défaut
                for k, v in default_config.items():
                    if k not in cfg:
                        cfg[k] = v
                if "schedule_slots" in cfg:
                    for slot in ["morning", "midday", "evening"]:
                        if slot not in cfg["schedule_slots"]:
                            cfg["schedule_slots"][slot] = default_config["schedule_slots"][slot]
                return cfg
        except Exception as e:
            print(f"Erreur lecture config: {e}")
    return default_config

def save_config(cfg):
    try:
        cfg["last_updated"] = get_today_str()
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

# Statut de campagne
def get_campaign_status(config):
    today = datetime.date.today()
    try:
        start = datetime.date.fromisoformat(config.get("campaign_start_date", today.isoformat()))
        end = datetime.date.fromisoformat(config.get("campaign_end_date", today.isoformat()))
    except Exception:
        start = today
        end = today + datetime.timedelta(days=7)

    is_active = config.get("active_campaign", True)
    total_days = max(1, (end - start).days + 1)
    days_passed = max(0, (today - start).days)
    days_remaining = max(0, (end - today).days)
    
    slots = config.get("schedule_slots", {})
    active_slots_count = sum(1 for s in slots.values() if s.get("enabled", False))
    total_expected_posts = total_days * active_slots_count

    expired = today > end
    if expired and is_active:
        is_active = False

    return {
        "is_active": is_active,
        "expired": expired,
        "start_date": start.strftime("%d/%m/%Y"),
        "end_date": end.strftime("%d/%m/%Y"),
        "total_days": total_days,
        "days_passed": min(days_passed, total_days),
        "days_remaining": days_remaining,
        "active_slots_count": active_slots_count,
        "total_expected_posts": total_expected_posts,
        "posts_published": config.get("posts_published_in_campaign", 0),
        "progress_percent": min(1.0, max(0.0, days_passed / total_days))
    }

# 2. Appel robuste à Google Gemini (Support Multi-tours + REST Fallback)

def get_available_gemini_models(api_key=None):
    key = (api_key or GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")).strip().replace('"', '').replace("'", "")
    if not key:
        return ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            models_list = res.json().get("models", [])
            supported = []
            for m in models_list:
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods and "vision" not in name:
                    supported.append(name)
            preferred = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
            ordered = [m for m in preferred if m in supported] + [m for m in supported if m not in preferred]
            if ordered:
                return ordered
    except Exception as e:
        print(f"ListModels info: {e}")
    return ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]

def call_gemini(prompt_or_contents, system_instruction=None, api_key=None):
    key = (api_key or GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")).strip().replace('"', '').replace("'", "")
    if not key:
        raise Exception("Clé GEMINI_API_KEY manquante. Renseigne-la dans la barre latérale ou les secrets.")
    
    models_to_try = get_available_gemini_models(key)
    last_error = "Aucune réponse reçue"

    # Format de payload REST standard
    if isinstance(prompt_or_contents, str):
        structured_contents = [{"parts": [{"text": prompt_or_contents}]}]
    else:
        structured_contents = prompt_or_contents

    # 1. Tentative SDK officiel google-genai si prompt simple
    if genai is not None and isinstance(prompt_or_contents, str):
        try:
            client = genai.Client(api_key=key)
            for model_name in models_to_try[:2]:
                try:
                    full_prompt = prompt_or_contents
                    if system_instruction:
                        full_prompt = f"{system_instruction}\n\n{prompt_or_contents}"
                    res = client.models.generate_content(model=model_name, contents=full_prompt)
                    if res and res.text:
                        return res.text
                except Exception as e:
                    last_error = f"SDK {model_name} : {e}"
        except Exception as e:
            last_error = f"SDK init : {e}"

    # 2. Repli REST direct avec modèles actifs découverts
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            payload = {"contents": structured_contents}
            if system_instruction:
                payload["system_instruction"] = {"parts": [{"text": system_instruction}]}
                
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    return text
            else:
                try:
                    err_data = res.json().get("error", {})
                    err_msg = err_data.get("message", res.text)
                except Exception:
                    err_msg = res.text
                last_error = f"Google {model_name} (HTTP {res.status_code}) : {err_msg}"
                print(f"REST {model_name} : {last_error}")
        except Exception as e:
            last_error = f"Réseau REST {model_name} : {e}"
            print(last_error)
            
    raise Exception(f"Impossible de contacter Gemini. Détail : {last_error}")

# 3. Le Radar d'actualités (Google News RSS avec parsing robuste)
def fetch_ai_news(config, force=False):
    history = load_history()
    query = urllib.parse.quote(config.get("keywords", "intelligence artificielle IA"))
    rss_url = f"https://news.google.com/rss/search?q={query}+when:2d&hl=fr&gl=FR&ceid=FR:fr"
    
    fresh_articles = []
    
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
        fresh_articles = [{"title": f"Dernières tendances et innovations en {config.get('niche', 'IA')}", "link": "https://news.google.com"}]

    return fresh_articles

# 4. Rédacteur de post d'actualité / tendance
def generate_post(articles, config):
    articles_text = "\n".join([f"- {a['title']} (Lien: {a['link']})" for a in articles])
    niche = config.get("niche", "Intelligence Artificielle")
    tone = config.get("tone", "Professionnel et engageant")
    
    prompt = f"""Tu es le Community Manager officiel d'Emmanuel Kint.
Niche active : {niche}
Ton : {tone}

Voici les actualités récentes :
{articles_text}

TÂCHE :
1. Choisis la nouvelle la plus percutante.
2. Rédige un post Facebook de grande qualité en français :
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

# 5. Rédacteur de Publicité / Promotion (Framework Marketing AIDA)
def generate_ad_post(product_name, offer_details, cta="Contactez-moi en message privé", audience="Grand public", config=None):
    cfg = config or load_config()
    niche = cfg.get("niche", "Business & IA")
    tone = cfg.get("tone", "Persuasif, chaleureux et professionnel")
    
    prompt = f"""Tu es un Copywriter publicitaire d'élite et expert marketing digital sur Facebook pour Emmanuel Kint.
Tu dois concevoir une publication promotionnelle/publicitaire irrésistible.

INFORMATIONS CAMPAGNE :
- Thématique : {niche}
- Produit / Service : {product_name}
- Détails de l'offre & Avantages : {offer_details}
- Appel à l'action (CTA) : {cta}
- Public ciblé : {audience}
- Ton : {tone}

STRUCTURE MARKETING (AIDA) :
1. [ATTENTION] Accroche captivante qui stoppe le défilement (stop-scroll).
2. [INTÉRÊT] Explication concrète du problème résolu et de la transformation apportée.
3. [DÉSIR] Puces claires mettant en valeur les bénéfices majeurs.
4. [ACTION] Appel à l'action immédiat ({cta}).
5. Émojis engageants et 4 hashtags ciblés.

PROMPT PHOTO PUBLICITAIRE :
- Rédige en anglais un prompt TRÈS PRÉCIS pour une superbe photographie publicitaire de studio haut de gamme, moderne et lumineuse (commercial photography, award winning studio lighting, sleek clean aesthetic, 8k).
- AUCUN texte ou logo écrit sur l'image.

FORMAT DE RÉPONSE OBLIGATOIRE EN JSON STRICT :
{{
  "post_text": "le texte publicitaire complet prêt à être publié",
  "image_prompt": "description de la photo publicitaire en anglais",
  "headline": "titre court de la promotion"
}}
Ne renvoie rien d'autre que ce JSON."""

    raw_output = call_gemini(prompt)
    clean_json = raw_output.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

# 6. Prompt image à partir d'un texte libre
def create_image_prompt_from_text(post_text):
    prompt = f"""À partir du texte de publication suivant, rédige une description visuelle (prompt en anglais de 15 à 25 mots) pour générer une photographie professionnelle de studio remarquable (style 8k studio photo, commercial lighting, clean aesthetics) :

POST :
{post_text}

Règles :
- En anglais uniquement.
- Pas de texte ou de mots écrits dans l'image.
- Pas de visages bizarres ou de créatures étranges.
- Renvoie UNIQUEMENT la description en anglais, rien d'autre."""
    try:
        res = call_gemini(prompt)
        return res.strip().replace('"', '').replace("```", "")
    except Exception:
        return "modern high-tech clean studio photography, cinematic lighting, crisp focus, 8k photo"

# 7. Téléchargement et découpage anti-filigrane (0 LOGO GARANTI)

# --- CATALOGUE DE VRAIES PHOTOS PROFESSIONNELLES LIBRES DE DROITS (UNSPLASH HD 1080x1080) ---
UNSPLASH_CATALOG = {
    "formation": [
        "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=1080&h=1080&fit=crop", # Classe moderne & apprentissage
        "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1080&h=1080&fit=crop", # Présentation tech & formation
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1080&h=1080&fit=crop", # Étudiant concentré sur laptop
        "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=1080&h=1080&fit=crop", # Travail d'équipe en formation
        "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=1080&h=1080&fit=crop", # Session de travail moderne
    ],
    "ia_tech": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1080&h=1080&fit=crop", # Circuit imprimé haute technologie
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&h=1080&fit=crop", # Ondes abstraites modernes
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1080&h=1080&fit=crop", # Écran de programmation
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1080&h=1080&fit=crop", # Data center & cybersécurité
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1080&h=1080&fit=crop", # Technologie digitale
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1080&h=1080&fit=crop", # Robotique blanche épurée
    ],
    "business": [
        "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=1080&h=1080&fit=crop", # Poignée de main accord business
        "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1080&h=1080&fit=crop", # Entrepreneur professionnel confiant
        "https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=1080&h=1080&fit=crop", # Femme d'affaires sur ordinateur
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1080&h=1080&fit=crop", # Équipe en coworking
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1080&h=1080&fit=crop", # Gratte-ciels modernes en verre
    ],
    "marketing": [
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1080&h=1080&fit=crop", # Graphiques de croissance & analytics
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=1080&h=1080&fit=crop", # Marketing sur smartphone
        "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1080&h=1080&fit=crop", # Réunion stratégique
    ],
    "ecommerce": [
        "https://images.unsplash.com/photo-1556742049-0a67c5574f73?w=1080&h=1080&fit=crop", # Paiement en ligne sécurisé
        "https://images.unsplash.com/photo-1512428559087-560fa5ceab42?w=1080&h=1080&fit=crop", # Achats sur mobile
    ]
}

def get_stock_photo(query_or_topic="Tech"):
    """Trouve une vraie photographie professionnelle HD sur Unsplash adaptée au sujet."""
    query_lower = str(query_or_topic).lower()
    
    if any(k in query_lower for k in ["format", "cours", "appren", "tuto", "etudiant", "ecole"]):
        category = "formation"
    elif any(k in query_lower for k in ["vente", "commerce", "boutique", "shopp", "produit", "client", "remise", "promo"]):
        category = "ecommerce"
    elif any(k in query_lower for k in ["market", "pub", "visibilite", "croissance", "audience", "reseau"]):
        category = "marketing"
    elif any(k in query_lower for k in ["business", "coach", "entrepr", "argent", "service", "agence", "travail"]):
        category = "business"
    else:
        category = "ia_tech"
        
    photos = UNSPLASH_CATALOG.get(category, UNSPLASH_CATALOG["ia_tech"])
    chosen_url = random.choice(photos)
    
    try:
        res = requests.get(chosen_url, timeout=20)
        if res.status_code == 200 and len(res.content) > 10000:
            return res.content
    except Exception as e:
        print(f"Erreur get_stock_photo : {e}")
        
    return None

def download_image(prompt):
    import random
    clean_prompt = prompt.strip().replace('"', '').replace("'", "")
    full_prompt = f"{clean_prompt}, clean professional photography, crisp focus, studio lighting, award winning 8k"
    encoded = urllib.parse.quote(full_prompt)
    seed = random.randint(1000, 999999)
    
    url_flux = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1120&model=flux&nologo=true&seed={seed}"
    try:
        res = requests.get(url_flux, timeout=50)
        if res.status_code == 200 and len(res.content) > 15000:
            if Image is not None:
                raw_img = Image.open(io.BytesIO(res.content))
                w, h = raw_img.size
                clean_img = raw_img.crop((0, 0, w, h - 40)).resize((1080, 1080), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                clean_img.save(out, format="JPEG", quality=95)
                return out.getvalue()
            return res.content
    except Exception as e:
        print(f"Erreur FLUX : {e}")

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

# 8. Publication Facebook
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

def publish_to_facebook(text, image_bytes, page_id=None, access_token=None, scheduled_time=None):
    token, target_id = get_page_access_token(access_token, page_id)
    if not token:
        return False, "Jeton Facebook manquant (FB_PAGE_ACCESS_TOKEN)."

    url = f"https://graph.facebook.com/v19.0/{target_id}/photos"
    data = {"caption": text, "access_token": token}
    
    if scheduled_time:
        # Programmation native sur les serveurs Facebook (UNIX timestamp en secondes)
        data["published"] = "false"
        data["scheduled_publish_time"] = str(int(scheduled_time))

    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    try:
        res = requests.post(url, data=data, files=files, timeout=45)
        if res.status_code == 200:
            if scheduled_time:
                dt_str = datetime.datetime.fromtimestamp(scheduled_time).strftime("%d/%m/%Y à %H:%M")
                return True, f"Publication programmée avec succès sur Facebook pour le {dt_str} !"
            return True, "Publication réussie avec succès sur la Page Facebook !"
        else:
            return False, res.text
    except Exception as e:
        return False, str(e)

# 9. Envoi Telegram
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

def send_telegram_preview(text, image_bytes=None, title="👁️ APERÇU DE PUBLICATION"):
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
        return r.status_code == 200, "Envoyé sur Telegram"
    except Exception as e:
        return False, str(e)

def test_telegram_connection():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "🔔 **Connexion Réussie !**\nTon bot Telegram est relié à ton Agent IA Facebook ! Tu recevras ici un rapport complet avec photo à chaque publication.",
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=25)
        return r.status_code == 200
    except Exception as e:
        print(f"Exception test Telegram : {e}")
        return False

# 10. Dialogue interactif avec VRAIE mémoire conversationnelle multi-tours
def chat_with_agent(user_message, history=None):
    config = load_config()
    niche = config.get("niche", "Tech & IA")
    tone = config.get("tone", "Professionnel et engageant")
    
    system_instruction = f"""Tu es l'assistant IA officiel et le Community Manager personnel d'Emmanuel Kint pour sa page Facebook ("Emmanuel kint").
Thématique active : {niche}
Ton de communication : {tone}

RÈGLES CAPITALES DE COMPORTEMENT (À RESPECTER SCRUPULEUSEMENT) :
1. ZERO SALUTATION :
   - Ne commence JAMAIS tes réponses par 'Bonjour Emmanuel', 'Salut !' ou des salutations.
   - Entre DIRECTEMENT et immédiatement dans le vif du sujet sans préambule de politesse.

2. RYTHME CONVERSATIONNEL ET STEP-BY-STEP (AU FUR ET À MESURE) :
   - Parle comme un collaborateur humain direct sur WhatsApp ou Telegram : sois COURT, NATUREL et CONCIS (1 à 3 phrases pour une réponse normale).
   - Ne balance JAMAIS des pavés de texte ou de longs discours inutiles.
   - Si Emmanuel évoque une idée, donne une consigne ou entame une configuration (ex: 'je veux faire une pub', 'on change le sujet', 'propose-moi quelque chose') :
     -> Réponds brièvement et pose-lui UNE SEULE question simple pour avancer étape par étape au lieu de tout déballer d'un coup.
   - Si Emmanuel demande expressément 'Rédige le post complet' ou 'Donne-moi le texte' :
     -> Rédige le post complet de façon percutante avec émojis, puces et hashtags.

3. CONTEXTE ET SUIVI PARFAIT :
   - Tu te souviens de TOUT ce qui précède dans l'échange.
   - Si Emmanuel demande un ajustement ('plus court', 'enlève ça', 'change le prix', 'ajoute des hashtags') : applique immédiatement la modification demandée sans digresser."""

    # Construction de la structure multi-tours propre
    contents = []
    if history:
        # On ne prend que les derniers échanges précédents (sans inclure le message actuel s'il y était déjà)
        clean_history = [m for m in history if m.get("content") != user_message]
        for m in clean_history[-8:]:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": str(m.get("content", ""))}]
            })

    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    reply = call_gemini(contents, system_instruction=system_instruction)
    clean_reply = reply.strip()
    for s in ["Bonjour Emmanuel !", "Bonjour Emmanuel,", "Bonjour Emmanuel", "Salut Emmanuel !", "Salut Emmanuel,", "Salut Emmanuel"]:
        if clean_reply.startswith(s):
            clean_reply = clean_reply[len(s):].strip()
    return clean_reply

# 11. Orchestration autonome respectant les créneaux et la campagne
def run_autonomous_slot(slot_name=None, force=False):
    config = load_config()
    camp_status = get_campaign_status(config)
    
    # 1. Vérification de la validité de la campagne
    if not force:
        if not camp_status["is_active"]:
            print("⏸️ Campagne inactive ou en pause. Exécution passée.")
            return False
        if camp_status["expired"]:
            print("🏁 Campagne expirée. Exécution passée.")
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                send_telegram_preview(
                    f"🏁 **Ta campagne est arrivée à son terme !**\n\nPériode : {camp_status['start_date']} au {camp_status['end_date']}\nPosts publiés : {camp_status['posts_published']}/{camp_status['total_expected_posts']}.\n\nTu peux définir et relancer une nouvelle programmation sur ta Mini-App !",
                    title="🔔 BILAN DE FIN DE CAMPAGNE"
                )
            return False

    # 2. Détection du créneau
    now_hour = datetime.datetime.utcnow().hour
    if not slot_name:
        if now_hour < 11:
            detected_slot = "morning"
        elif now_hour < 16:
            detected_slot = "midday"
        else:
            detected_slot = "evening"
    else:
        detected_slot = slot_name

    slots = config.get("schedule_slots", {})
    slot_cfg = slots.get(detected_slot, {})
    slot_label = slot_cfg.get("label", detected_slot)
    
    if not force and not slot_cfg.get("enabled", True):
        print(f"⏸️ Le créneau '{slot_label}' n'est pas activé dans la programmation d'Emmanuel. Passage.")
        return False

    print(f"🚀 Lancement de la publication pour le créneau : {slot_label}...")
    
    # 3. Choix du contenu selon la stratégie de la campagne
    content_type = config.get("campaign_content_type", "Mixte (Actualités & Publicités)")
    
    # En mode Mixte, le soir est réservé à la pub/offre, le matin aux actualités/conseils
    should_publish_ad = False
    if "Publicités" in content_type and "Actualités" not in content_type:
        should_publish_ad = True
    elif "Mixte" in content_type and detected_slot in ["evening", "midday"]:
        should_publish_ad = True

    post_content = None
    image_prompt = ""
    selected_link = ""

    if should_publish_ad:
        ad_topic = config.get("campaign_ad_topic", "Solutions et accompagnement par Emmanuel Kint")
        print(f"📢 Rédaction d'une publication publicitaire : {ad_topic}")
        ad_data = generate_ad_post(
            product_name=ad_topic,
            offer_details=ad_topic,
            cta="Laissez un message privé ou commentez sous ce post",
            audience="Entrepreneurs et passionnés",
            config=config
        )
        post_content = ad_data["post_text"]
        image_prompt = ad_data["image_prompt"]
    else:
        print("📰 Recherche d'une actualité tendance...")
        articles = fetch_ai_news(config, force=force)
        if not articles:
            print("ℹ️ Aucune actualité fraîche trouvée.")
            return False
        news_data = generate_post(articles, config)
        post_content = news_data["post_text"]
        image_prompt = news_data["image_prompt"]
        selected_link = news_data.get("selected_link", "")

    # 4. Génération de l'image HD 1080x1080 (0 logo)
    print("🎨 Génération de l'image haute définition FLUX...")
    img_bytes = download_image(image_prompt)
    if not img_bytes:
        print("⚠️ Échec du téléchargement de l'image.")
        return False

    # 5. Publication Facebook
    ok, msg = publish_to_facebook(post_content, img_bytes)
    if ok:
        if selected_link:
            save_to_history(selected_link)
        send_telegram_report(post_content, img_bytes, f"{config.get('niche')} - Créneau {slot_label}")
        
        # Incrémenter le compteur de la campagne
        config["posts_published_in_campaign"] = config.get("posts_published_in_campaign", 0) + 1
        save_config(config)
        print("✅ Publication et rapport Telegram terminés avec succès !")
        return True
    else:
        print(f"❌ Erreur Facebook : {msg}")
        return False

def main():
    if "--test-telegram" in sys.argv:
        test_telegram_connection()
        return

    force = "--force" in sys.argv
    slot_arg = None
    for arg in sys.argv:
        if arg.startswith("--slot="):
            slot_arg = arg.split("=")[1]
            
    run_autonomous_slot(slot_name=slot_arg, force=force)

if __name__ == "__main__":
    main()

def test_facebook_token(token_to_test=None):
    token = token_to_test or FB_PAGE_ACCESS_TOKEN
    if not token:
        return False, "Aucun jeton Facebook renseigné."
    try:
        res = requests.get(f"https://graph.facebook.com/v19.0/me?access_token={token}", timeout=15)
        data = res.json()
        if "error" in data:
            return False, data["error"].get("message", "Erreur Facebook")
        name = data.get("name", "Page Facebook")
        return True, f"Connexion réussie ! Identifié en tant que : {name}"
    except Exception as e:
        return False, str(e)

def test_gemini_key(key_to_test=None):
    key = (key_to_test or GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")).strip().replace('"', '').replace("'", "")
    if not key:
        return False, "Aucune clé Gemini renseignée."
    
    models = get_available_gemini_models(key)
    target_model = models[0] if models else "gemini-2.5-flash"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "Reponds uniquement: OK"}]}]}
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            return True, f"Clé Google Gemini 100% valide et fonctionnelle ! (Modèle actif : {target_model})"
        else:
            try:
                err_data = res.json().get("error", {})
                return False, f"Erreur Google (HTTP {res.status_code}) : {err_data.get('message', res.text)}"
            except Exception:
                return False, f"Erreur Google (HTTP {res.status_code}) : {res.text}"
    except Exception as e:
        return False, f"Erreur de connexion : {e}"
