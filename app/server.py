from fastapi import FastAPI, Query
import json
import os
from starlette.responses import HTMLResponse, UJSONResponse
from typing import List
import elastic
import db
from pydantic import BaseModel
from starlette.requests import Request
from copy import deepcopy


app = FastAPI(__name__)


@app.on_event("startup")
async def startupEvent():

    global responseTemplate
    with open("responseTemplate.json", encoding="utf-8") as file:
        responseTemplate = json.load(file)

    responseTemplate["links"]["listings"] = os.environ["LISTINGS_URL"]
    responseTemplate["links"]["reports"] = os.environ["REPORTS_URL"]
    responseTemplate["logo"] = os.environ["LOGO_URL"]
    responseTemplate["name"] = os.environ["NAME"]

    await elastic.init()
    await db.init()


@app.get("/")
async def search(request: Request,
                 q: str = "*",
                 ps: int = 0,
                 p: int = 0,
                 shipsTo: str = "any",
                 acceptedCurrencies: List[str] = Query([]),
                 nsfw: bool = False,
                 contractTypes: List[str] = Query([]),
                 sortBy: str = "relevance"):
    
    response = await elastic.getSearchResults(deepcopy(responseTemplate), q, ps, p, sortBy, shipsTo, acceptedCurrencies, nsfw, contractTypes)

    for option in response["options"]["shipsTo"]["options"]:
        if option["value"] == shipsTo:
            option["checked"] = True
            break

    for option in response["options"]["acceptedCurrencies"]["options"]:
        if option["value"] in acceptedCurrencies:
            option["checked"] = True

    for option in response["options"]["nsfw"]["options"]:
        if option["value"] == str(nsfw).lower():
            option["checked"] = True
            break
    
    for option in response["options"]["contractTypes"]["options"]:
        if option["value"] in contractTypes:
            option["checked"] = True

    response["sortBy"][sortBy]["selected"] = True
    response["links"]["self"] = str(request.url)
    return response


class Report(BaseModel):
    peerID: str
    slug: str
    reason: str


@app.post("/reports/", status_code=201)
async def reports(report: Report):
    await db.insertReport(report.peerID, report.slug, report.reason)
    return {}