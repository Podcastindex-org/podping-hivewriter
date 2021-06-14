import beem
from beem.account import Account
import json
import asyncio
from timeit import default_timer as timer


async def get_posting_meta(acc_name) -> dict:
    """ Gets the posting_json_metadata from the Hive account
        auth Returns Json object"""
    hive = beem.Hive()
    acc = Account(acc_name, blockchain_instance=hive, lazy=True)
    posting_meta = json.loads(acc["posting_json_metadata"])
    return posting_meta


async def get_podping_settings(acc_name) -> dict:
    """Returns podping settings if they exist"""
    hive = beem.Hive()
    acc = Account(acc_name, blockchain_instance=hive, lazy=True)
    posting_meta = json.loads(acc["posting_json_metadata"])
    podping_settings = posting_meta.get("podping-settings")
    if podping_settings:
        return podping_settings
    else:
        return None


async def run():

    # loop = asyncio.new_event_loop()
    start = timer()
    podping_settings = await get_podping_settings("podping")
    print(timer() - start)
    if podping_settings:
        print(json.dumps(podping_settings, indent=2))
    else:
        print("no settings found")


if __name__ == "__main__":
    asyncio.run(run())
