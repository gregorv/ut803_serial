# ut803_serial
A small utility to read data from the inexpensive table multimeter UNI-T UT803 via the RS232 port.

## Software Options

## The Protocol
Aside from the actual transmission, the real (non-USB) RS232 port of the multimeter requires power supply via DTR and RTS signals from the PC.

Each measurement is sent as a 11 byte packet, forming a fixed length 9 ASCII character line, terminated by CR+LF. The charaters have the following meanings

Byte Position | Interpretation
--------------|---------------
 0            | Exponent
 1-4          | Base Value
 5            | Measurement Type
 6-9          | Flags

The flags and the measurement are encoded in a "super-decimal" format, possibly hex-ish. Anyway, the numericals are `0123456789:;<=>?`. The characters are consecutive in the ASCII table, so the value of the super-decimal characters can be determined by subtracting 48 from their ASCII value.

Char | Numerical Value | ASCII Code
-----|-----------------|-----------
 :   | 10              | 58
 ;   | 11              | 59
 <   | 12              | 60
 =   | 13              | 61
 >   | 14              | 62
 ?   | 15              | 63
 
### Numerical Values
The numerical value of the measurement is encoded with a base value in byte 1-4 and an exponent value in byte 0. It seems like some exponent values have special meanings, so it is not that simple?!

### Measurement Types
A straight forward table. There are some missing entries, maybe the controller support additional modes, but I don't know. The UT803 only sends these.

Code | Measurement Type | Base Unit
-----|------------------|----------
 1   | Diode Test       | V
 2   | Frequency        | Hz
 3   | Resistance       | Ohm
 4   | Temperature      | °F/°C, depending on FLAG_2_3
 5   | Continuity       | ?
 6   | Capacitance      | nF
 9   | Current          | A
 ;   | Voltage          | V
 =   | Current          | µA
 >   | hFE              | 
 ?   | Current          | mA

### Flags
There are three flag characters encoding 4 bits each. The first char encodes interpretation hints of the value. The second char specifies the recording mode. Last but not least, the last char specifies range and AC/DC options.

Byte | Bit | Designation | Interpretation
-----|-----|-------------|---------------
 1   | 1   | FLAG_1_1    | Set on *Overload* condition.
 1   | 2   | FLAG_1_2    | *unused*
 1   | 3   | FLAG_1_3    | Set if value is negative.
 1   | 4   | FLAG_1_4    | Always set except when unit is *°F*.
 2   | 1   | FLAG_2_1    | *unused*
 2   | 2   | FLAG_2_2    | Record minimum value
 2   | 3   | FLAG_2_3    | Record maximum value
 2   | 4   | FLAG_2_4    | Hold value
 3   | 1   | FLAG_3_1    | *unused*
 3   | 2   | FLAG_3_2    | Auto-Range mode
 3   | 3   | FLAG_3_3    | AC TrueRMS measurement
 3   | 4   | FLAG_3_4    | DC measurement
 
 ## License
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
