"""Модуль для управления 12-битным цифро-аналоговым преобразователем с EEPROM памятью"""

# micropython
# mail: goctaprog@gmail.com
# MIT license
# import struct

from sensor_pack_2 import bus_service
from sensor_pack_2.base_sensor import DeviceEx, check_value
from sensor_pack_2.dacmod import DAC
from collections import namedtuple

#   описывает состояние выходного регистра ЦАП
#	out_reg  - значение 0..4095 (12 бит), выходной регистр ЦАП
#	power_mode - режим работы (0 - нормальный режим, 1..3 - режим малого потребления мощности)
mcp4725_data = namedtuple("mcp4725_data", "out_reg power_mode")

#   тип данных, для чтения из ЦАП.
#	data  - это значение типа mcp4725_data
#	eeprom_data  - это значение типа mcp4725_data, хранимое в EEPROM
#	write_status - это значение типа bool, состояние записи EEPROM памяти (EEPROM Write Status)
mcp4725_status = namedtuple("mcp4725_status", 'data eeprom_data write_status')

class MCP4725(DeviceEx, DAC):
    """Представление MCP4725"""
    def __init__(self, adapter: bus_service.BusAdapter, address=0x60):
        # MCP3421 имеет фиксированный адрес 0x68, но АЦП MCP342Х имеют адреса в диапазоне 0x68..0x6F
        check_value(address, range(0x60, 0x68), f"Неверное значение адреса I2C устройства: 0x{address:x}")
        DeviceEx.__init__(self, adapter, address, True)
        DAC.__init__(self, resolution=12, unipolar=True)
        # прием инфы от ЦАП
        self._buf = bytearray(0 for _ in range(5))
        # для 'быстрой' записи в выходной регистр ЦАП
        self._buf_fast_wr = bytearray(0 for _ in range(2))
        # для 'обычной' записи
        self._buf_wr = bytearray(0 for _ in range(3))

    def _check_out(self, value: int) -> int:
        check_value(value, self.get_out_range(), f"Неверное значение регистра: 0x{value:x}")
        return value

    @staticmethod
    def _check_power_mode(value: int) -> int:
        check_value(value, range(4), f"Неверный режим работы устройства: 0x{value:x}")
        return value

    def _read(self) -> bytes:
        """Чтение из устройства на шине"""
        return self.read_to_buf(self._buf)

    def _fast_write(self, value: int, power_mode: int = 0):
        """'Быстрая' запись значения value в регистр ЦАП. Установка power_mode"""
        self._check_out(value)
        MCP4725._check_power_mode(power_mode)
        buf = self._buf_fast_wr
        buf[0] = (power_mode << 4) | (value >> 8)
        buf[1] = value & 0b0000_1111_1111
        self.write(buf)

    def _write(self, value: int, power_mode: int, save: bool = False):
        """Запись значения в выходной регистр ЦАП, если save is False, установка power_mode.
        Запись значения выходного регистра ЦАП и power_mode в EEPROM, если save is True."""
        self._check_out(value)
        MCP4725._check_power_mode(power_mode)
        buf = self._buf_wr
        cx_mask = 0b011 if save else 0b010
        buf[0] = (cx_mask << 5) | (power_mode < 1)
        buf[1] = (value & 0b1111_1111_0000) >> 4
        buf[2] = (value & 0b0000_0000_1111) << 4
        self.write(buf)

    @staticmethod
    def _make_status_from_buf(buf: bytes) -> mcp4725_status:
        """Возвращает информацию о состоянии ЦАП в удобном виде"""
        _write_status = 0 != (buf[0] & 0x80)     # состояние записи EEPROM
        _power_mode = (buf[0] & 0x06) >> 1    # Power Down Selection
        _do = (buf[1] << 4) | (buf[2] >> 4)     # выходной регистр ЦАП
        # байты с индексами 3, 4 хранят значения из EEPROM !!!
        _ed = mcp4725_data(out_reg=buf[4] | ((buf[3] & 0x0F) << 8), power_mode=(buf[3] & 0b0110_0000) >> 5)
        _bd = mcp4725_data(out_reg=_do, power_mode=_power_mode)
        return mcp4725_status(data=_bd, eeprom_data=_ed, write_status=_write_status)

    def get_status(self) -> mcp4725_status:
        """Возвращает текущее состояние ЦАП"""
        buf = self._read()
        return MCP4725._make_status_from_buf(buf)

        # power_mode:
        # 0 - нормальный режим работы. выход АЦП включен.
        # 1 - режим энергосбережения 1. Нога ИМС, V out, отключена от преобразователя и подключена к шине GND через сопротивление 1 КОм.
        # 2 - режим энергосбережения 2. Нога ИМС, V out, отключена от преобразователя и подключена к шине GND через сопротивление 100 КОм.
        # 3 - режим энергосбережения 3. Нога ИМС, V out, отключена от преобразователя и подключена к шине GND через сопротивление 500 КОм.
    def set_status(self, out: [int, float], power_mode: int = 0, save: bool = False):
        """Устанавливает новое состояние выхода ЦАП, режим работы.
        Если save is True, то в EEPROM записываются значения out и power_mode.
        Тип переменной out может быть как int, так и float.
        Если вы выбрали int, то значение должно быть в диапазоне self.get_out_range.
        Если вы выбрали float, то потрудитесь, чтобы значение было в диапазоне 0..100. Это проценты от опорного напряжения ЦАП."""
        MCP4725._check_power_mode(power_mode)
        _raw_out: int = 0
        if isinstance(out, float):
            _raw_out = self.get_raw(out)
        if isinstance(out, int):
            _raw_out = out
        self._check_out(_raw_out)
        if not save:
            self._fast_write(_raw_out, power_mode)
            return
        self._write(value=_raw_out, power_mode=power_mode, save=save)

    def __call__(self, value: [int, float]):
        """для удобства использования"""
        self.set_status(out=value, power_mode=0, save=False)
