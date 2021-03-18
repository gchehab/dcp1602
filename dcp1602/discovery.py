#import easysnmp
#import zeroconf
import logging
import time

import usb.core
import usb.util

from pprint import pprint
import binascii

logger = logging.getLogger(__name__)


class ScannerFinder:
    #svc_type = "_scanner._tcp.local."
    dev = None

    __usb_devices = [
        {
            'name': 'Brother DCP-1602',
            'idVendor': 0x04f9,
            'idProduct': 0x0376
        }
    ]


    def __init__(self):
        pass
        #logger.info("Querying MDNS for %s", self.svc_type)
        logger.info("Querying USB for %d devices", len(self.__usb_devices))
        #self._address = None

    def add_service(self, zc, type_, name):
        if self._address:
            logger.warning("Got second response, scanner selection is not implemented, so ignoring it.")
        logger.error("Got service: %s %s", type_, name)
        data = zc.get_service_info(type_, name)
        addr = '.'.join([str(i) for i in data.address])
        mfg = data.properties.get(b'mfg', '[NO_DATA]')
        model = data.properties.get(b'mdl', '[NO_DATA]')
        button = data.properties.get(b'button', None) == b'T'
        flatbed = data.properties.get(b'flatbed', None) == b'T'
        feeder = data.properties.get(b'feeder', None) == b'T'
        logger.warning("Scanner found: addr=%s:%d, mfg=%s, model=%s, buttons=%s, feeder=%s, flatbed=%s",
                       addr, data.port, mfg, model, button, feeder, flatbed)
        self._address = addr
        self._model = model
        self._port = data.port

    def query(self):
        #self.zc = zeroconf.Zeroconf()
        #self.br = zeroconf.ServiceBrowser(self.zc, self.svc_type, self)
        #for i in range(50):
        #    if self._address:
        #        self.br.cancel()
        #        return self._address, self._model
        #    time.sleep(0.1)

        for device in self.__usb_devices:
            self.dev = usb.core.find(
                    idVendor=device['idVendor'], idProduct=device['idProduct'])
            if self.dev is None:
                raise ValueError('No scanner found')
            else:
                break

        # set the active congfiguration. With no arguments, the first
        # configuration will be the active one
        try:
            if self.dev.is_kernel_driver_active(0):
                reattach = True
                self.dev.detach_kernel_driver(0)
        except Exception:
            pass

        self.dev.set_configuration()

        # get an endpoint instance
        self.cfg = self.dev.get_active_configuration()
        self.intf = self.cfg[(0,0)]

        self.ep = usb.util.find_descriptor (
            self.intf,
            # match the first OUT endpoint
            custom_match = \
                    lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

        assert self.ep is not None

        self.ep.write(b'D=ADF\n')
        print(binascii.hexlify(self.ep.read(1024)))

        self.ep.write(b'D=FB\n')
        print(binascii.hexlify(self.ep.read(1024)))
        
def find_scanner():
    f = ScannerFinder()
    return f.query()

find_scanner()
