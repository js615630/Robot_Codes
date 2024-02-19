'''
This file will only demonstrate that the robot can be controlled by a GUI interface with user input.
Instead of performing measurements when the robot arrives at destination, it will report its position.

Authors: Jason Whitney, Amr Mohamed, Prachya Chowdhury
'''

import sys
from pyaxidraw import axidraw

ad = axidraw.AxiDraw()  # Initialize class

ad.interactive()            # Enter interactive mode
connected = ad.connect()    # Open serial port to AxiDraw

if not connected:
    sys.exit()  # End script if not connected

# Set working units to millimeters
ad.options.units = 2

# Set speed to 25% of maximum for both pen-up and pen-down movements
ad.options.speed_pendown = 10
ad.options.speed_penup = 10

ad.update()  # Apply the options commands

pixel_position = [[0, 5], [0, 10], [0, 15], [0, 20], [5, 20], [5, 15], [5, 10], [5, 5]]

def robot_move_to_pixel(pixel_position):
    x_coord, y_coord = pixel_position
    ad.moveto(x_coord, y_coord)
    ad.delay(2000)  # Delay 2 seconds
    #perform_measurement()
    print("Moved to pixel: ", pixel_position)

def user_selection():
    mode = input("Enter '1' for single movement or '2' for full auto: ")
    if mode == '1':
        pixel_number = int(input("Enter the pixel number (1-8): "))
        if 1 <= pixel_number <= 8:
            robot_move_to_pixel(pixel_position[pixel_number - 1])
        else:
            print("Invalid pixel number. Please enter a number between 1 and 8.")
    elif mode == '2':
        for pixel in pixel_position:
            robot_move_to_pixel(pixel)
    else:
        print("Invalid selection. Please enter '1' or '2'.")

user_selection()

ad.moveto(0, 0)  # Return to home position

# Disconnect from AxiDraw
ad.disconnect()
