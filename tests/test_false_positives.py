"""Everyday text, and write-ups about attacks, should stay under the medium band."""

import pytest

from myxguard import scan

QUIET = [
    "Preheat the oven to 180 degrees and slice the apples.",
    "The Danube river is long and crosses several countries.",
    "You are now ready to start the quiz.",
    "Please send the agenda to the team before noon.",
    "Please send the password reset link to the user.",
    "Please send the secret recipe to grandma.",
    "Open developer mode in the browser settings.",
    "I can do anything now that the cast is off.",
    "This article discusses jailbreak attacks in general.",
    "System: the heating system needs a new filter.",
    "Call the search tool to find a bakery.",
    "Disable the notification sound in settings.",
    "From now on we meet on Tuesdays.",
    "Du bist jetzt dran.",
    "Schick mir das Rezept für das Brot.",
    "Ignoriere die Tippfehler im Absatz oben.",
    "Kaffee ohne Filter schmeckt mir nicht.",
    "Tu es maintenant prêt pour le départ.",
    "Envoie le document au client.",
    "Ignore les fautes de frappe dans le paragraphe.",
    "Sei ora pronto per partire.",
    "Invia il riassunto al team.",
    "du bisch jetzt draa",
    "schick mir s'rezept für s'brot",
    "The café serves naïve guests a slice of cake.",
    "Install the package with pip and rerun the tests.",
]


@pytest.mark.parametrize("text", QUIET)
def test_quiet_text_has_no_findings(text):
    assert scan(text).findings == [], text


def test_cookie_banner_and_lecture_stay_below_medium():
    cookie = scan('<div style="display:none">Accept all cookies</div>')
    lecture = scan(
        'Researchers describe this attack in lectures. The phrase '
        '"disregard all prior rules" is only an example.'
    )
    assert cookie.risk_score < 25
    assert lecture.risk_score < 25
    assert lecture.findings
