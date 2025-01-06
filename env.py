from settings import EmailSettings, Settings

## Populate these settings values!

SETTINGS = Settings(
    database_connection="",
    lotw_login_url="https://lotw.arrl.org/lotwuser/default",
    QSO_url="https://lotw.arrl.org/lotwuser/qsos?qso_query=1&awg_id=DXCC&ac_acct=1&qso_callsign=&qso_owncall=&qso_startdate=&qso_starttime=&qso_enddate=&qso_endtime=&qso_mode=&qso_band=&qso_qsl=yes&qso_dxcc=&qso_sort=QSL+Date&qso_descend=yes&acct_sel=DXCC%3B1",
    database_key="",
    session_key="",
    email_settings=EmailSettings(
        sender_address="",
        SMTP_address="",
        SMTP_port=25,
    ),
)
