# import sys
from machine import I2C, Pin
from sensor_pack_2.bus_service import I2cAdapter
import mcp4725module
import time

#def show(buf: bytes, sep: str = "=", sep_len: int = 16):
#    print(16*sep_len*sep)
#    for b in buf:
#        print(f"0x{b:x}")
#    print(16 * sep_len * sep)

def delay_ms(value: int):
    time.sleep_ms(value)

if __name__ == '__main__':
    i2c = I2C(id=1, scl=Pin(7), sda=Pin(6), freq=400_000)  # on Raspberry Pi Pico
    adapter = I2cAdapter(i2c)

    dac = mcp4725module.MCP4725(adapter)
    status = dac.get_status()
    # show(dac._buf)
    #
    print(status)
    step_delay_ms = 10
    delay_ms(step_delay_ms)
    dac.set_status(out=2048, power_mode=0, save=True)
    # sys.exit(0)
    i = 0
    while True:
        # генератор линейно изменяющегося напряжения от 0 Вольт до Vcc ЦАП.
        # подключите вольтметр между выводами V out и GND платы с ЦАП. Наблюдайте медленно изменяющееся напряжение!
        # выход из программы в IDE - нажатие CTRL+C!
        for val in range(0, 2 ** 12, 5):
            dac(val)
            print(f"круг: {i}; значение: {val}; voltage: {100* val/4096} % от ЦАП Vcc")
            delay_ms(step_delay_ms)
        i += 1
