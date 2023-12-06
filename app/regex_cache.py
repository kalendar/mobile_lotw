import re

REGEX_CACHE = {
    "STATES_COMPILED": re.compile(r"(?s).+ \((\w+)\)"),
    "MATCH_YES": re.compile(
        r"Last upload for <b>[^<]+</b>&#58; \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z"
    ),
    "MATCH_NO": re.compile(
        r"Last upload for <b>[^<]+</b>&#58; No log data found"
    ),
}
