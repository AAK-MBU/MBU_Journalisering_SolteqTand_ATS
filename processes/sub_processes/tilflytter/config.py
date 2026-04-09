"""Configuration settings for the Tilflytter process."""

# ----------------------
# Document handling settings
# ----------------------
DOCUMENT_FILE_NAME = "Kvittering_Tilflytter.pdf"
DOCUMENT_TYPE = "Digital blanket"

# ----------------------
# Journal note handling settings
# ----------------------
ADM_NOTE_TYPE = "Administrativt notat"
ADM_NOTE_MESSAGE = "'Tilflytter - Digital formular er udfyldt. Se Dokumenter'"

ADM_NOTE_CONSENT_TYPE = "Administrativt notat"
ADM_NOTE_CONSENT_MESSAGE = "'Samtykke til at indhente journal fra tidligere tandklinik'"

ADM_NOTE_NO_CONSENT_TYPE = "Administrativt notat"
ADM_NOTE_NO_CONSENT_MESSAGE = (
    "'Ikke samtykke til at indhente journal fra tidligere tandklinik'"
)

DIAGNOSE_NOTE_CONSENT_TYPE = "Ja"
DIAGNOSE_NOTE_CONSENT_MESSAGE = "'Generelt samtykke'"
DIAGNOSE_SUB_NOTE_CONSENT_TYPE = "Informeret samtykke"
DIAGNOSE_SUB_NOTE_CONSENT_MESSAGE = "'Forældremyndighedsindehaver har på baggrund af skriftlig information i formular til tilflytter givet generelt, udtrykkeligt samtykke til fluoridbehandlinger, fissurforseglinger og røntgenundersøgelser på indikation'"

DIAGNOSE_NOTE_NO_CONSENT_TYPE = "Nej"
DIAGNOSE_NOTE_NO_CONSENT_MESSAGE = "'til generelt samtykke. Forældremyndighedsindehaver har på baggrund af skriftlig information i formular til tilflytter ikke givet generelt, udtrykkeligt samtykke til fluoridbehandlinger, fissurforseglinger og røntgenundersøgelser på indikation'"


# ----------------------
# Event handling settings
# ----------------------
EVENT_TEXT = "Tilflytter - Digital formular modtaget"

# ----------------------
# Dashboard settings
# ----------------------
DASHBOARD_PROCESS_NAME = "Tilflytter til Aarhus Kommune"
DASHBOARD_STEP_6_NAME = "Formular journaliseret"
