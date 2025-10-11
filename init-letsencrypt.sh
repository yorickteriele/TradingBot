#!/bin/bash

# Create necessary directories
mkdir -p data/certbot/conf/live/trading.yorickteriele.nl
mkdir -p data/certbot/www

# Create certbot configuration
mkdir -p data/certbot/conf
cat > data/certbot/conf/cli.ini <<EOL
# Use a 4096 bit RSA key instead of 2048
rsa-key-size = 4096

# Register with the specified email address
email = yorick.teriele@outlook.com

# Use the webroot authenticator
authenticator = webroot
webroot-path = /var/www/certbot

# Use the standalone authenticator on port 80
# authenticator = standalone
# standalone-supported-challenges = http-01
# http-01-port = 80

# Agree to the terms of service
agree-tos = True

# Don't share email with the EFF
eff-email = False

# Force renewal of certificates
force-renewal = True
EOL

# Get certificates with certbot
docker run -it --rm \
  -v "$(pwd)/data/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/data/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --config /etc/letsencrypt/cli.ini \
  -d trading.yorickteriele.nl \
  --non-interactive \
  --expand

# Create a script to renew certificates
echo '#!/bin/bash

# Renew certificates
docker run -it --rm \
  -v "$(pwd)/data/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/data/certbot/www:/var/www/certbot" \
  certbot/certbot renew --quiet --deploy-hook "docker-compose exec nginx nginx -s reload"
' > renew-certs.sh

chmod +x renew-certs.sh

echo "SSL certificates have been set up. To renew certificates, run ./renew-certs.sh"
