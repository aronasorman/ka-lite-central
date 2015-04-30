import os

try:
    import local_settings
except ImportError:
    local_settings = object()


########################
# Django dependencies
########################

INSTALLED_APPS = (
    "kalite.topic_tools",  # lots of access to topic_tools
)

MIDDLEWARE_CLASSES = (
)

TEMPLATE_CONTEXT_PROCESSORS = (
)


#######################
# Set module settings
#######################

CROWDIN_PROJECT_ID      = getattr(local_settings, "CROWDIN_PROJECT_ID", None)
CROWDIN_PROJECT_KEY     = getattr(local_settings, "CROWDIN_PROJECT_KEY", None)

KA_CROWDIN_PROJECT_ID      = getattr(local_settings, "KA_CROWDIN_PROJECT_ID", None)
KA_CROWDIN_PROJECT_KEY     = getattr(local_settings, "KA_CROWDIN_PROJECT_KEY", None)

AMARA_USERNAME          = getattr(local_settings, "AMARA_USERNAME", None)
AMARA_API_KEY           = getattr(local_settings, "AMARA_API_KEY", None)

I18N_CENTRAL_DATA_PATH = os.path.join(os.path.dirname(__file__), "data")

# So KA used to have a translated_youtube_id field from the video API.
# But that seems to be gone now, so we just don't fetch any dubbed
# video data from their API.
DUBBED_LANGUAGES_FETCHED_IN_API = [] # ["es", "fr"]

KA_DUBBED_LANGUAGES_URL = "http://www.khanacademy.org/api/internal/videos/localized/all"
