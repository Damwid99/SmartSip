"""Seed domyślnych napojów i naczyń.

Jak ustalono hydration_multiplier (ml realnego nawodnienia na 1 ml napoju):

1. Domyślnie 1.0 (woda). Odchylenie tylko tam, gdzie są dowody.
2. Podwyższenie (mleko, ORS, sok 100%): 1 + dolna granica 95% CI różnicy
   względem wody z Beverage Hydration Index po 2 h (Maughan i in. 2016,
   Am J Clin Nutr 103:717-723), zaokrąglona w dół do 0.05.
   Nie bierzemy średniej, bo badanie dotyczy 1 l wypitego w 30 min, na czczo,
   u młodych mężczyzn, a w skali doby różnice między napojami zanikają
   (Tucker i in. 2015, J Am Coll Nutr 34:318-327).
3. Alkohol: obniżenie oparte na diurezie z Hobson i Maughan 2010
   (Alcohol Alcohol 45:366-373): 1 l piwa 4% dało przy pełnym nawodnieniu
   ok. 158 ml więcej moczu niż piwo bezalkoholowe (1279 vs 1121 ml w 4 h),
   czyli ok. 5 ml na gram etanolu (1 l 4% = ok. 31,6 g etanolu).
   Mnożnik = 1 - 5 * g_etanolu_na_ml_napoju. Dla wina i mocnych alkoholi
   to ekstrapolacja liniowa z jednego badania na słabym piwie.

Poziom dowodów (evidence):
  A - zmierzone bezpośrednio w BHI 2016 lub w badaniu na tym napoju,
  B - dowody pośrednie lub sprzeczne,
  C - brak danych, analogia do podobnego napoju albo konwencja.

Kofeina: dawka poniżej ok. 250-300 mg naraz nie zmienia diurezy w sposób
mierzalny (Maughan 2016, Maughan i Griffin 2003), więc nie obniża mnożnika.
Cukier i kofeinę liczyć osobno, nie przez mnożnik.
"""

import datetime
from typing import Literal, NamedTuple

from sqlmodel import Session, col, select

import src.catalog.models  # noqa: F401
import src.core.models  # noqa: F401
import src.hydration.models  # noqa: F401
import src.users.models  # noqa: F401
from src.catalog.models import Container, DrinkType
from src.core.database import engine
from src.core.security import get_password_hash
from src.users.models import Gender, Profile, User

Evidence = Literal["A", "B", "C"]


class DrinkSeed(NamedTuple):
    name: str
    multiplier: float
    icon: str
    evidence: Evidence
    note: str  # tylko dokumentacja w kodzie, nie trafia do bazy


