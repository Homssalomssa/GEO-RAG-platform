"""
Image-Knowledge Base Index

Maps satellite images to their corresponding ADM2 knowledge documents.
Enables linking of satellite imagery with structured geospatial metadata.
"""

IMAGE_KNOWLEDGE_MAP = {
    "39236": {
        "adm1": "Ariana",
        "adm2": "Ariana Ville",
        "image": "images/ariana_ville_39236.png",
        "knowledge": "knowledge/tunisia_adm2_39236_ariana_ville.txt",
        "description": "Ariana Ville satellite imagery and administrative division metadata"
    },
    "39237": {
        "adm1": "Ariana",
        "adm2": "El Mnihla",
        "image": "images/el_mnihla_39237.png",
        "knowledge": "knowledge/tunisia_adm2_39237_el_mnihla.txt",
        "description": "El Mnihla satellite imagery and administrative division metadata"
    },
    "39238": {
        "adm1": "Ariana",
        "adm2": "Ettadhamen",
        "image": "images/ettadhamen_39238.png",
        "knowledge": "knowledge/tunisia_adm2_39238_ettadhamen.txt",
        "description": "Ettadhamen satellite imagery and administrative division metadata"
    },
    "39239": {
        "adm1": "Ariana",
        "adm2": "Kalaat El Andalous",
        "image": "images/kalaat_el_andalous_39239.png",
        "knowledge": "knowledge/tunisia_adm2_39239_kalaat_el_andalous.txt",
        "description": "Kalaat El Andalous satellite imagery and administrative division metadata"
    },
    "39240": {
        "adm1": "Ariana",
        "adm2": "Raoued",
        "image": "images/raoued_39240.png",
        "knowledge": "knowledge/tunisia_adm2_39240_raoued.txt",
        "description": "Raoued satellite imagery and administrative division metadata"
    },
}


def get_image_for_adm2(adm2_code: str) -> str | None:
    """Get the image path for a given ADM2 code."""
    entry = IMAGE_KNOWLEDGE_MAP.get(str(adm2_code))
    return entry["image"] if entry else None


def get_knowledge_for_adm2(adm2_code: str) -> str | None:
    """Get the knowledge document path for a given ADM2 code."""
    entry = IMAGE_KNOWLEDGE_MAP.get(str(adm2_code))
    return entry["knowledge"] if entry else None


def get_all_adm2_codes() -> list[str]:
    """Get all available ADM2 codes."""
    return list(IMAGE_KNOWLEDGE_MAP.keys())


def get_all_image_knowledge_pairs() -> dict:
    """Get all image-knowledge pairs."""
    return IMAGE_KNOWLEDGE_MAP.copy()
