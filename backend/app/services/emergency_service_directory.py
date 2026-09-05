"""India-focused emergency contacts resolved by the backend, not the LLM."""
from __future__ import annotations

SERVICE_DIRECTORY: dict[str, list[str]] = {
    "ambulance": ["108", "102"],
    "police": ["100"],
    "fire_service": ["101"],
    "women_safety_support": ["181", "1091"],
    "child_protection": ["1098"],
    "cybercrime": ["1930"],
    "lpg": ["1906"],
    "railway": ["139"],
    "highway": ["1033"],
    "integrated_emergency": ["112"],
    "disaster": ["1070", "1077"],
    "senior_citizen": ["14567"],
}

CONTACT_NAMES = {
    "112": "Integrated Emergency Response",
    "100": "Police",
    "108": "Ambulance / Medical Emergency",
    "102": "Ambulance / Medical Emergency",
    "101": "Fire and Rescue",
    "181": "Women Helpline",
    "1091": "Women Helpline",
    "1098": "Child Helpline",
    "1930": "Cyber Crime",
    "1906": "LPG Leak",
    "1073": "Road Accident Assistance",
    "139": "Railway Assistance",
    "14567": "Senior Citizen Helpline",
    "1070": "Disaster Management",
    "1077": "Disaster Management",
}


def numbers_for_services(services: list[str]) -> dict[str, list[str]]:
    return {service: SERVICE_DIRECTORY[service] for service in services if service in SERVICE_DIRECTORY}


def emergency_contacts_for_services(services: list[str], *, serious: bool = False) -> dict[str, str]:
    numbers: list[str] = []
    if serious:
        numbers.append("112")
    for service in services:
        for number in SERVICE_DIRECTORY.get(service, []):
            if number not in numbers:
                numbers.append(number)
    return {number: CONTACT_NAMES[number] for number in numbers if number in CONTACT_NAMES}
