import sys
import tkinter as tk
from tkinter import simpledialog
import threading
from pyaxidraw import axidraw
import serial
import os
from measurement_system import MeasurementSystem

class PixelControlSystem:
    def __init__(self):
        # Initialize MeasurementSystem instance
        self.measurement_system = MeasurementSystem('USB0::0x05E6::0x2450::04387860::INSTR')
        self.ad = axidraw.AxiDraw()  # Initialize AxiDraw
        self.ad.interactive()
        if not self.ad.connect():
            sys.exit("Failed to connect to AxiDraw")

        # Set AxiDraw options
        self.ad.options.units = 2
        self.ad.options.speed_pendown = 10
        self.ad.options.speed_penup = 10
        self.ad.update()

        # Define pixel positions#hello
        self.pixel_positions = {
            1: [0, 5],
            2: [0, 10],
            3: [0, 15],
            4: [0, 20],
            5: [5, 20],
            6: [5, 15],
            7: [5, 10],
            8: [5, 5]
        }

        # Initialize serial connection to Arduino
        self.ser = serial.Serial('COM7', 9600)

        # Initialize MeasurementSystem reference
        self.measurement_system = None

        # Create the GUI
        self.root = tk.Tk()
        self.root.title("Pixel Control")
        self.create_gui()

    def create_gui(self):
        button_positions = {
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

        # Adding an Abort button
        abort_button = tk.Button(self.root, text="Abort", command=self.abort_program)
        abort_button.place(x=appropriate_x, y=appropriate_y, width=button_width, height=button_height)

        for name, position in button_positions.items():
            pixel_num = int(name[5:]) if name.startswith("Pixel") else name
            button = tk.Button(self.root, text=name, command=lambda n=pixel_num: self.pixel_button_click(n))
            button.place(x=position[0], y=position[1], width=50, height=50)

    def pixel_button_click(self, pixel_number):
        results = self.get_measurement_inputs()
        if all(result is not None for result in results):
            save_directory, input_power, start_voltage, stop_voltage, steps = results
            threading.Thread(target=self.robot_move_to_pixel, args=(
                pixel_number, save_directory, input_power, start_voltage, stop_voltage, steps)).start()
            #self.robot_move_to_pixel(pixel_number, save_directory, input_power)

    def get_measurement_inputs(self):
        # Prompt the user for the name of the directory to save the measurements
        final_directory_name = simpledialog.askstring("Save Directory",
                                                      "Enter the name of the directory to save the measurements:",
                                                      parent=self.root)

        # If the user cancelled the prompt, return None values
        if not final_directory_name:
            return None, None

        # Define the base directory (update this path as per your requirement)
        base_directory = 'C:\\Users\\jaybr\\Desktop\\'

        # Combine the base directory with the final directory name
        save_directory = os.path.join(base_directory, final_directory_name)
        # Create the directory if it doesn't exist
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        # Prompt user for input power and convert it to float
        input_power = simpledialog.askfloat("Input Power", "Enter the input power (in Watts):", parent=self.root)
        # If the user cancelled the prompt, return None values
        if input_power is None:
            return None, None
         # Prompt user for start voltage, stop voltage, and steps
        start_voltage = simpledialog.askfloat("Start Voltage", "Enter the start voltage:", parent=self.root)
        stop_voltage = simpledialog.askfloat("Stop Voltage", "Enter the stop voltage:", parent=self.root)
        steps = simpledialog.askinteger("Steps", "Enter the number of steps:", parent=self.root)

            if start_voltage is None or stop_voltage is None or steps is None:
                return None, None, None, None, None

            return save_directory, input_power, start_voltage, stop_voltage, steps


    def robot_move_to_pixel(self, pixel_number, save_directory, input_power):
        x_coord, y_coord = self.pixel_positions[pixel_number]

        # Move the AxiDraw to the specified coordinates
        self.ad.moveto(x_coord, y_coord)
        self.ad.delay(2000)  # Delay 2 seconds

        # Send command to Arduino for the selected pixel
        command = self.get_arduino_command(pixel_number)
        self.ser.write(command.encode())

        # Perform measurement at the current pixel position
        if self.measurement_system:
            self.measurement_system.perform_measurement(save_directory, input_power)
        else:
            print("Measurement system not initialized")

        # Return to starting position
        self.ad.moveto(0, 0)

    def get_arduino_command(self, pixel_number):
        # Map each pixel number to a specific Arduino command
        pixel_commands = {
            1: 'r',  # Command for Pixel 1
            2: 'g',  # Command for Pixel 2
            3: 'b',  # Command for Pixel 3
            4: 'f',  # Command for Pixel 4
            5: 'y',  # Command for Pixel 5
            6: 'u',  # Command for Pixel 6
            7: 'i',  # Command for Pixel 7
            8: 'k'  # Command for Pixel 8
            # Add additional mappings as needed
        }

        # Get the command for the given pixel number, default to 'o' if not found
        return pixel_commands.get(pixel_number, 'o')

    def abort_program(self):
        # Optionally, confirm with the user before aborting
        if tk.messagebox.askokcancel("Abort", "Are you sure you want to abort and exit?"):
            # Move the robot to its origin position
            self.move_robot_to_origin()

            # Close all resources
            self.close()

            # Exit the program
            sys.exit("Program aborted by user.")

    def move_robot_to_origin(self):
        # Assuming (0, 0) is the origin position for the robot
        self.ad.moveto(0, 0)
        self.ad.delay(1000)  # Optional delay to allow the robot to reach the origin

    def run(self):
        self.root.mainloop()

    def close(self):
        # Close the serial connection to Arduino
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial connection to Arduino closed.")

        # Disconnect from AxiDraw
        if self.ad:
            self.ad.disconnect()
            print("Disconnected from AxiDraw.")

        # Close the connection to the SMU if it's open
        if self.measurement_system:
            self.measurement_system.close_connections()
            print("Connection to SMU closed.")

if __name__ == "__main__":
    pixel_control_system = PixelControlSystem()
    try:
        pixel_control_system.run()
    finally:
        pixel_control_system.close()
