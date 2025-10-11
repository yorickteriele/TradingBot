#!/bin/bash

# Create necessary directories
mkdir -p data/certbot/conf/live/trading.yorickteriele.nl
mkdir -p data/certbot/www

# Get certificates with certbot
docker run -it --rm \
  -v "$(pwd)/data/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/data/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d trading.yorickteriele.nl \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  --force-renewal

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