DEFAULT_DRINKS: list[DrinkSeed] = [
    # --- Wody ---
    DrinkSeed("Woda", 1.0, "💧", "A", "Punkt odniesienia, BHI = 1,0."),
    DrinkSeed("Woda gazowana", 1.0, "🫧", "A", "BHI bez różnicy względem wody."),
    DrinkSeed("Woda smakowa (bez cukru)", 1.0, "🍋", "C", "Skład jak woda."),
    DrinkSeed(
        "Woda kokosowa",
        1.0,
        "🥥",
        "B",
        "Wyniki sprzeczne: w jednym badaniu retencja 71% vs 56% dla wody, "
        "w innym bez różnicy względem wody. Przy sprzecznych danych zostaje 1,0.",
    ),
    # --- Bez cukru ---
    DrinkSeed(
        "Cola zero / dieta",
        1.0,
        "🥤",
        "A",
        "Diet cola w BHI bez różnicy względem wody (kofeina 127 mg/l).",
    ),
    DrinkSeed("Napój gazowany bez cukru", 1.0, "🥤", "C", "Analogia do diet coli."),
    # --- Słodzone ---
    DrinkSeed(
        "Cola",
        1.0,
        "🥤",
        "A",
        "BHI bez różnicy względem wody; w 24 h także bez różnic (Tucker 2015). "
        "Cukier liczyć osobno.",
    ),
    DrinkSeed("Napój gazowany słodzony", 1.0, "🥤", "C", "Analogia do coli."),
    DrinkSeed("Lemoniada / mrożona herbata słodzona", 1.0, "🍹", "C", "Analogia do coli."),
    DrinkSeed(
        "Napój energetyczny",
        1.0,
        "⚡",
        "C",
        "Brak badań BHI. Typowa puszka 250 ml ma zwykle ok. 80 mg kofeiny, "
        "poniżej progu 250-300 mg. Liczyć kofeinę osobno.",
    ),
    DrinkSeed("Kompot", 1.0, "🍒", "C", "Brak danych, skład zbliżony do rozcieńczonego soku."),
    # --- Kawa i herbata ---
    DrinkSeed(
        "Kawa czarna",
        1.0,
        "☕",
        "A",
        "BHI bez różnicy względem wody; 4 x 200 ml/dobę nawadniało jak woda "
        "u osób pijących kawę (Killer 2014, tylko mężczyźni).",
    ),
    DrinkSeed(
        "Kawa z mlekiem (latte)",
        1.1,
        "☕",
        "C",
        "Analogia: kawa = woda, mleko daje premię; przyjęta połowa premii mleka.",
    ),
    DrinkSeed("Herbata", 1.0, "🍵", "A", "Czarna herbata w BHI, bez różnicy względem wody."),
    DrinkSeed("Herbata mrożona (niesłodzona)", 1.0, "🧊", "A", "Cold tea w BHI."),
    DrinkSeed("Herbata ziołowa / owocowa", 1.0, "🫖", "C", "Praktycznie woda, brak kofeiny."),
    # --- Mleczne ---
    DrinkSeed(
        "Mleko",
        1.20,
        "🥛",
        "A",
        "BHI 2 h: 1,50 (pełne) i 1,58 (odtłuszczone); dolna granica CI różnicy "
        "to 1,20 (pełne) i 1,28 (odtł.). Bierzemy niższą.",
    ),
    DrinkSeed(
        "Kefir / maślanka / jogurt pitny",
        1.1,
        "🥛",
        "C",
        "Skład zbliżony do mleka; przyjęta połowa premii mleka.",
    ),
    DrinkSeed(
        "Napój roślinny (soja, owies, migdały)",
        1.0,
        "🌱",
        "C",
        "Brak danych, skład bardzo zróżnicowany.",
    ),
    DrinkSeed("Kakao na mleku", 1.1, "🍫", "C", "Analogia do mleka; połowa premii."),
    # --- Soki ---
    DrinkSeed(
        "Sok owocowy 100%",
        1.05,
        "🧃",
        "A",
        "BHI 2 h sok pomarańczowy ok. 1,39, ale po korekcie na zawartość wody "
        "różnica względem wody jest nieistotna; dolna granica CI = 1,05.",
    ),
    DrinkSeed("Nektar / napój owocowy", 1.0, "🍊", "C", "Mniej składników niż sok 100%."),
    DrinkSeed("Sok warzywny", 1.0, "🍅", "C", "Brak danych."),
    DrinkSeed("Smoothie", 1.0, "🍓", "C", "Brak danych."),
    # --- Izotoniki i ORS ---
    DrinkSeed(
        "Izotonik",
        1.05,
        "⚡",
        "B",
        "W BHI (Powerade, w spoczynku) bez różnicy względem wody. Po wysiłku "
        "retencja płynu wyższa niż dla wody w badaniach rehydratacji.",
    ),
    DrinkSeed(
        "Płyn nawadniający (ORS)",
        1.15,
        "🧂",
        "A",
        "BHI 2 h: 1,54; dolna granica CI = 1,16. Badano Dioralyte (Na 55 mmol/l), "
        "polskie preparaty mogą mieć inny skład.",
    ),
    DrinkSeed(
        "Woda z elektrolitami (tabletka)",
        1.0,
        "💧",
        "C",
        "Zwykle niska zawartość sodu, brak danych.",
    ),
    # --- Inne ---
    DrinkSeed("Kombucha", 1.0, "🫖", "C", "Brak danych."),
    # --- Alkohol ---
    DrinkSeed(
        "Piwo 4-5%",
        0.8,
        "🍺",
        "B",
        "Z Hobson i Maughan 2010: ok. 0,84 dla 4%, ok. 0,80 dla 5%. "
        "W BHI lager nie różnił się istotnie od wody. Efekt słabszy przy odwodnieniu.",
    ),
    DrinkSeed("Piwo 0,0%", 1.0, "🍻", "C", "Brak bezpośredniego porównania z wodą."),
    DrinkSeed("Wino", 0.5, "🍷", "C", "Ekstrapolacja liniowa: ok. 0,53 dla 12%."),
    DrinkSeed(
        "Mocny alkohol",
        0.0,
        "🥃",
        "C",
        "Ekstrapolacja daje wartość ujemną; przycięte do 0, czyli nie liczy się do celu.",
    ),
]


