import asyncio
import logging

from common.httpApp import make_app, resolve_front_dir
from common.config import getConfig
from common.LNG import G
from service.system import onStart


async def main(server_cfg, front_dir):
    app = make_app(server_cfg, front_dir)
    logger = logging.getLogger()
    app.listen(server_cfg['port'], address='0.0.0.0')
    successMsg = G('running_success').format(url=f"http://0.0.0.0:{server_cfg['port']}/")
    logger.critical(successMsg)
    await asyncio.Event().wait()


if __name__ == "__main__":
    onStart.init()
    cfg = getConfig()
    asyncio.run(main(cfg['server'], resolve_front_dir()))
