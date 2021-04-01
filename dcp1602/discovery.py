#import easysnmp
#import zeroconf
import logging
import time
import os, sys
import struct
import usb.core
import usb.util
from usb.core import USBError

from time import sleep
from pprint import pprint
import binascii

logger = logging.getLogger(__name__)

def wrap_request(t, fields):
    if isinstance(fields, list):
        fields = ''.join(['%s=%s\n' % k for k in fields])
    return b'\x1b%s\n%s\x80' % (t, fields.encode())


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
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%H:%M:%S",
            stream=sys.stdout)
        os.environ['PYUSB_DEBUG']='debug'

        #logger.info("Querying MDNS for %s", self.svc_type)
        logger.info("Querying USB for %d devices", len(self.__usb_devices))
        #self._address = None

    # def add_service(self, zc, type_, name):
    #     if self._address:
    #         logger.warning("Got second response, scanner selection is not implemented, so ignoring it.")
    #     logger.error("Got service: %s %s", type_, name)
    #     data = zc.get_service_info(type_, name)
    #     addr = '.'.join([str(i) for i in data.address])
    #     mfg = data.properties.get(b'mfg', '[NO_DATA]')
    #     model = data.properties.get(b'mdl', '[NO_DATA]')
    #     button = data.properties.get(b'button', None) == b'T'
    #     flatbed = data.properties.get(b'flatbed', None) == b'T'
    #     feeder = data.properties.get(b'feeder', None) == b'T'
    #     logger.warning("Scanner found: addr=%s:%d, mfg=%s, model=%s, buttons=%s, feeder=%s, flatbed=%s",
    #                    addr, data.port, mfg, model, button, feeder, flatbed)
    #     self._address = addr
    #     self._model = model
    #     self._port = data.port

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
        # try:
        #     self.dev.reset()
        # except:
        #     pass

        # set the active congfiguration. With no arguments, the first
        # configuration will be the active one
        try:
            for cfg in self.dev:
                for intf in cfg:
                    if self.dev.is_kernel_driver_active(intf.bInterfaceNumber) and intf.bInterfaceClass != 7:
                        self.dev.detach_kernel_driver(intf.bInterfaceNumber)
        except Exception:
            pass

        try:
            self.dev.set_configuration()

        except USBError:
            self.dev.reset()
            self.dev.set_configuration()
            
        # get an endpoint instance
        self.cfg = self.dev.get_active_configuration()

        usb.util.claim_interface(self.dev, intf)
        self.intf = intf

        self.ep_out = usb.util.find_descriptor (
            self.intf,
            # match the first OUT endpoint
            custom_match = \
                    lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_OUT)

        assert self.ep_out is not None

        self.ep_in = usb.util.find_descriptor (
            self.intf,
            # match the first IN endpoint
            custom_match = \
                    lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

        assert self.ep_in is not None

        #tmp=self.dev.ctrl_transfer(0x40, 1, 2, 0)
        # sleep(1)

        # Handshake
        tmp=self.dev.ctrl_transfer(0xc0, 1, 2, 0, 5)
        
        self.ep_out.write(binascii.unhexlify('1b510a80'))
        sleep(.2)
        tmp=self.ep_in.read(self.ep_in.wMaxPacketSize)
            

        # tmp=self.ep_out.write(wrap_request(b'D', 'ADF\n'))
        # sleep(.2)
        # tmp=self.ep_in.read(self.ep_in.wMaxPacketSize)
        # print(binascii.hexlify(tmp))

        params = [
            ('R', '%d,%d' % (300, 300)),
            ('M', 'CGRAY'),
            ('D', 'SIN'),
            ('S', 'NORMAL_SCAN'),
        ]
        tmp=self.ep_out.write(wrap_request(b'I', params))
        sleep(.2)
        tmp=self.ep_in.read(self.ep_in.wMaxPacketSize)
        print(binascii.hexlify(tmp))
        
        params = [
            ('R', '%d,%d' % (300, 300)),
            ('M', 'CGRAY'),
            ('B', 50),
            ('N', 50),
            ('C', 'JPEG'),  # compression format 
            ('J', 'MID'),   # Compression level
            #('C', 'NONE'),
            ('A', '%d,%d,%d,%d' % (0,0,2416,3437)),
            ('S', 'NORMAL_SCAN'),
            ('D', 'SIN'),
            #('P', 0),
            ('E', 0),
            ('G', 0),
        ]
        self.ep_out.write(wrap_request(b'X', params))
        sleep(.2)
        out_buffer = b''
        empty = 0
        while True or empty < 50:
            tmp=self.ep_in.read(65536)
            if len(tmp)>=1:
                pl_type = tmp[0]
                logger.debug("Packet type: %x", pl_type)
                if pl_type == 0xc6:
                    logger.info("Stop error")
                    empty = -1
                    break
                if pl_type == 0x82:
                    logger.info("Stop packet received")
                    empty = 0
                    break

                if (pl_type & 0x40) != 0x40:
                    logger.info("Interrupt")
                    empty = -2
                    break
                    
                hdr = tmp[2:12]
                fields = struct.unpack('hhhhh', hdr)
                pl_len = fields[-1]
                logger.debug("Header: %s, payload len: %d", 
                    binascii.hexlify(hdr), pl_len)
                
                out_buffer+=tmp[12:]
                empty=0
            else:
                empty+=1
            sleep (.2)

        #print(binascii.hexlify(out_buffer))

        # End use
        tmp=self.dev.ctrl_transfer(0xc0, 2, 2, 0, 5)
        usb.util.dispose_resources(self.dev)

        #assert tmp == b'\x80'
        if empty == 0:
            output_file = "scan.jpg"
            with open(output_file, 'wb') as local_file:
                local_file.write(out_buffer)
        else:
            raise Exception("Error while scanning")

def find_scanner():
    f = ScannerFinder()
    return f.query()

find_scanner()
