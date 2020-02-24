# MobSearch
An open source crawler, indexer and search provider stack for OpenBazaar written in Python

This project uses:
 - Python 3 (with asyncio)
 - PostgreSQL
 - Elasticsearch
 - FastAPI
 - Traefik (with Let's Encrypt for https)
 - Docker (with Docker Compose)
 

# Mobis
https://mobis.xyz

I have deployed this code, currently residing at https://search.mobis.xyz/. Just add that URL to the OpenBazaar client to try it out.


# How it works

These are the Docker containers running:
 - traefik (reverse proxy and https certbot)
 - server (a FastAPI based API web server, which takes the OpenBazaar search requests, and returns them with data from Elasticsearch)
 - crawler (uses the Openbazaar API to crawl the network, and adds the new peerIDs to the postgres database
 - importer (takes the peerIDs from the postgres table which the crawler inserts into, and downloads peer and listing data from the Openbazaar API, then indexes them with Elasticsearch)
 - updater (cycles through the database, downloading peer and listing data again for all listings, then updates the index in Elasticsearch)
 - elasticsearch
 - postgresql
 - openbazaar
 
 
# Setup

I tried to make the setup as easy as possible, although there is still some more I can do.

Should be able to follow these steps to set up a basic installation:
 - download the repo using `git clone`
 - edit the `docker-compose.yaml` file and fill in any fields with <> in them
 - create a `acme.json` file in the project directory, and give it the necessary permissions (`chmod 600`)
 - run `docker-compose up`, but once the containers are running - kill them
 - now find where the `obdata` Docker volume is mounted, and edit the config file in there...
 - in the config file: change the gateway to `0.0.0.0`, and in `JSON-api` object, make `"Authenticated": true`, `"Username": "openbazaar"` and `"Password": "<sha256 of the password set in the docker-compose file>"`
 - now run `docker-compose up` again, and 🤞 it should work.
 - (message me if it does not work, I might have missed something out...)


