"""Small French helpers shared by the engine and the adapter: elision and prepositions."""

VOWELS = "AEIOUYÉÈÊÎÔÛH"


def de(name):
    """'de Nadia', 'd'Ada'."""
    return ("d'" if name[:1].upper() in VOWELS else "de ") + name


def at(label):
    """'au Néon Bleu', 'à la Morgue', 'rue Verlaine', 'sur la promenade du Canal', 'chez Ada'."""
    low = label[:1].lower() + label[1:]
    for prefix, form in (("Le ", "au "), ("La ", "à la "), ("Les ", "aux "), ("L'", "à l'"), ("L’", "à l’"),
                         ("Chez ", "chez "), ("Logement ", "au logement "), ("Appartement ", "à l'appartement ")):
        if label.startswith(prefix):
            return form + label[len(prefix):]
    if label.startswith(("Rue ", "Place ")):
        return low  # 'rue Verlaine': no preposition in spoken French
    if label.startswith("Promenade "):
        return "sur la " + low
    if label.startswith(("Ruelle ", "Impasse ", "Allée ")):
        return "dans la " + low
    return "à " + label
