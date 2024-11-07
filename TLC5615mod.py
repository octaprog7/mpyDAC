"""Модуль для управления 10-битным КМОП ЦАП от TI.
Module for controlling 10-bit CMOS DAC from TI.
Analog full scale output (Rload = 100kΩ) 2*V_ref (1023/1024)"""

# micropython
# mail: kolbasilyvasily@yandex.ru
# MIT license

from sensor_pack_2 import bus_service
from sensor_pack_2.base_sensor import DeviceEx, check_value
from sensor_pack_2.dacmod import DAC, check_percent_rng
from sensor_pack_2.dacmod import get_value_percent
from machine import Pin


def _to_bytes_16(value: int) -> tuple[int, int]:
    """Возвращает кортеж (старший байт value, младший байт value). Результат будет верен для 16 битного value!
    Чтобы не дергать менеджер памяти!"""
    return (value & 0b1111_1111_0000_0000) >> 8, (value & 0b1111_1111)


class TLC5615(DeviceEx, DAC):
    """Представление TLC5615"""
    def __init__(self, adapter: bus_service.SpiAdapter, chip_select: Pin):
        """"""
        DeviceEx.__init__(self, adapter=adapter, address=chip_select, big_byte_order=True)
        DAC.__init__(self, resolution=10, unipolar=True)
        self._valid_rng = self.get_out_range()
        # буфер для записи в ЦАП
        self._send_buf = bytearray(2)
        # буфер для чтения при записи в ЦАП
        self._recv_buf = bytearray(2)
        # проверка, путем чтения во время записи в ЦАП
        self._check_write = False

    def __del__(self):
        del self._send_buf

    def _write_out(self, value: int, check_write: bool = False) -> [None, bytes]:
        """Записывает в выходной регистр ЦАП значение.
        Если check_write is True, то одновременно с записью по шине, производится чтение с шины! Буферы для
        чтения и записи должны быть одинаковой длины.
        Необходимо записать 10-битное слово данных с двумя битами ниже бита LSB (sub-LSB) с нулевыми значениями,
        поскольку входная защелка ЦАП имеет ширину 12 бит, поэтому сдвиг влево на два разряда!!!"""
        rng = self._valid_rng
        check_value(value, rng, f"{value} вне допустимого диапазона {rng}!")
        _buf = self._send_buf
        low_byte, high_byte = _to_bytes_16(value << 2)
        # к сожалению _buf[0], _buf[1] = _to_bytes_16(_val) работает неправильно. Почему, я не знаю! Пишите почему!
        _buf[0], _buf[1] = low_byte, high_byte
        if not check_write:
            self.write(_buf)
            return
        # check_write is true
        _recv_b = self._recv_buf
        # из внутреннего сдвигового регистра ЦАП выдвигается предидущее значение, которое хранилось в нем до записи!
        # что вы будете с ним делать, решайте сами!
        self.adapter.write_and_read(self.address, _buf, _recv_b)    # SPI bus! write_and_read only in SpiAdapter
        return _recv_b

    def set_output(self, value: [int, float]) -> [None, bytes]:
        """записывает в выходной регистр ЦАП значение.
        Если значение имеет тип int, то будет записано сырое значение, которое должно быть в диапазоне get_out_range!
        Если значение имеет тип float (0.0 .. 100.0 %) то в выходной регистр будет записано сырое значение,
        соответствующее value в % от get_out_range.stop - 1."""
        _val = value
        if isinstance(value, float):
            check_percent_rng(value)
            rng = self._valid_rng
            _val = int( get_value_percent(percent=value, base=rng.stop - 1) )
        #
        return self._write_out(_val, self.check_write)

    @property
    def check_write(self) -> bool:
        return self._check_write

    @check_write.setter
    def check_write(self, value):
        self._check_write = value
