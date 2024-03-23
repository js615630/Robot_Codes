'''
This file is to be imported by syp_program_control.py.

Authors: Jason Whitney, Amr Mohamed, Prachya Chowdhury
'''

import os
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import serial

class MeasurementSystem:
    def __init__(self, instrument_address, ser_port='COM7', ser_baud=9600):
        self.instrument_address = instrument_address
        self.ser_port = ser_port
        self.ser_baud = ser_baud
        self.rm = None
        self.smu = None
        self.ser = None
        self.initialize_connections()

    def initialize_connections(self):
        self.rm = pyvisa.ResourceManager()
        self.smu = self.rm.open_resource(self.instrument_address)
        self.ser = serial.Serial(self.ser_port, self.ser_baud)

    def perform_measurement(self, save_directory, input_power, measurement_identifier=None):
        self.configure_instrument()
        voltage, current, power, mpp_voltage, max_power, isc, voc, efficiency = self.fetch_and_process_data(input_power)
        # Use measurement_identifier in plot_and_save method to differentiate between measurements
        self.plot_and_save(voltage, current, power, mpp_voltage, max_power, isc, voc, efficiency, save_directory, measurement_identifier)

    def configure_instrument(self, start_voltage, stop_voltage, steps):
        self.smu.write('*RST')
        self.smu.write('*CLS')
        self.smu.write('SENS:FUNC "CURR"')
        self.smu.write('SENS:CURR:RANG:AUTO ON')
        self.smu.write('SENS:CURRent:RSENse OFF')
        self.smu.write('SOUR:FUNC VOLT')
        self.smu.write('SOUR:VOLT:RANG 2')
        self.smu.write('SOUR:VOLT:ILIM 1')
        self.smu.write(f'SOUR:SWE:VOLT:LIN {start_voltage}, {stop_voltage}, {steps}, 0.1')
        self.smu.write(':INIT')
        self.smu.write('*WAI')

    def fetch_and_process_data(self, input_power):
        data = self.smu.query('TRAC:DATA? 1, 56, "defbuffer1", SOUR, READ')
        data_points = data.strip().split(',')
        voltage = np.array(data_points[0::2], dtype=float)
        current = np.array(data_points[1::2], dtype=float)
        power = voltage * current
        max_power_index = np.argmax(power)
        mpp_voltage = voltage[max_power_index]
        max_power = power[max_power_index]
        zero_voltage_index = np.argmin(np.abs(voltage))
        isc = current[zero_voltage_index]
        #isc = np.max(current)
        voc_index = np.argmin(np.abs(current))
        voc = voltage[voc_index]
        #voc_index = np.where(current >= 0)[0][-1]
        #voc = voltage[voc_index]
        efficiency = (max_power / input_power) * 100 if input_power > 0 else 0
        return voltage, current, power, mpp_voltage, max_power, isc, voc, efficiency

    def plot_and_save(self, voltage, current, power, mpp_voltage, max_power, isc, voc, efficiency, save_directory,
                      measurement_identifier=None):
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # Update to use measurement_identifier, which could be a pixel number or 'baseline'
        suffix = f"_{measurement_identifier}" if measurement_identifier is not None else ""
        iv_plot_filename = os.path.join(save_directory, f'IV_Curve{suffix}.png')
        pv_plot_filename = os.path.join(save_directory, f'PV_Curve{suffix}.png')
        values_filename = os.path.join(save_directory, f'Calculated_Values{suffix}.txt')


        # Plotting I-V Curve
        plt.figure()
        plt.plot(voltage, current, label='I-V Curve')
        plt.xlabel('Voltage (V)')
        plt.ylabel('Current (A)')
        plt.title('I-V Characteristics')
        plt.legend()
        plt.grid(True)
        plt.savefig(iv_plot_filename)  # Use the correct filename with suffix
        plt.close()

        # Plotting P-V Curve
        plt.figure()
        plt.plot(voltage, power, label='P-V Curve')
        plt.scatter(mpp_voltage, max_power, color='red', label='Max Power Point')  # Marking the MPP point
        plt.xlabel('Voltage (V)')
        plt.ylabel('Power (W)')
        plt.title('P-V Characteristics')
        plt.legend()
        plt.grid(True)
        plt.savefig(pv_plot_filename)  # Use the correct filename with suffix
        plt.close()

        # Saving Calculated Values
        with open(values_filename, 'w') as f:  # Use the correct filename with suffix
            f.write(f'Maximum Power (Pmax): {max_power:.4f} W\n')
            f.write(f'Short Circuit Current (Isc): {isc:.4f} A\n')
            f.write(f'Open Circuit Voltage (Voc): {voc:.4f} V\n')
            f.write(f'Efficiency: {efficiency:.2f}%\n')

    def close_connections(self):
        self.ser.close()
        self.smu.close()
