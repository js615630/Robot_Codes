'''
This file contains code that will only be able to control the pixel selection, and the SMU measurement.

Authors: Jason Whitney, Amr Mohamed, Prachya Chowdhury
'''

import tkinter as tk
import serial
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import os
import time
import threading

class PixelControlSystem:
    def __init__(self):
        # Define the base directory
        base_directory = 'C:\\Users\\jaybr\\Desktop\\'

        # Get the name of the directory to save the measurements
        final_directory_name = input("Enter the name of the directory to save the measurements: ")
        save_directory = os.path.join(base_directory, final_directory_name)

        # Create the directory if it doesn't exist
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # Assign the save directory
        self.save_directory = save_directory

        # Get the input power value from the user
        self.input_power = float(input("Enter the input power (in Watts): "))
        # Get voltage sweep parameters from user
        self.start_voltage = float(input("Enter the start voltage (in Volts): "))
        self.stop_voltage = float(input("Enter the stop voltage (in Volts): "))
        self.step_count = int(input("Enter the number of steps in the voltage sweep: "))
        self.step_delay = float(input("Enter the step delay (in seconds): "))


        # Initialize serial connection
        self.ser = serial.Serial('COM7', 9600)

        # Define pixel commands
        self.pixel_commands = {
            1: ('o', 'r'),
            2: ('o', 'g'),
            3: ('o', 'b'),
            4: ('o', 'f'),
            5: ('o', 'y'),
            6: ('o', 'u'),
            7: ('o', 'i'),
            8: ('o', 'k')
        }

        # Create the GUI
        self.create_gui()

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("Pixel Control")
        # Define button positions and create them
        buttons = {
            "Pixel1": (60, 67),
            "Pixel2": (60, 134),
            "Pixel3": (60, 201),
            "Pixel4": (60, 268),
            "Pixel5": (240, 67),
            "Pixel6": (240, 134),
            "Pixel7": (240, 201),
            "Pixel8": (240, 268),
            "PREV": (50, 370),
            "NEXT": (200, 370),
            "OFF": (125, 580)
          }

        for name, position in buttons.items():
            pixel_num = int(name[5:]) if name.startswith("Pixel") else name
            button = tk.Button(self.root, text=name, command=lambda n=pixel_num: self.button_click(n))
            button.place(x=position[0], y=position[1], width=50, height=50)

    def button_click(self, pixel_number):
        commands = self.pixel_commands.get(pixel_number, ())
        for cmd in commands:
            self.ser.write(cmd.encode())
        time.sleep(1)
        # Start perform_measurement in a new thread
        measurement_thread = threading.Thread(target=self.perform_measurement)
        measurement_thread.start()

    def perform_measurement(self):
        # Establish communication with the instrument
        rm = pyvisa.ResourceManager()
        smu = rm.open_resource('USB0::0x05E6::0x2450::04387860::INSTR')

        # Measurement code...
        # Reset and configure the instrument
        smu.write('*RST')  # resets SMU before each solar cell measurement
        smu.write('*CLS')  # clears the error queue
        smu.write('SENS:FUNC "CURR"')  # sets the test for current measurement
        smu.write('SENS:CURR:RANG:AUTO ON')
        smu.write('SENS:CURRent:RSENse OFF')  # changes test from default 4-wire to 2-wire
        smu.write('SOUR:FUNC VOLT')  # sets the output function to voltage
        smu.write('SOUR:VOLT:RANG 2')  # sets max allowable output voltage
        smu.write('SOUR:VOLT:ILIM 1')  # Sets current limit to 1 amp
        smu.write(f'SOUR:SWE:VOLT:LIN {self.start_voltage}, {self.stop_voltage}, {self.step_count}, {self.step_delay}')
        smu.write(':INIT')  # initializes SMU with the above parameters
        smu.write('*WAI')  # set SMU to wait for command

        # Fetch the data
        smu.timeout = 20000  # Timeout in milliseconds, adjust as needed

        # Adjust the number of data points to be fetched based on the step count
        data_points_to_fetch = self.step_count * 2  # Two data points (voltage, current) per step

        # Construct the query command with the correct number of data points
        data_query = f'TRAC:DATA? 1, {data_points_to_fetch}, "defbuffer1", SOUR, READ'
        data = smu.query(data_query)
        #data = smu.query('TRAC:DATA? 1, 56, "defbuffer1", SOUR, READ')

        # Process the data
        data_points = data.strip().split(',')
        voltage = np.array(data_points[0::2], dtype=float)
        current = np.array(data_points[1::2], dtype=float)
        power = voltage * current
        max_power_index = np.argmax(power)
        mpp_voltage = voltage[max_power_index]
        max_power = power[max_power_index]

        # Find Isc and Voc
        isc = np.max(current)
        voc_index = np.where(current >= 0)[0][-1]
        voc = voltage[voc_index]

        # Calculate efficiency
        efficiency = (max_power / input_power) * 100 if input_power > 0 else 0

        # Plotting and Saving
        iv_plot_filename = os.path.join(self.save_directory, 'IV_Curve.png')
        pv_plot_filename = os.path.join(self.save_directory, 'PV_Curve.png')
        values_filename = os.path.join(self.save_directory, 'Calculated_Values.txt')

        plt.figure()
        plt.plot(voltage, current, label='I-V Curve')
        plt.xlabel('Voltage (V)')
        plt.ylabel('Current (A)')
        plt.title('I-V Characteristics')
        plt.legend()
        plt.grid(True)
        plt.savefig(iv_plot_filename)
        plt.close()

        plt.figure()
        plt.plot(voltage, power, label='P-V Curve')
        plt.scatter(mpp_voltage, max_power, color='red')  # MPP point
        plt.xlabel('Voltage (V)')
        plt.ylabel('Power (W)')
        plt.title('P-V Characteristics')
        plt.legend()
        plt.grid(True)
        plt.savefig(pv_plot_filename)
        plt.close()

        with open(values_filename, 'w') as f:
            f.write(f'Maximum Power (Pmax): {max_power:.4f} W\n')
            f.write(f'Short Circuit Current (Isc): {isc:.4f} A\n')
            f.write(f'Open Circuit Voltage (Voc): {voc:.4f} V\n')
            f.write(f'Efficiency: {efficiency:.2f}%\n')

        smu.close()

    def run(self):
        self.root.mainloop()  # Start the GUI event loop

    def close(self):
        # Close serial connection
        self.ser.close()

if __name__ == "__main__":
    pixel_control_system = PixelControlSystem()
    try:
        pixel_control_system.run()
    finally:
        pixel_control_system.close()
