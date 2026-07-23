"""Fetch the HTRC Data-API JWT token with SSL verification disabled and save it to
~/.htrc. Workaround for the IDP certificate-verify failure (htrc download / htrc.auth
crash with 'certificate verify failed'). The token endpoint is otherwise reachable;
only the cert can't be validated, so we skip verification for this one HTRC call.

Run in the capsule:  /opt/anaconda/bin/python get_token.py
Then: cat ~/.htrc  (confirm [jwt] token is populated)  ->  bash dl.sh
"""
import subprocess
import requests
import urllib3
import htrc.config as config

urllib3.disable_warnings()

capsule_id = config._get_value("jwt", "capsule_id")
ip = subprocess.check_output(
    "hostname -s -I | awk '{print $1}'", shell=True).decode().strip()
url = config.get_idp_url() + "/" + capsule_id + "/" + ip

print("requesting:", url)
r = requests.get(url, verify=False, timeout=60)
print("HTTP", r.status_code)
print("response:", r.text[:200])

data = r.json()
if isinstance(data, dict) and data.get("token"):
    config.save_jwt_token(data["token"])
    print("TOKEN SAVED (starts:", data["token"][:24], "...)")
else:
    print("NO TOKEN in response — full payload:", data)
