"""Module for general configurations of the process"""

MAX_RETRY = 10

# ----------------------
# Subprocess settings
# ----------------------
SUBPROCESS_CHOICES = ["udskrivning22ar", "tilflytter", "fritvalg"]

# ----------------------
# Queue population settings
# ----------------------
MAX_CONCURRENCY = 100  # tune based on backend capacity
MAX_RETRIES = 3  # transient failure retries per item
RETRY_BASE_DELAY = 0.5  # seconds (exponential backoff)

# ----------------------
# Document handling settings
# ----------------------
DOCUMENT_PATH = "C:\\Temp\\Journalizing\\Documents"

# ----------------------
# Solteq Tand application settings
# ----------------------
APP_PATH = "C:\\Program Files (x86)\\TM Care\\TM Tand\\TMTand.exe"
