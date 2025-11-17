"""Module for general configurations of the process"""

MAX_RETRY = 10

# ----------------------
# Queue population settings
# ----------------------
MAX_CONCURRENCY = 100  # tune based on backend capacity
MAX_RETRIES = 3  # transient failure retries per item
RETRY_BASE_DELAY = 0.5  # seconds (exponential backoff)

# ----------------------
# Solteq Tand application settings
# ----------------------
APP_PATH = "C:\\Program Files (x86)\\TM Care\\TM Tand\\TMTand.exe"


# ----------------------
# Document handling settings
# ----------------------
DOCUMENT_PATH = "C:\\Temp\\Journalizing\\Documents"
DOCUMENT_FILE_NAME = "Kvittering_Udskrivning_22_år.pdf"
DOCUMENT_TYPE = "Digital blanket"

# ----------------------
# Journal note handling settings
# ----------------------
JOURNAL_NOTE_DOCUMENT_MESSAGE = "Administrativt notat 'Anmodning om journalmateriale via digital formular. Se dokumenter'"
JOURNAL_NOTE_NO_CONSENT_MESSAGE = (
    "Administrativt notat 'Ikke samtykke til afsendelse af journalmateriale'"
)
JOURNAL_NOTE_CONSENT_MESSAGE = (
    "Administrativt notat 'Samtykke til afsendelse af journalmateriale.'"
)

# ----------------------
# Dashboard settings
# ----------------------
DASHBOARD_PROCESS_NAME = "Udskrivning 22 år"
DASHBOARD_STEP_4_NAME = "Formular indsendt"
DASHBOARD_STEP_5_NAME = "Formular journaliseret"
DASHBOARD_STEP_6_NAME = "Tandklinik registreret i Solteq Tand"
DASHBOARD_STEP_7_NAME = "Samtykke"
