"""Characters voiced by a model. The engine decides what is said; the model only says it in character."""

from aiquery import ask_model

import re

from city import NAMES, TRAIT_TEXT

MODEL, PROVIDER = "gpt-6-luna", "openai"
SYSTEM = """Tu écris les répliques d'un personnage dans un jeu d'enquête, ambiance néon noir : une ville sous la pluie,
des enseignes qui grésillent, un bar mal famé, un tripot, un cabaret, et un détective en trench qui pose des questions.
Tu reçois sa fiche, la conversation en cours, la question du détective et le contenu exact de sa réponse.
Tu réécris ce contenu en une ou deux phrases, à la première personne, en français parlé, dans le caractère du personnage.
Règles :
- Tu transmets exactement l'information donnée, avec les mêmes détails (couleur, lieu, nom), sans en ajouter ni en retirer.
- Tu n'inventes aucun fait sur l'enquête, la victime ou d'autres personnes.
- Tu ne révèles rien de la fiche au-delà de ce que dit le contenu, et jamais le rôle.
- Le personnage parle comme un habitant, pas comme un guide de jeu : aucun conseil au détective, aucun ordre de recouper, de vérifier des horaires ou de consulter un document.
- Une hésitation reste une hésitation : « peut-être » ne devient jamais un fait certain. Aucun nom ajouté.
- Pas de guillemets, pas de didascalies, pas de nom du personnage : juste la réplique."""


def speak(persona, dialogue, question, intent):
    """One line of dialogue. Falls back to the plain intent if the model drops a detail."""
    sheet = "\n".join(f"- {k} : {v}" for k, v in persona.items())
    history = "\n".join(f"Détective : {q}\n{persona['nom']} : {a}" for q, a in dialogue) or "(début de la conversation)"
    prompt = f"Fiche :\n{sheet}\n\nConversation :\n{history}\n\nDétective : {question}\nContenu de la réponse : {intent}"
    keywords = [w[:4].lower() for w in TRAIT_TEXT.values() if len(w) > 2 and w in intent]
    for _ in range(2):
        line = (ask_model(prompt, model=MODEL, provider=PROVIDER, system_prompt=SYSTEM).content or "").strip()
        invented_names = any(re.search(rf"\b{re.escape(name)}\b", line) and not re.search(rf"\b{re.escape(name)}\b", intent)
                             for names in NAMES.values() for name in names)
        coaching = any(phrase in line.lower() for phrase in ("recoupez", "recouper", "croisez", "vérifiez", "cherchez", "leurs horaires restent"))
        invented_numbers = not set(re.findall(r"\d+", line)) <= set(re.findall(r"\d+", intent))
        if line and not invented_names and not coaching and not invented_numbers and all(k in line.lower() for k in keywords):
            return line
    return intent
