import asyncio
import random
import db
import obrequests
import time


async def filterOnlinePeers(peers: list):
    peers = await asyncio.gather(*[obrequests.peerOnline(peerID) for peerID in peers])
    peers = [peerID for peerID, peerOnline in peers if peerOnline]
    return peers


async def filterOutImportedPeers(peers: list):
    peers = await asyncio.gather(*[db.inNewDatabase(peerID) for peerID in peers])
    peers = [peerID for peerID, inDatabase in peers if not inDatabase]
    return peers


async def getNewPeers(peers: list):
    newPeers = await asyncio.gather(*[obrequests.fetchNewPeers(peerID) for peerID in peers])
    newPeers = [y for x in newPeers for y in x]
    newPeers = list(set(newPeers))
    return newPeers


def getRandomSample(population: list, length: int):
    if len(population) > length:
        return random.sample(population, length)
    else:
        return population


async def crawlPass():
    print("getting all peers from the database...")
    seedPeers = [peer[0] for peer in await db.getAllNewPeers()]
    print(len(seedPeers))

    # --- maybe this is not needed --- #
    #print("getting subset of peers which are online...")
    #seedPeers = await filterOnlinePeers(seedPeers)
    #print(len(seedPeers))

    print("getting random subset of peers...")
    seedPeers = getRandomSample(seedPeers, 100)
    print(len(seedPeers))
    
    print("crawling each peer...")
    newPeers = await getNewPeers(seedPeers)
    print(len(newPeers))
    
    print("geting subset of peers which are not in the database...")
    newPeers = await filterOutImportedPeers(newPeers)
    print(len(newPeers))
    
    #print("getting subset of peers which are online...")
    #newPeers = await filterOnlinePeers(newPeers)
    #print(len(newPeers))
    
    print("inserting the peers into the database...")
    await db.insertNewPeers(newPeers)

async def importFollowPeers():
    print("getting followers and following peers...")
    followPeers = await obrequests.fetchFollowPeers()
    print(len(followPeers))

    print("getting subset of peers which are not in the database...")
    followPeers = await filterOutImportedPeers(followPeers)
    print(len(followPeers))

    print("getting subset of peers which are online...")
    followPeers = await filterOnlinePeers(followPeers)
    print(len(followPeers))

    print("inserting the peers into the database...")
    await db.insertNewPeers(followPeers)


async def importConnectedPeers():
    print("getting the connected peers...")
    connectedPeers = await obrequests.fetchConnectedPeers()
    print(len(connectedPeers))

    print("getting subset of peers which are not in the database...")
    connectedPeers = await filterOutImportedPeers(connectedPeers)
    print(len(connectedPeers))

    print("inserting the peers into the database...")
    await db.insertNewPeers(connectedPeers)


async def crawl():
    await obrequests.init()
    await db.init()
    while True:
        time.sleep(random.randint(10, 100))
        await importConnectedPeers()
        await importFollowPeers()
        await crawlPass()


if __name__ == "__main__":
    asyncio.run(crawl())
