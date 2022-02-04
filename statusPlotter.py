#!/usr/bin/env python3
# Latency vs time plotting for python-based HDWX
# Created 19 Janurary 2022 by Sam Gardner <stgardner4@tamu.edu>

import requests
from os import path ,listdir
import json
from pathlib import Path
import pandas as pd
from datetime import datetime as dt, timedelta
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec

def set_size(w, h, ax=None):
    if not ax: ax=plt.gca()
    l = ax.figure.subplotpars.left
    r = ax.figure.subplotpars.right
    t = ax.figure.subplotpars.top
    b = ax.figure.subplotpars.bottom
    figw = float(w)/(r-l)
    figh = float(h)/(t-b)
    ax.figure.set_size_inches(figw, figh)

if __name__ == "__main__":
    currentTime = dt.utcnow()
    basePath = path.abspath(path.dirname(__file__))
    dataDir = path.join(basePath, "data")
    Path(dataDir).mkdir(parents=True, exist_ok=True)
    outDir = path.join(basePath, "output")
    Path(outDir).mkdir(parents=True, exist_ok=True)
    numberOfPlots = len(listdir(dataDir))
    if numberOfPlots > 0:    
        fig = plt.figure()
        px = 1/plt.rcParams["figure.dpi"]
        fig.set_size_inches(1920*px, 2*100*numberOfPlots*px)
        gs = GridSpec(numberOfPlots, 1, figure=fig)
        for i in range(numberOfPlots):
            ax = fig.add_subplot(gs[i, 0])
            dataFile = sorted(listdir(dataDir))[i]
            data = pd.read_csv(path.join(dataDir, dataFile))
            data["pydatetimes"] = pd.to_datetime(data["pydatetimes"], format="%Y-%m-%d %H:%M:%S.%f", errors="coerce")
            ax.plot(data["pydatetimes"], 100*data["complete"], "green")
            ax.set_xlim(currentTime - timedelta(days=1), currentTime)
            ax.set_ylim(0, 100)
            productDesc = data["productDescription"].to_list()[-1]
            ax.set_title("productID: "+dataFile.replace(".csv", "")+" productDescription: "+productDesc+" last heartbeat: "+str(data["lastReloadTime"].to_list()[-1]))
            ax.set_position([.05, .975-(i/numberOfPlots), .9, 0.69/numberOfPlots])
        fig.savefig(path.join(outDir, "status.png"))
    allProductData = json.loads(requests.get("http://hdwx.tamu.edu/api/all-products.php").content)
    for productTypeData in allProductData:
        for productData in productTypeData["products"]:
            prodID = productData["productID"]
            prodDesc = productData["productDescription"]
            reloadTimeInt = productData["lastReloadTime"]
            reloadTime = dt.strptime(str(reloadTimeInt), "%Y%m%d%H%M")
            productRuns = ""
            try:
                productRuns = json.loads(requests.get("http://hdwx.tamu.edu/api/get-available-runtimes.php?productID="+str(prodID)).content)
            except Exception as e:
                print("http://hdwx.tamu.edu/api/get-available-runtimes.php?productID="+str(prodID))
                print(e)
                continue
            if type(productRuns) == list and len(productRuns) > 0:
                latestRunInitStr = str(sorted(productRuns)[-1])
                latestRunInit = dt.strptime(latestRunInitStr, "%Y%m%d%H%M")
                timedelay = (currentTime - latestRunInit).total_seconds() / 60
                try:
                    latestRunData = json.loads(requests.get("http://hdwx.tamu.edu/api/get-run.php?productID="+str(prodID)+"&runtime="+latestRunInitStr).content)
                    pctcomp = (latestRunData["availableFrameCount"] / latestRunData["totalFrameCount"])
                except Exception as e:
                    print("http://hdwx.tamu.edu/api/get-run.php?productID="+str(prodID)+"&runtime="+latestRunInitStr)
                    print(e)
                    continue
            else:
                continue
            newRow = pd.DataFrame([[currentTime, prodDesc, reloadTimeInt, timedelay, pctcomp]], columns=["pydatetimes", "productDescription", "lastReloadTime", "timeDelay", "complete"])
            productcsvPath = path.join(dataDir, str(prodID)+".csv")
            productReloadTimes = pd.DataFrame()
            if path.exists(productcsvPath):
                productReloadTimes = pd.read_csv(productcsvPath)
                productReloadTimes = productReloadTimes.append(newRow, ignore_index=True)
            else:
                productReloadTimes = newRow.copy()
            productReloadTimes["pydatetimes"] = pd.to_datetime(productReloadTimes["pydatetimes"], format="%Y-%m-%d %H:%M:%S.%f", errors="coerce")
            productReloadTimes = productReloadTimes[productReloadTimes["pydatetimes"] > currentTime - timedelta(days=1)]
            productReloadTimes.to_csv(productcsvPath, index=False)
            
            