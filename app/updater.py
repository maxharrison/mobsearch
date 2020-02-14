import asyncio
import random
import json
import time
import db
import obrequests
import elastic
import importer


async def updatePass():
    peers = [peer[0] for peer in await db.getAllPeers()]
    print("all peers:", len(peers))
    peers = importer.getRandomSample(peers, 50)
    print("random sample:", len(peers))
    await asyncio.gather(*[importer.insertPeerAndListings(peerID) for peerID in peers])


async def update():
    try:
        await db.init()
        await obrequests.init()
        await elastic.init()
        while True:
            time.sleep(random.randint(10, 100))
            await updatePass()
    finally:
        await elastic.close()

if __name__ == "__main__":
    asyncio.run(update())