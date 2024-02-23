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

        # Define pixel commands #
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
        rm = pyvisa.ResourceManager()
        try:
            smu = rm.open_resource('USB0::0x05E6::0x2450::04387860::INSTR')
            tsp_script = f"""
                    -- Define the number of points in the sweep.
                    num = {self.step_count}

                    -- Reset the instrument and clear the buffer.
                    reset()

                    -- Set the source and measure functions.
                    smu.measure.func = smu.FUNC_DC_CURRENT
                    smu.source.func = smu.FUNC_DC_VOLTAGE

                    -- Measurement settings.
                    smu.terminals = smu.TERMINALS_FRONT
                    smu.measure.sense = smu.SENSE_4WIRE
                    smu.measure.autorange = smu.ON
                    smu.measure.nplc = 1

                    -- Source settings.
                    smu.source.highc = smu.OFF
                    smu.source.range = 2
                    smu.source.readback = smu.ON
                    smu.source.ilimit.level = 1
                    smu.source.sweeplinear("SolarCell", {self.start_voltage}, {self.stop_voltage}, num, {self.step_delay})

                    -- Start the trigger model and wait for it to complete.
                    trigger.model.initiate()
                    waitcomplete()

                    -- Define initial values.
                    voltage = defbuffer1.sourcevalues
                    current = defbuffer1
                    isc = current[1]
                    mincurr = current[1]
                    imax = current[1]
                    voc = voltage[1]
                    vmax = voltage[1]
                    pmax = voltage[1] * current[1]

                    -- Calculate values.
                    for i = 1, num do
                        print(voltage[i], current[i], voltage[i] * current[i])
                        if (voltage[i] * current[i] < pmax) then
                            pmax = voltage[i] * current[i]
                            imax = current[i]
                            vmax = voltage[i]
                        end
                        if math.abs(current[i]) < math.abs(mincurr) then
                            voc = voltage[i]
                        end
                    end

                    pmax = math.abs(pmax)
                    imax = math.abs(imax)

                    -- Print calculated maximum power, current, and voltage
                    print("Pmax = ", pmax, ", Imax = ", imax, ", Vmax = ", vmax, ", Isc = ", isc, ", Voc = ", voc)

                    -- Display values on the front panel.
                    display.changescreen(display.SCREEN_USER_SWIPE)
                    display.settext(display.TEXT1, string.format("Pmax = %.4fW", pmax))
                    display.settext(display.TEXT2, string.format("Isc = %.4fA, Voc = %.2fV", isc, voc))
                    """

            # Send the TSP script to the instrument
            smu.write(tsp_script)

            # Read the response (if applicable)
            response = smu.read()
            print(response)

        finally:
            # Close the connection
            smu.close()