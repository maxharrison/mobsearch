import asyncio
from elasticsearch_async import AsyncElasticsearch
import elasticsearch.exceptions
import time
import os
import logging
import random


async def init():

    ELASTICSEARCH_HOST = os.environ["ELASTICSEARCH_HOST"]

    global es
    logging.getLogger('elasticsearch').level = logging.ERROR
    es = AsyncElasticsearch([ELASTICSEARCH_HOST])

    connected = False
    while not connected:
        try:
            await es.ping()
            connected = True
            print("connected to elasticsearch")
        except:
            print("cannot connect to elasticsearch at {}, trying again...".format(ELASTICSEARCH_HOST))
            time.sleep(random.randint(10,50)/10)
    time.sleep(random.randint(10,50)/10)

    body = {
        "mappings": {
            "properties": {
                "listingID": {"type": "keyword"},
                "peerID": {"type": "keyword"},
                "description": {"type": "text"},
                "tags": {"type": "text"},
                "categories": {"type": "text"},
                "equivalentBitcoinPrice": {"type": "long"},
                "contractType": {"type": "keyword"},
                "language": {"type": "keyword"},
                "shipsTo": {"type": "keyword"},
                "condition": {"type": "keyword"},
                "acceptedCurrencies": {"type": "keyword"},
                "moderators": {"type": "keyword"},
                "peerData": {
                    "properties": {
                        "peerID": {"type": "keyword"},
                        "name": {"type": "text"},
                        "avatarHashes": {
                            "properties": {
                                "tiny" : {"type": "keyword"}
                            }
                        }
                    }
                },
                "listingData": {
                    "properties": {
                        "hash": {"type": "keyword"},
                        "slug": {"type": "keyword"},
                        "title": {"type": "text"},
                        "thumbnail": {
                            "properties": {
                                "small": {"type": "keyword"}
                            }
                        },
                        "price": {
                            "properties": {
                                "amount": {"type": "long"},
                                "currencyCode": {"type": "keyword"},
                                "modifier": {"type": "float"}
                            }
                        },
                        "coinType": {"type": "keyword"},
                        "nsfw": {"type": "boolean"},
                        "averageRating": {"type": "float"},
                        "ratingCount": {"type": "integer"},
                        "freeShipping": {"type": "keyword"}
                    }
                }
            }
        }
    }

    await es.indices.create(index='listings', body=body, ignore=400)


async def close():
    await es.transport.close()


async def indexListings(peerID: str, listings: list, fullPeerData: dict):

    async def indexListing(peerID: str, listing: dict, fullPeerData: dict):
        listingID = str(listing["hash"])
        body = {
            "listingID": listingID,
            "peerID": peerID,
            "description": str(listing["description"]),
            "tags": list(listing["tags"]),
            "categories": list(listing["categories"]),
            "equivalentBitcoinPrice": 0,
            "contractType": str(listing["contractType"]),
            "language": str(listing["language"]),
            "shipsTo": list(listing["shipsTo"]),
            "condition": str(listing["condition"]),
            "acceptedCurrencies": list(listing["acceptedCurrencies"]),
            "moderators": list(listing["moderators"]),
            "listingData": dict(listing["listingData"]),
            "peerData": {
                "peerID": peerID,
                "name": str(fullPeerData["name"]),
                "avatarHashes": dict(fullPeerData.get("avatarHashes", {}))
            }
        }

        response = await es.index(index="listings", id=listingID, body=body)   
        print("index", response["result"], listingID)

    await asyncio.gather(*[indexListing(peerID, listing, fullPeerData) for listing in listings])
    print("indexed listings:", peerID)


async def updateBitcoinPrice(listingID: str, equivalentBitcoinPrice: int):
    body = {
        "doc": {"equivalentBitcoinPrice": int(equivalentBitcoinPrice)}
    }
    await es.update(index="listings", id=listingID, body=body)#, ignore=400)


async def search(query: str,
                 size: int,
                 start: int,
                 sortBy: str,
                 shipsTo: str,
                 acceptedCurrencies: list,
                 nsfw: bool,
                 contractTypes: list):

    body = {
        "from": start, "size" : size,
        "_source": ["listingData", "peerData", "moderators", "equivalentBitcoinPrice"],
        "query": {
            "bool": {
                "filter": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["listingData.title^5", "tags^2", "description", "peerData.name"]
                        }
                    }
                ]
            }
        },
        "sort": {"_score": {"order": "desc"}}
    }

    if sortBy == "relevance":
        pass
    elif sortBy == "price-asc":
        body["sort"] = {"equivalentBitcoinPrice": {"order": "asc"}}
    elif sortBy == "price-desc":
        body["sort"] = {"equivalentBitcoinPrice": {"order": "desc"}}
    else:
        pass

    if shipsTo == "any":
        pass
    else:
        shipsToOption = {
            "bool": {
                "should": [
                    {"term": {"shipsTo": shipsTo.upper()}},
                    {"term": {"shipsTo": "ANY"}}
                ]
            }
        }
        body["query"]["bool"]["filter"].append(shipsToOption)

    if acceptedCurrencies != []:   
        acceptedCurrenciesOption = {"bool": {"should": []}}
        for acceptedCurrency in acceptedCurrencies:
            acceptedCurrencyOption = {"term": {"acceptedCurrencies": acceptedCurrency.upper()}}
            acceptedCurrenciesOption["bool"]["should"].append(acceptedCurrencyOption)
        body["query"]["bool"]["filter"].append(acceptedCurrenciesOption)

    if not nsfw:
        nsfwOption = {"bool": {"filter": {"term": {"listingData.nsfw": False}}}}
        body["query"]["bool"]["filter"].append(nsfwOption)

    if contractTypes != []:   
        contractTypesOption = {"bool": {"should": []}}
        for contractType in contractTypes:
            contractTypeOption = {"term": {"contractType": contractType.upper()}}
            contractTypesOption["bool"]["should"].append(contractTypeOption)
        body["query"]["bool"]["filter"].append(contractTypesOption)

    response = await es.search(index="listings", body=body)
    return response["hits"]


async def getSearchResults(response: dict,
                           query: str,
                           pageSize: int,
                           pageNumber: int,
                           sortBy: str,
                           shipsTo: str,
                           acceptedCurrencies: list,
                           nsfw: bool,
                           contractTypes: list):
    
    start = pageNumber*pageSize
    elasticResults = await search(query, pageSize, start, sortBy, shipsTo, acceptedCurrencies, nsfw, contractTypes)
    results = {
        "total": elasticResults["total"]["value"],
        "morePages": True if start+pageSize < elasticResults["total"]["value"] else False,
        "results": []
    }
    
    for hit in elasticResults["hits"]:
        result = {
            "type": "listing",
            "data": hit["_source"]["listingData"],
            "relationships": {
                "vendor": {"data": hit["_source"]["peerData"]},
                "moderators": hit["_source"]["moderators"]
            }
        }
        results["results"].append(result)
    response["results"] = results
    return response


async def main():
    try:
        await init()
    finally:
        await close()

if __name__ == "__main__":
    asyncio.run(main())
