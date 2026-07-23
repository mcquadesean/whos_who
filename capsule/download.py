"""Download HathiTrust volumes with SSL certificate verification disabled — workaround
for the HTRC stale-cert 'certificate verify failed' that makes `htrc download` fail with
'Could not download volumes. None None'. Two sites need it: the token fetch (requests)
and the Data-API download (ssl context, which the toolkit leaves verifying — their own
'# TODO: Fix SSL cert verification'). We patch both, fetch a fresh JWT, and call the
toolkit's own download_volumes().

Usage (capsule, secure mode):
    /opt/anaconda/bin/python download.py ids.txt /media/secure_volume/vols
"""
import ssl
import sys
import requests
import urllib3

urllib3.disable_warnings()

# 1) Data-API download: make every SSL context skip server-cert verification.
_orig_ctx = ssl.create_default_context


def _noverify_ctx(*args, **kw):
    ctx = _orig_ctx(*args, **kw)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


ssl.create_default_context = _noverify_ctx

# 2) Token fetch (htrc.auth uses requests.get): force verify=False.
_orig_get = requests.get
requests.get = lambda url, **kw: _orig_get(url, **{**kw, "verify": False})

import htrc.config       # noqa: E402
import htrc.volumes      # noqa: E402

ids_file = sys.argv[1] if len(sys.argv) > 1 else "ids.txt"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "/media/secure_volume/vols"

ids = [ln.strip() for ln in open(ids_file) if ln.strip()]
print("downloading %d volumes -> %s" % (len(ids), out_dir))

token = htrc.config.get_jwt_token()
cfg = htrc.config.HtrcDataApiConfig(token=token)
cfg.cert = cfg.cert or None
cfg.key = cfg.key or None

htrc.volumes.download_volumes(ids, out_dir, data_api_config=cfg)
print("done ->", out_dir)
