import asyncio
import asyncpg
from datetime import datetime
import json
import os
import time
import random


async def init():

    POSTGRESQL_USER = os.environ["POSTGRESQL_USER"]
    POSTGRESQL_PASS = os.environ["POSTGRESQL_PASS"]
    POSTGRESQL_DB = os.environ["POSTGRESQL_DB"]
    POSTGRESQL_HOST = os.environ["POSTGRESQL_HOST"]

    global connectionPool
    connected = False
    while not connected:
        try:
            connectionPool = await asyncpg.create_pool(
                user=POSTGRESQL_USER,
                password=POSTGRESQL_PASS,
                database=POSTGRESQL_DB,
                host=POSTGRESQL_HOST)
            connected = True
            print("connected to postgres")
        except:
            print("unable to connect to postgres, trying again...")
            time.sleep(random.randint(10,50)/10)
    time.sleep(random.randint(10,50)/10)

    sql = """CREATE TABLE IF NOT EXISTS reports(peerID TEXT NOT NULL,
                                                slug TEXT NOT NULL,
                                                reason TEXT NOT NULL,
                                                time TIMESTAMP NOT NULL,
                                                status BOOLEAN,
                                                PRIMARY KEY(peerID, slug, time));"""
    async with connectionPool.acquire() as connection:
        await connection.execute(sql)
    
    sql = """CREATE TABLE IF NOT EXISTS newPeers(peerID TEXT PRIMARY KEY);"""
    async with connectionPool.acquire() as connection:
        await connection.execute(sql)
    
    sql = """CREATE TABLE IF NOT EXISTS peers(peerID TEXT PRIMARY KEY,
                                              lastProfileUpdate TIMESTAMP,
                                              lastListingUpdate TIMESTAMP,
                                              lastOnline TIMESTAMP,
                                              listingCount INT,
                                              profileData JSONB);"""
    async with connectionPool.acquire() as connection:
        await connection.execute(sql)
    
    sql = """CREATE TABLE IF NOT EXISTS listings (listingID TEXT PRIMARY KEY,
                                                  peerID TEXT,
                                                  equivalentBitcoinPrice BIGINT,
                                                  lastPriceUpdate TIMESTAMP,
                                                  currentlyFeatured BOOLEAN,
                                                  basicListing JSONB,
                                                  detailedListing JSONB,
                                                  listingData JSONB);"""
    async with connectionPool.acquire() as connection:
        await connection.execute(sql)


async def insertReport(peerID: str, slug: str, reason: str):
    sql = "INSERT INTO reports (peerID, slug, reason, time) VALUES ($1, $2, $3, $4);"
    async with connectionPool.acquire() as connection:
        await connection.fetch(sql, peerID, slug, reason, datetime.now())


async def inNewDatabase(peerID: str):
    sql = "SELECT peerID FROM newPeers WHERE peerID = $1;"
    async with connectionPool.acquire() as connection:
        result = await connection.fetch(sql, peerID)
    return [peerID, True] if len(result) > 0 else [peerID, False]


async def insertNewPeers(peers: list):

    async def insertNewPeer(peerID: str):
        try:
            sql = "INSERT INTO newPeers (peerID) VALUES ($1);"
            async with connectionPool.acquire() as connection:
                await connection.execute(sql, peerID)
            print("peer inserted:", peerID)
        except asyncpg.exceptions.UniqueViolationError:
            print("peer already inserted:", peerID)
    
    await asyncio.gather(*[insertNewPeer(peerID) for peerID in peers])


async def insertPeer(peerID: str, profileData: dict, update: bool):
    try:
        sql = "INSERT INTO peers (peerID, profileData) VALUES ($1, $2);"
        async with connectionPool.acquire() as connection:
            await connection.execute(sql, peerID, json.dumps(profileData))
        await updateLastProfileUpdate(peerID)
        print("peer inserted:", peerID)
    
    except asyncpg.exceptions.UniqueViolationError:
        if update:
            sql = "UPDATE peers SET profileData = $1 WHERE peerID = $2;"
            async with connectionPool.acquire() as connection:
                await connection.execute(sql, json.dumps(profileData), peerID)
            print("peer updated:", peerID)
    
    await updateLastProfileUpdate(peerID)


