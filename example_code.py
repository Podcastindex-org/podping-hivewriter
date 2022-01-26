from podping_hivewriter.podping_hivewriter import PodpingHivewriter
from podping_hivewriter.podping_settings_manager import PodpingSettingsManager
from podping_hivewriter.models.medium import Medium
from podping_hivewriter.models.reason import Reason
import os
import asyncio


pp = PodpingHivewriter(
    server_account=os.environ["PODPING_HIVE_ACCOUNT"],
    posting_keys=[os.environ["PODPING_HIVE_POSTING_KEY"]],
    settings_manager=PodpingSettingsManager(ignore_updates=True),
    resource_test=False,
)

iris = {"https://3speak.tv/rss/brianoflondon.xml"}

coro = pp.failure_retry(iri_set=iris, medium=Medium.video, reason=Reason.update)

loop = asyncio.get_event_loop()
loop.run_until_complete(coro)
