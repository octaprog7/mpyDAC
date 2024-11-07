import sys
from machine import SPI, I2C, Pin

import TLC5615mod
from sensor_pack_2.bus_service import I2cAdapter, SpiAdapter
import mcp4725module
import time

# Raspberry Pi Pico with RP2040 работает от напряжения питания 3.3 В.
# Для датчиков и любого вспомогательного оборудования, работающего на логическом уровне 5.0 В,
# используйте преобразователь уровня 3.3<->5.0 В !!!
# Читай: https://www.raspberrypi-spy.co.uk/2018/09/using-a-level-shifter-with-the-raspberry-pi-gpio/

def show_header(info: str, width: int = 32):
    print(width * "-")
    print(info)
    print(width * "-")

def delay_ms(_val: int):
    time.sleep_ms(_val)

tlc5615 = False

if __name__ == '__main__':
    if tlc5615:
        # default SPI port on "Raspberry Pi Pico with RP2040"
        # если  вас другая плата, то у вас другие выводы порта SPI !!!
        bus = SPI(0, baudrate=1_000_000, polarity=0, phase=0, bits=8, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
        adapter = SpiAdapter(bus)
        # вывод выбор чипа для SPI
        chip_sel = Pin(20, mode=Pin.OUT, value=True)
        dac = TLC5615mod.TLC5615(adapter, chip_sel)
        show_header(f"TLC5615 demo.")
        show_header(f"Напряжение сейчас линейно нарастает от 0 Вольт до 2*V_опорное_ЦАП * 1023/1024")
        rng = dac.get_out_range()
        print(f"DAC out range: {rng}")
        rng = range(100)
        dac.check_write = False
        for value in rng:
            buf = dac.set_output(value + 0.0)
            delay_ms(250)
            percent_completed = 100 * value / (rng.stop - 1)
            print(f"percent completed: {percent_completed}")
            if dac.check_write and not buf is None:
                print(f"read buf: {buf[0]:x}\t{buf[1]:x}")
        show_header(f"TLC5615 finished.")
        sys.exit(0)

    bus = I2C(id=1, scl=Pin(7), sda=Pin(6), freq=400_000)  # on Raspberry Pi Pico
    adapter = I2cAdapter(bus)
    dac = mcp4725module.MCP4725(adapter)
    status = dac.get_status()
    #
    print(status)
    step_delay_ms = 10
    delay_ms(step_delay_ms)
    dac.set_status(out=2048, power_mode=0, save=True)

    show_header("MCP4725 demo. CTRL+C для выхода!")
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
