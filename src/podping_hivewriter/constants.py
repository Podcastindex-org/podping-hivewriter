LIVETEST_OPERATION_ID = "podping-livetest"
PODPING_OPERATION_ID = "podping"
STARTUP_OPERATION_ID = "podping-startup"
CURRENT_PODPING_VERSION = "0.3"

STARTUP_FAILED_UNKNOWN_EXIT_CODE = 10
STARTUP_FAILED_INVALID_POSTING_KEY_EXIT_CODE = 20
STARTUP_FAILED_HIVE_API_ERROR_EXIT_CODE = 30
PODPING_SETTINGS_KEY = "podping-settings"

# Operation JSON must be less than or equal to 8192 bytes.
HIVE_CUSTOM_OP_DATA_MAX_LENGTH = 8192
# This is a global signal to shut down until RC's recover
# Stores the RC cost of each operation to calculate an average
HIVE_HALT_TIMES = [0, 1, 1, 1, 1, 1, 1, 1, 3, 6, 9, 15, 15, 15, 15, 15, 15, 15]
