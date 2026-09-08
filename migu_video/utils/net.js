import os from "os"
import { printRed } from "./colorOut.js";

function getLocalIPv(ver = 4) {
  const ips = []
  const inter = os.networkInterfaces()
  // console.dir(inter, { depth: null })
  for (let net in inter) {

    // console.dir(net, { depth: null })
    // console.log()
    for (let netPort of inter[net]) {
      // netPort = inter[net][netPort]
      // console.dir(netPort, { depth: null })
      if (netPort.family === `IPv${ver}`) {
        // console.dir(netPort, { depth: null })
        ips.push(netPort.address)
      }
    }
  }
  // console.log()
  // console.dir(ips, { depth: null })
  return ips
}

async function fetchUrl(url, opts = {}, timeout = 6000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort()
    printRed("请求超时")
  }, timeout);
  try {
    const res = await fetch(url, {
      ...opts,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return await res.json();
  } catch (err) {
    console.error("请求失败:", err);
    clearTimeout(timeoutId);
    return null;
  }
}

export {
  getLocalIPv, fetchUrl
}
