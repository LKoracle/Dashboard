#!/opt/dashboard/venv/bin/python
"""Certbot HTTP-01: use existing nginx static document root; no upload endpoint."""
import os,re,subprocess,sys
name=os.environ['CERTBOT_TOKEN']
value=os.environ.get('CERTBOT_VALIDATION','')
if not re.fullmatch(r'[A-Za-z0-9_-]+',name):
    raise SystemExit('Invalid token')
path='/usr/share/nginx/html/.well-known/acme-challenge/'+name
if len(sys.argv)>1 and sys.argv[1]=='cleanup':
    subprocess.run(['docker','exec','my-gateway','rm','-f',path],check=True)
else:
    subprocess.run(['docker','exec','my-gateway','mkdir','-p','/usr/share/nginx/html/.well-known/acme-challenge'],check=True)
    subprocess.run(['docker','exec','-i','my-gateway','sh','-c','cat > "$1"','sh',path],input=value.encode(),check=True)
