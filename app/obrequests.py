import asyncio
import aiohttp
import os
import time
import random


async def init():
    
    global OPENBAZAAR_HOST, OPENBAZAAR_USER, OPENBAZAAR_PASS, requestSemaphore
    OPENBAZAAR_HOST = os.environ["OPENBAZAAR_HOST"]
    OPENBAZAAR_USER = os.environ["OPENBAZAAR_USER"]
    OPENBAZAAR_PASS = os.environ["OPENBAZAAR_PASS"]
    requestSemaphore = asyncio.Semaphore(64)

    for _ in range(30):
        try:
            await asyncRequest("/ob/peers")
            break
        except aiohttp.client_exceptions.ClientConnectorError:
            print("cannot connect to OB via {}, trying again...".format(OPENBAZAAR_HOST))
            time.sleep(random.randint(10,50)/10)
    time.sleep(random.randint(10,50)/10)


async def asyncRequest(endpoint: str):
    async with requestSemaphore:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://{}:{}@{}:4002{}".format(OPENBAZAAR_USER, OPENBAZAAR_PASS, OPENBAZAAR_HOST, endpoint), timeout=10) as response:
                    data = await response.json()
            if type(data) == dict and data.get("success") == False:
                return "failure"
            return data     
        except asyncio.TimeoutError:
            return "timeout"
        


async def getBitcoinPrice(currencyCode: str, amount: float):
    if currencyCode == "BTC":
        return amount
    async with requestSemaphore:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://blockchain.info/tobtc?currency={}&value={}".format(currencyCode, amount), timeout=5) as response:
                    data = await response.text()
            try:
                return float(data)
            except ValueError:
                return "no float"
        except asyncio.TimeoutError:
            return "timeout"


def buildListingData(basicListing: dict, detailedListing: dict):
    listingData = dict()
    listingData["hash"] = str(basicListing["hash"])
    listingData["basicListing"] = basicListing
    listingData["detailedListing"] = detailedListing
    listingData["moderators"] = list(detailedListing["moderators"])
    listingData["description"] = str(basicListing["description"])
    listingData["tags"] = list(basicListing.get("tags", []))
    listingData["categories"] = list(basicListing["categories"])
    listingData["contractType"] = str(basicListing["contractType"])
    listingData["language"] = str(basicListing["language"])
    listingData["shipsTo"] = list(basicListing.get("shipsTo", []))
    listingData["condition"] = str(detailedListing["item"]["condition"])
    listingData["acceptedCurrencies"] = list(basicListing.get("acceptedCurrencies", []))
    listingData["listingData"] = dict()
    listingData["listingData"]["hash"] = str(basicListing["hash"])
    listingData["listingData"]["slug"] = str(basicListing["slug"])
    listingData["listingData"]["title"] = str(basicListing["title"])
    listingData["listingData"]["thumbnail"] = dict(basicListing["thumbnail"])
    listingData["listingData"]["language"] = str(basicListing["language"])
    listingData["listingData"]["price"] = dict(basicListing["price"])
    listingData["listingData"]["averageRating"] = float(basicListing["averageRating"])
    listingData["listingData"]["ratingCount"] = int(basicListing["ratingCount"])
    listingData["listingData"]["freeShipping"] = list(basicListing.get("freeShipping", []))
    listingData["listingData"]["coinType"] = str(basicListing.get("coinType", ""))
    listingData["listingData"]["nsfw"] = bool(basicListing["nsfw"])
    return listingData


async def fetchListings(peerID: str):

    async def fetchListing(basicListing: dict, peerID: str):
        endpoint = "/ob/listing/{}/{}".format(peerID, basicListing["hash"])
        detailedListing = await asyncRequest(endpoint)
        if type(detailedListing) == dict:
            listingData = buildListingData(basicListing, detailedListing["listing"])
            return listingData
        return None

    endpoint = "/ob/listings/{}".format(peerID)
    basicListings = await asyncRequest(endpoint)
    if type(basicListings) == list:
        if len(basicListings) > 0:
            if type(basicListings[0]) == dict:
                listings = await asyncio.gather(*[fetchListing(basicListing, peerID) for basicListing in basicListings])
                return [listing for listing in listings if listing != None]
    return None


async def fetchProfile(peerID: str):
    endpoint = "/ob/profile/{}".format(peerID)
    profile = await asyncRequest(endpoint)
    if type(profile) == dict:
        return profile
    return None


async def fetchAPeerList(endpoint: str):
    peers = await asyncRequest(endpoint)
    if type(peers) == list and len(peers) > 0 and type(peers[0]) == str:
        return peers
    else:
        return []


async def fetchConnectedPeers():
    endpoint = "/ob/peers"
    connectedPeers = await fetchAPeerList(endpoint)
    return connectedPeers


async def fetchFollowPeers():
    endpoints = ["/ob/followers", "/ob/following"]
    peers = await asyncio.gather(*[fetchAPeerList(endpoint) for endpoint in endpoints])
    peers = [y for x in peers for y in x]
    peers = list(set(peers))
    return peers

    
async def fetchNewPeers(peerID: str):
    endpoints = ["/ob/closestpeers/{}".format(peerID),
                 "/ob/following/{}".format(peerID),
                 "/ob/followers/{}".format(peerID)]
    newPeers = await asyncio.gather(*[fetchAPeerList(endpoint) for endpoint in endpoints])
    newPeers = [y for x in newPeers for y in x]
    newPeers = list(set(newPeers))
    return newPeers


async def peerOnline(peerID: str):
    endpoint = "/ob/status/{}".format(peerID)
    status = await asyncRequest(endpoint)
    if type(status) == dict:
        if status.get("status") == "online":
            return [peerID, True]
    return [peerID, False]


async def getConfig():
    endpoint = "/ob/config"
    config = await asyncRequest(endpoint)
    if type(config) == dict:
        return config
    else:
        return None


async def main():
    await init()

if __name__ == "__main__":
    asyncio.run(main())