class ContainerSeed(NamedTuple):
    name: str
    volume_ml: int
    icon: str


DEFAULT_CONTAINERS: list[ContainerSeed] = [
    ContainerSeed("Kieliszek", 150, "🍷"),
    ContainerSeed("Mała szklanka", 200, "🥛"),
    ContainerSeed("Szklanka / Kubek", 250, "☕"),
    ContainerSeed("Puszka", 330, "🥫"),
    ContainerSeed("Duży kubek", 350, "🍵"),
    ContainerSeed("Mała butelka", 500, "🧴"),
    ContainerSeed("Bidon sportowy", 750, "🥤"),
    ContainerSeed("Butelka 1 l", 1000, "💧"),
    ContainerSeed("Duża butelka", 1500, "🧴"),
]


def _validate() -> None:
    names = [d.name for d in DEFAULT_DRINKS]
    assert len(names) == len(set(names)), "Zduplikowane nazwy napojów"
    assert all(0.0 <= d.multiplier <= 1.5 for d in DEFAULT_DRINKS), "Mnożnik poza 0-1,5"
    cnames = [c.name for c in DEFAULT_CONTAINERS]
    assert len(cnames) == len(set(cnames)), "Zduplikowane nazwy naczyń"


def _sync_drinks(session: Session) -> None:
    """Upsert po nazwie: seed jest źródłem prawdy dla napojów systemowych."""
    for d in DEFAULT_DRINKS:
        row = session.exec(select(DrinkType).where(DrinkType.name == d.name)).first()
        if row is None:
            session.add(DrinkType(name=d.name, hydration_multiplier=d.multiplier, icon=d.icon))
        else:
            row.hydration_multiplier = d.multiplier
            row.icon = d.icon
            session.add(row)


def _sync_containers(session: Session) -> None:
    """Tylko dodaje brakujące naczynia systemowe (user_id IS NULL), nie rusza istniejących."""
    for c in DEFAULT_CONTAINERS:
        exists = session.exec(
            select(Container).where(
                Container.name == c.name,
                col(Container.user_id).is_(None),
            )
        ).first()
        if exists is None:
            session.add(Container(name=c.name, volume_ml=c.volume_ml, icon=c.icon, user_id=None))


def seed_database() -> None:
    _validate()
    with Session(engine) as session:
        # 1. Słowniki
        _sync_drinks(session)
        _sync_containers(session)

        # 2. Domyślny użytkownik testowy (ID = 1) wraz z profilem
        existing_user = session.exec(select(User)).first()
        if not existing_user:
            test_user = User(
                email="dev@smartsip.local",
                hashed_password=get_password_hash("SuperSecret123!"),
                is_active=True,
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)

            assert test_user.id is not None
            test_profile = Profile(
                user_id=test_user.id,
                username="damwid",
                gender=Gender.MALE,
                weight_kg=78.0,
                birth_date=datetime.date(1999, 5, 20),
                location="Warszawa",
            )
            session.add(test_profile)

        session.commit()

    print("Seed completed successfully.")


if __name__ == "__main__":
    seed_database()


if __name__ == "__main__":
    seed_database()