async def insertListings(peerID: str, listings: list, update: bool):

    async def insertListing(peerID: str, listing: dict, update: bool):
        listingID = listing["hash"]
        basicListing = listing["basicListing"]
        detailedListing = listing["detailedListing"]
        listingData = listing["listingData"]

        try:
            sql = "INSERT INTO listings (listingID, peerID, basicListing, detailedListing, listingData) VALUES ($1, $2, $3, $4, $5);"
            async with connectionPool.acquire() as connection:
                await connection.execute(sql, listingID, peerID, json.dumps(basicListing), json.dumps(detailedListing), json.dumps(listingData))
            print("listing inserted:", peerID)
        
        except asyncpg.exceptions.UniqueViolationError:
            if update:
                sql = "UPDATE listings SET basicListing = $1, detailedListing = $2, listingData = $3 WHERE listingID = $4;"
                async with connectionPool.acquire() as connection:
                    await connection.execute(sql, json.dumps(basicListing), json.dumps(detailedListing), json.dumps(listingData), listingID)
                print("listings updated:", peerID)
    
    await asyncio.gather(*[insertListing(peerID, listing, update) for listing in listings])
    await updateLastListingUpdate(peerID)
    await updateListingCount(peerID, len(listings))


#async def updateLastOnline(peerID: str):  ### dont think this is used but probably should be
#    sql = "UPDATE peers SET lastOnline = $1 WHERE peerID = $2;"
#    async with connectionPool.acquire() as connection:
#        result = await connection.execute(sql, datetime.now(), peerID)
#    return True if result == "UPDATE 1" else False


async def updateLastProfileUpdate(peerID: str):
    sql = "UPDATE peers SET lastProfileUpdate = $1 WHERE peerID = $2;"
    async with connectionPool.acquire() as connection:
        result = await connection.execute(sql, datetime.now(), peerID)
    return True if result == "UPDATE 1" else False


async def updateLastListingUpdate(peerID: str):
    sql = "UPDATE peers SET lastListingUpdate = $1 WHERE peerID = $2;"
    async with connectionPool.acquire() as connection:
        result = await connection.execute(sql, datetime.now(), peerID)
    return True if result == "UPDATE 1" else False


async def updateListingCount(peerID: str, listingCount: int):
    sql = "UPDATE peers SET listingCount = $1 WHERE peerID = $2;"
    async with connectionPool.acquire() as connection:
        result = await connection.execute(sql, listingCount, peerID)
    return True if result == "UPDATE 1" else False


async def updateBitcoinPrice(listingID: str, equivalentBitcoinPrice: int):
    sql = "UPDATE listings SET equivalentBitcoinPrice = $1, lastPriceUpdate = $2 WHERE listingID = $3;"
    async with connectionPool.acquire() as connection:
        result = await connection.execute(sql, equivalentBitcoinPrice, datetime.now(), listingID)
    return True if result == "UPDATE 1" else False
    

async def getAllPeers():
    sql = ("SELECT peerID FROM peers;")
    async with connectionPool.acquire() as connection:
        peers = await connection.fetch(sql)
    return peers


async def getAllNewPeers():
    sql = ("SELECT peerID FROM newPeers;")
    async with connectionPool.acquire() as connection:
        peers = await connection.fetch(sql)
    return peers


async def countPeers():
    sql = ("SELECT count(*) FROM peers;")
    async with connectionPool.acquire() as connection:
        response = await connection.fetch(sql)
    return response


async def countListings():
    sql = ("SELECT count(*) FROM listings;")
    async with connectionPool.acquire() as connection:
        response = await connection.fetch(sql)
    return response


async def getNewReports():
    sql = ("SELECT * FROM reports;")
    async with connectionPool.acquire() as connection:
        response = await connection.fetch(sql)
    return response


async def main():
    await init()

if __name__ == "__main__":
    asyncio.run(main())
