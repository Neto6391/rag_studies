"""Gazetteer NER leve para Machado de Assis (sem spaCy)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


def _normalize(text: str) -> str:
    text = text.lower().replace("\r\n", "\n")
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


@dataclass(frozen=True)
class Entity:
    id: str
    label: str
    type: str  # PERSON | WORK | PHRASE | CHAPTER


# Nomes canônicos + aliases (query e texto sem acento após normalize).
_GAZETTEER: list[tuple[str, Entity]] = [
    # Dom Casmurro
    ("capitu", Entity("person:capitu", "Capitu", "PERSON")),
    ("capitolina", Entity("person:capitu", "Capitu", "PERSON")),
    ("bentinho", Entity("person:bentinho", "Bentinho", "PERSON")),
    ("betinho", Entity("person:bentinho", "Bentinho", "PERSON")),
    ("bento santiago", Entity("person:bentinho", "Bentinho", "PERSON")),
    ("escobar", Entity("person:escobar", "Escobar", "PERSON")),
    ("jose dias", Entity("person:jose-dias", "José Dias", "PERSON")),
    ("padua", Entity("person:padua", "Pádua", "PERSON")),
    ("dona gloria", Entity("person:dona-gloria", "Dona Glória", "PERSON")),
    ("d. gloria", Entity("person:dona-gloria", "Dona Glória", "PERSON")),  # grafia do corpus
    ("sancha", Entity("person:sancha", "Sancha", "PERSON")),
    # Memórias Póstumas
    ("bras cubas", Entity("person:bras-cubas", "Brás Cubas", "PERSON")),
    ("bras", Entity("person:bras-cubas", "Brás Cubas", "PERSON")),
    ("braz cubas", Entity("person:bras-cubas", "Brás Cubas", "PERSON")),  # grafia arcaica (1881)
    ("braz", Entity("person:bras-cubas", "Brás Cubas", "PERSON")),  # grafia arcaica (1881)
    ("marcela", Entity("person:marcela", "Marcela", "PERSON")),
    ("marcella", Entity("person:marcela", "Marcela", "PERSON")),  # grafia arcaica (1881)
    ("virgilía", Entity("person:virgilia", "Virgília", "PERSON")),
    ("virgilia", Entity("person:virgilia", "Virgília", "PERSON")),
    ("quincas borba", Entity("person:quincas-borba", "Quincas Borba", "PERSON")),
    ("lobo neves", Entity("person:lobo-neves", "Lobo Neves", "PERSON")),
    ("eugenio", Entity("person:eugenio", "Eugênio", "PERSON")),
    ("eugenia", Entity("person:eugenio", "Eugênio", "PERSON")),  # grafia do corpus
    # Quincas Borba (romance)
    ("rubiao", Entity("person:rubiao", "Rubião", "PERSON")),
    ("sofia", Entity("person:sofia", "Sofia", "PERSON")),
    ("sophia", Entity("person:sofia", "Sofia", "PERSON")),  # grafia arcaica (1881)
    ("christiano", Entity("person:christiano", "Christiano", "PERSON")),
    # Obras
    ("dom casmurro", Entity("work:dom-casmurro", "Dom Casmurro", "WORK")),
    ("memorias postumas", Entity("work:memorias-postumas", "Memórias Póstumas de Brás Cubas", "WORK")),
    ("memorias postumas de bras cubas", Entity("work:memorias-postumas", "Memórias Póstumas de Brás Cubas", "WORK")),
    ("quincas borba", Entity("work:quincas-borba", "Quincas Borba", "WORK")),
    ("esaú e jacó", Entity("work:esau-e-jaco", "Esaú e Jacó", "WORK")),
    ("esau e jaco", Entity("work:esau-e-jaco", "Esaú e Jacó", "WORK")),
    ("memorial de aires", Entity("work:memorial-de-aires", "Memorial de Aires", "WORK")),
    # Frases / conceitos (âncoras de retrieve)
    ("olhos de ressaca", Entity("phrase:olhos-de-ressaca", "olhos de ressaca", "PHRASE")),
    ("emplasto", Entity("phrase:emplasto", "emplasto Brás Cubas", "PHRASE")),
    ("humanitas", Entity("phrase:humanitas", "Humanitas", "PHRASE")),
    ("ao vencedor as batatas", Entity("phrase:vencedor-batatas", "ao vencedor as batatas", "PHRASE")),
    ("vencedor as batatas", Entity("phrase:vencedor-batatas", "ao vencedor as batatas", "PHRASE")),
]

# Ordenar aliases longos primeiro para match guloso.
_GAZETTEER.sort(key=lambda item: len(item[0]), reverse=True)


def extract_entities(text: str, extra: Iterable[Entity] | None = None) -> list[Entity]:
    """Extrai entidades do gazetteer presentes na query/texto."""
    norm = _normalize(text)
    found: dict[str, Entity] = {}

    for alias, entity in _GAZETTEER:
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, norm):
            found[entity.id] = entity

    if extra:
        for entity in extra:
            found[entity.id] = entity

    return list(found.values())


def all_person_aliases() -> list[tuple[str, Entity]]:
    return [(alias, ent) for alias, ent in _GAZETTEER if ent.type == "PERSON"]


def all_phrase_aliases() -> list[tuple[str, Entity]]:
    return [(alias, ent) for alias, ent in _GAZETTEER if ent.type == "PHRASE"]


def all_work_aliases() -> list[tuple[str, Entity]]:
    return [(alias, ent) for alias, ent in _GAZETTEER if ent.type == "WORK"]
