import asyncio
import random
import json
import time
import db
import obrequests
import elastic
import updater


def getRandomSample(population: list, length: int):
    if len(population) > length:
        return random.sample(population, length)
    else:
        return population


async def updateBitcoinPrice(listing: dict):
    with open("currencyExponents.json") as file:
        currencyExponents = json.load(file)

    pricingCurrency = str(listing["detailedListing"]["metadata"]["pricingCurrency"])
    price = float(listing["detailedListing"]["item"]["price"])
    listingID = str(listing["hash"])

    if pricingCurrency != "":
        price = price*(10**(-1*int(currencyExponents[pricingCurrency])))
        bitcoinPrice = await obrequests.getBitcoinPrice(pricingCurrency, price)
        if type(bitcoinPrice) == float:
            bitcoinPrice = int(bitcoinPrice*(10**8))
            await elastic.updateBitcoinPrice(listingID, bitcoinPrice)
            await db.updateBitcoinPrice(listingID, bitcoinPrice)



async def insertPeerAndListings(peerID: str):
    profileData = await obrequests.fetchProfile(peerID)
    if type(profileData) == dict:
        listings = await obrequests.fetchListings(peerID)
        if type(listings) == list:
            await elastic.indexListings(peerID, listings, profileData)
            await db.insertListings(peerID, listings, True)
            await db.insertPeer(peerID, profileData, True)
            await asyncio.gather(*[updateBitcoinPrice(listing) for listing in listings])


async def insertPass():
    peers = list(set(await db.getAllNewPeers())-set(await db.getAllPeers()))
    peers = [peer[0] for peer in peers]
    print(len(peers))
    peers = getRandomSample(peers, 150)
    print(len(peers))
    await asyncio.gather(*[insertPeerAndListings(peerID) for peerID in peers])


async def importFromCrawler():
    try:
        await db.init()
        await obrequests.init()
        await elastic.init()
        while True:
            time.sleep(random.randint(10, 100))
            await insertPass()
    finally:
        await elastic.close()

if __name__ == "__main__":
    asyncio.run(importFromCrawler())
