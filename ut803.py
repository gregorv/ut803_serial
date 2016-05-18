#!/usr/bin/env python3
"""
    A readout library and command line tool for the UNI-T UT803 multimeter
    Copyright (C) 2016 Gregor Vollmer <mail@dynamic-noise.net>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import time
import serial

def chrToInt(c):
    """
    Convert an incoming "hex" character from the UT803 to integer value.
    
    The numerical value corresponds to the ASCII value minus 48 ('0').
    So valid numerical characters are 0123456789:;<=>?
    
    Raises TypeError for any character any other than 0123456789:;<=>?
    """
    num = ord(c) - 48
    if 0 <= num <= 15:
        return num
    raise TypeError("Invalid numeric character")

class UT803:
    measurement_type_table = {
        1: "diode",
        2: "frequency",
        3: "resistance",
        4: "temperature",
        5: "continuity",
        6: "capacitance",
        9: "current",
        11: "voltage",
        13: "current",
        14: "hFE",
        15: "current",
    }
    
    def __init__(self, tty, timeout=2):
        self.conn = serial.Serial(tty,
                       baudrate=19200,
                       bytesize=serial.SEVENBITS,
                       parity=serial.PARITY_ODD,
                       stopbits=serial.STOPBITS_ONE,
                       timeout=timeout,
                       xonxoff=1,
                       rtscts=0,
                       dsrdtr=0
                       )
        # switch on power for hardware RS232
        # transmitter via handshake-signals
        self.conn.dtr = True
        self.conn.rts = False

    def __del__(self):
        self.close()

    def read(self):
        if not self.conn:
            return
        line = self.conn.readline().decode("ascii")
        if not line or len(line) != 11:
            return
        
        measurement = chrToInt(line[5])
        meas_type = UT803.measurement_type_table[measurement]
        flags = [chrToInt(c) for c in line[6:9]]
        
        overload = flags[0] & 0x1
        sign = flags[0] & 0x4
        not_farenheit = flags[0] & 0x8
        
        minimum = flags[1] & 0x2
        maximum = flags[1] & 0x4
        hold = flags[1] & 0x8
        
        autorange = flags[2] & 0x2
        ac = flags[2] & 0x4
        dc = flags[2] & 0x8
        
        unit = UT803.getUnit(measurement, flags)
        
        # different units have different exponent offsets …
        exponent = chrToInt(line[0])
        if unit == "V" and exponent & 0x4:
            exponent -= 2
        exponent += UT803.getExponentOffsetForUnit(unit)
        base_value = int(line[1:5])
        value = float(base_value) * 10**exponent
        if sign:
            value *= -1
        
        flags_dict = {
            "overload": overload > 0,
            "sign": sign > 0,
            "not_farenheit": not_farenheit > 0,
            "min": minimum > 0,
            "max": maximum > 0,
            "hold": hold > 0,
            "autorange": autorange > 0,
            "ac": ac > 0,
            "dc": dc > 0
        }
        return value, unit, meas_type, flags_dict

    @classmethod
    def getUnit(cls, measurement, flags):
        static_units = {
            1: "V",
            2: "Hz",
            3: "Ohm",
            5: "Ohm",
            6: "F",
            9: "A",
            11: "V",
            13: "uA",
            14: "",
            15: "mA",
        }
        if measurement in static_units:
            return static_units[measurement]
        else:
            # handle temperature units
            if measurement == 4:
                return ("°C" if flags[0] & 0x8 else "°F")
            else:
                return "???"

    @classmethod
    def getExponentOffsetForUnit(cls, unit):
        try:
            return {
                "V": -3,
                "Ohm": -1,
                "A": -2,
                "mA": -2,
                "uA": -1,
                "F": -3-9,
            }[unit]
        except KeyError:
            return 0

    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = None


def prettyValueFormat(value, unit=""):
    if value == 0.0:
        return value, unit
    if value < 1e-9:
        return value*1e12, "p"+unit
    if value < 1e-6:
        return value*1e9, "n"+unit
    if value < 1e-3:
        return value*1e6, "u"+unit
    if value < 1:
        return value*1e3, "m"+unit
    if value < 1e3:
        return value, unit
    if value < 1e6:
        return value*1e-3, "k"+unit
    return value*1e-6, "M"+unit

def interactive():
    import argparse
    parser = argparse.ArgumentParser(description="""
Record and monitor data from a UNI-T UT803 table multimeter via serial connection. Either connect the UT803 via the RS-232 port, or USB. In the second case, a virtual RS-232 device is created.
""")
    parser.add_argument("port", help="Serial port for UT803 connection.")
    parser.add_argument("output", help="Specify output file. Use - for stdout.")
    parser.add_argument("-d", "--delay", type=int, help="Delay measurement for specified number of seconds.")
    parser.add_argument("-m", "--monitor", action="store_true", default=False, help="Display a line with the current value and device status.")
    args = parser.parse_args()
    conn = UT803(tty=args.port)
    stdout = args.output == "-"
    if stdout:
        f = sys.stdout
    else:
        f = open(args.output, "w")
    current_measurement = ""
    initial_time = 0.0
    # For some freakin' reason the UT803 sends each measurement twice.
    # Filter that out!
    last_time = 0.0
    try:
        while True:
            r = conn.read()
            if not r:
                continue
            value, unit, measure, flags = r
            t = time.time() - initial_time
            if measure != current_measurement:
                if current_measurement:
                    f.write("\n")
                current_measurement = measure
                f.write("# initial flags: {}\n#time(s)\t{}({})\toverload\n".format(
                    ", ".join(str(k) for k,v in flags.items() if v),
                    measure,
                    unit
                    )
                )
                initial_time = time.time()
                t = 0
                last_time = -10
            if t - last_time < 0.05:
                continue
            last_time = t
            f.write("{:.1f}\t{}\t{}\n".format(t, value, "1" if flags["overload"] else "0"))
            f.flush()
            if args.monitor:
                pval, punit = prettyValueFormat(value, unit)
                sys.stdout.write("\r\033[0K{}: {:.2f} {}, flags: {}".format(
                    measure, pval, punit,
                    " ".join(str(k) for k,v in flags.items() if v)
                    )
                )
            if args.delay:
                time.sleep(args.delay)
    except KeyboardInterrupt:
        pass
    finally:
        if f and not stdout:
            f.close()
        conn.close()

if __name__ == "__main__":
    interactive()
