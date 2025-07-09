from bluepy.btle import Peripheral

MAC = "4C:65:A8:D4:6C:34"

peripheral = Peripheral(MAC)

for service in peripheral.getServices():
    for characteristic in service.getCharacteristics():
        print("Characteristic - id: %s\tname (if exists): %s\tavailable methods: %s" % (str(characteristic.uuid), str(characteristic), characteristic.propertiesToString()))

