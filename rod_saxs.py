#!/usr/bin/env python3

# import time
import sys
import subprocess 
import pickle
import colorsys
from datetime import datetime
import numpy as np
from scipy import special as sp
import matplotlib.colors as colors
import matplotlib.cm as cm
from PIL import Image, ImageDraw, ImageFont
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from gpiozero import Button

 
BTN1_PIN = 19
BTN2_PIN = 25

bright_list = [10, 20, 30, 40, 50, 60, 80,] # Choosing not to include 100% to limit current draw
# bright_ndx = 0
cmap_list = ['jet', 'turbo', 'gnuplot','gnuplot2', 'hot', 'viridis','plasma','inferno','cividis','gist_earth','gist_gray']
# cmap_ndx = 0
font_color_dict = [{'red': 250, 'green': 0, 'blue': 0},
    {'red': 250, 'green': 0, 'blue': 0},
    {'red': 0, 'green': 250, 'blue': 0},
    {'red': 0, 'green': 250, 'blue': 0},
    {'red': 0, 'green': 200, 'blue': 250},
    {'red': 250, 'green': 150, 'blue': 0},
    {'red': 150, 'green': 250, 'blue': 0},
    {'red': 100, 'green': 250, 'blue': 0},
    {'red': 250, 'green': 0, 'blue': 0},
    {'red': 250, 'green': 0, 'blue': 0},
    {'red': 250, 'green': 0, 'blue': 250},]
# clock_disp_ndx = 1
clock_disp_max = 8

stored_time = datetime.now().strftime("%H:%M:%S").split(':')
set_time_digit = 0 #0 not setting time, 1 setting hour, 2 setting 10 min, 3 setting 1 min


def main():
    load_ndx() # load previously saved configuration

    # Setting up buttons
    Button.was_held = False

    btn1 = Button(BTN1_PIN, hold_time=1)
    btn1.when_released = btn_released
    btn1.when_held = btn_held

    btn2 = Button(BTN2_PIN, hold_time=1)
    btn2.when_released = btn_released
    btn2.when_held = btn_held

    # Setting up RGB Matrix
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat-pwm'  # If you have an Adafruit HAT: 'adafruit-hat'
    options.show_refresh_rate = 0 #turn on to debug performance optimization
    options.gpio_slowdown = 1 #def 1
    options.scan_mode = 1
    options.pwm_lsb_nanoseconds = 100 #def 130, lower better performance, less quality
    options.pwm_bits = 11 # def 11, 1 to 11, lower less color depth but more performance
    options.pwm_dither_bits = 0 #def 0, 1 increases performances
    options.limit_refresh_rate_hz = 0 #def 0= no limit
    options.drop_privileges = 0
    # options.disable_hardware_pulsing = False
    
    matrix = RGBMatrix(options=options)
    matrix.brightness = bright_list[bright_ndx]

    # Setting up font positions
    # font = graphics.Font()
    # font.LoadFont("clR6x12.bdf")
    # font_color = graphics.Color(**font_color_dict[cmap_ndx])
    font_x = [0, 0, 0, 0, 0, 33, 33, 33, 33]
    font_y = [63, 63, 63, 9, 9, 9, 9, 63, 63]
    box_size = (31, 10)
    box_pos = [(0, 53), (0, 54), (0, 54), (0, 0), (0, 0), (33, 0), (33, 0), (33, 54), (33, 54)]
    box_im = Image.new("RGB", box_size, (0,0,0))
    
    # Setting up saxs geometry
    lamb = 0.93 # 13.3 keV in wavelength (Angstroms)
    k = 2.0*np.pi/lamb
    alpha_i = 0*np.pi/180.0 # incident angle, set to zero
    L = 1.1e10 # sample to detector distance in Angstroms

    numpix_y = 64
    numpix_z = 64
    pix_y0 = numpix_y/2 + 0.5
    pix_z0 = numpix_z/2 + 0.5

    pix_y_size = 3000*1e4 # pixel size in angstroms
    pix_z_size = 3000*1e4

    pix_y = np.arange(1.0, numpix_y+1.0) - pix_y0
    pix_z = np.arange(1.0, numpix_z+1.0) - pix_z0

    y = pix_y*pix_y_size
    z = pix_z*pix_z_size

    PixY, PixZ = np.meshgrid(pix_y, pix_z)
    Y, Z = np.meshgrid(y, z)

    twotheta = np.arctan(Y/L)
    alpha_f = np.arctan(Z/L*np.cos(twotheta))

    qx = k*(np.cos(alpha_f)*np.cos(twotheta) - np.cos(alpha_i))
    qy = k*(np.cos(alpha_f)*np.sin(twotheta))
    qz = k*(np.sin(alpha_f) + np.sin(alpha_i))

    q = np.sqrt(qx**2 + qy**2 + qz**2)
    qr = np.sqrt(qx**2 + qy**2)
    chi = np.arccos(qz/q)

    # Calculate angle between hour hand rod and q vector for each pixel
    qvec = np.zeros((numpix_y,numpix_z,3))
    qvec[:,:,0] = qx
    qvec[:,:,1] = qy
    qvec[:,:,2] = qz
    
    Lr = 300
    Rr = 20

    current_angle = 0.0

    # Main loop
    try:
        while True:
            matrix.brightness = bright_list[bright_ndx]
            # start = time.time()
            current_angle = get_time_angle()
            # current_angle += 1 * np.pi / 180.0 # rotating pattern for debugging
            # current_angle = 0*np.pi/4 # constant pattern for debugging

            rodvec = np.zeros((numpix_y,numpix_z,3)) # x component always zero because aligned in plane parallel to detector plane
            rodvec[:,:,1] = np.sin(current_angle) # y component
            rodvec[:,:,2] = np.cos(current_angle) # z component

            q_rod_angle = np.zeros((numpix_y,numpix_z)) # initialize, angle between cylinder/rod and qvec
            dot_v1_v2 = np.einsum('ijk,ijk->ij', qvec, rodvec)
            dot_v1_v1 = np.einsum('ijk,ijk->ij', qvec, qvec)
            dot_v2_v2 = np.einsum('ijk,ijk->ij', rodvec, rodvec)
            
            q_rod_angle = np.arccos(dot_v1_v2/(np.sqrt(dot_v1_v1)*np.sqrt(dot_v2_v2)))

            # Calculate the oriented cylinder form factor at each pixel
            P = (2*np.sin(0.5*q*Lr*np.cos(q_rod_angle))/(0.5*q*Lr*np.cos(q_rod_angle))*sp.jv(1.0, q*Rr*np.sin(q_rod_angle))/(q*Rr*np.sin(q_rod_angle)))**2

            # Convert to color mapped image
            cmap = cm.ScalarMappable(norm=colors.LogNorm(vmin=1e-6, vmax=1), cmap=cmap_list[cmap_ndx])
            P_RGB = cmap.to_rgba(P)
            im = Image.fromarray(np.uint8(P_RGB*255))
            im = im.transpose(Image.FLIP_TOP_BOTTOM).convert('RGB')

            # draw a text box for clarity for display settings 3, 5, 7, 9
            if clock_disp_ndx != 0 and clock_disp_ndx % 2 == 0:
                im.paste(box_im, box_pos[clock_disp_ndx])

            # Draw to LED matrix without text
            # matrix.SetImage(im)

            # get current time font color
            font_color = graphics.Color(**font_color_dict[cmap_ndx])
            
            # Display time text
            if clock_disp_ndx > 0:
                draw = ImageDraw.Draw(im)
                pilfont = ImageFont.load('clR6x12.pil')

                time_str = datetime.now().strftime('%H:%M').split(':')
                hour_str = time_str[0]
                min_str = time_str[1]
                if int(hour_str) > 12:
                    hour_str = str(int(hour_str) - 12)
                if int(hour_str) < 10:
                    hour_str = ' ' + str(int(hour_str))
                if int(hour_str) == 0:
                    hour_str = '12'

                draw.text((font_x[clock_disp_ndx], font_y[clock_disp_ndx]-9), hour_str + ':' + min_str, fill=tuple(font_color_dict[cmap_ndx].values()), font=pilfont)
                # graphics.DrawText(matrix, font, font_x[clock_disp_ndx], font_y[clock_disp_ndx], font_color, hour_str + ':' + min_str)
                # previously used graphics to draw text on top of matrix.SetImage, but resulted in flicker
                # now using pil to draw font onto the image first before drawing with matrix.SetImage

            # Draw to LED matrix with text already in image
            matrix.SetImage(im)
            
            # Underline the digits if time is being set
            if set_time_digit == 1:
                graphics.DrawLine(matrix, font_x[clock_disp_ndx]+2, font_y[clock_disp_ndx], font_x[clock_disp_ndx]+10, font_y[clock_disp_ndx], get_opposite_color(**font_color_dict[cmap_ndx]))
            elif set_time_digit == 2:
                graphics.DrawLine(matrix, font_x[clock_disp_ndx]+18, font_y[clock_disp_ndx], font_x[clock_disp_ndx]+22, font_y[clock_disp_ndx], get_opposite_color(**font_color_dict[cmap_ndx]))
            elif set_time_digit == 3:
                graphics.DrawLine(matrix, font_x[clock_disp_ndx]+24, font_y[clock_disp_ndx], font_x[clock_disp_ndx]+28, font_y[clock_disp_ndx], get_opposite_color(**font_color_dict[cmap_ndx]))
            
            # print(time.time()-start)
    except KeyboardInterrupt:
        sys.exit()

def get_time_angle() -> float:
    time = datetime.now().strftime("%H:%M:%S")
    time = time.split(':')
    hour = int(time[0])
    minute = int(time[1])
    sec = int(time[2])

    sec_per_day = 86400.0
    sec_per_rot = sec_per_day / 2.0 # 12 hr clock rotates twice per day
    angle_per_sec = 2.0 * np.pi / sec_per_rot

    if hour >= 12:
        hour = hour - 12

    # print([hour, minute, sec])

    current_sec = hour*60*60 + minute*60 + sec
    # print(current_sec)

    current_angle = angle_per_sec * current_sec
    # print(current_angle)

    return current_angle

def btn_pressed(btn): # Generic handler
    if btn.pin.number == BTN1_PIN:
        btn1_pressed()
    elif btn.pin.number == BTN2_PIN:
        btn2_pressed()

def btn_held(btn): # Generic handler
    btn.was_held = True
    if btn.pin.number == BTN1_PIN:
        btn1_held()
    elif btn.pin.number == BTN2_PIN:
        btn2_held()
	
def btn_released(btn): # Generic handler
    if not btn.was_held:
        btn_pressed(btn)
    btn.was_held = False

def btn1_pressed(): # Change clock display position
    global set_time_digit
    if set_time_digit == 0:
        global clock_disp_ndx
        if clock_disp_ndx < clock_disp_max:
            clock_disp_ndx += 1
        else:
            clock_disp_ndx = 0
        save_ndx()
    elif set_time_digit == 3:
        set_time_digit = 0
        subprocess.run(['hwclock','-w'])
        load_ndx()
    else:
        set_time_digit += 1

def btn1_held(): # Set time
    global set_time_digit
    #Change display mode to display box for clarity
    global clock_disp_ndx
    if set_time_digit == 0:
        if clock_disp_ndx == 0:
            clock_disp_ndx = 2
        elif clock_disp_ndx % 2 == 1:
            clock_disp_ndx += 1
        store_current_time()
        set_time_digit = 1
    
def btn2_pressed(): # Change brightness
    global set_time_digit
    if set_time_digit == 0:
        global bright_ndx
        if bright_ndx < len(bright_list)-1:
            bright_ndx += 1
        else:
            bright_ndx = 0
        save_ndx()
    elif set_time_digit == 1:
        add_1_hour()
    elif set_time_digit == 2:
        add_10_min()
    elif set_time_digit == 3:
        add_1_min()

def btn2_held(): # Change color map
    global cmap_ndx
    if cmap_ndx < len(cmap_list)-1:
        cmap_ndx += 1
    else:
        cmap_ndx = 0
    save_ndx()

def add_1_hour():
    global stored_time
    hour = int(stored_time[0])
    if hour == 23:
        hour = 0
    else:
        hour += 1
    stored_time[0] = str(hour)
    write_stored_time()

def add_10_min():
    global stored_time
    min = int(stored_time[1])
    if min >= 50:
        min = min % 10
    else:
        min += 10
    stored_time[1] = str(min)
    write_stored_time()

def add_1_min():
    global stored_time
    min = int(stored_time[1])
    if min % 10 == 9:
        min = min // 10 * 10
    else:
        min += 1
    stored_time[1] = str(min)
    write_stored_time()

def store_current_time():
    global stored_time
    stored_time = datetime.now().strftime("%H:%M:%S").split(':')

def write_stored_time():
    subprocess.run(['date', '+%T', '-s', stored_time[0] + ':' + stored_time[1] + ':' + stored_time[2]])
    # subprocess.run(['hwclock','-w']) #this is now only done when completing time setting with last btn1 press

def save_ndx():
    dict_to_save = {'bright_ndx': bright_ndx, 'cmap_ndx': cmap_ndx, 'clock_disp_ndx': clock_disp_ndx}
    with open('clock_config.txt','wb') as file:
        pickle.dump(dict_to_save, file)

def load_ndx():  
    with open('clock_config.txt', 'rb') as file:
        saved_dict = pickle.load(file)
        global bright_ndx
        bright_ndx = saved_dict['bright_ndx']
        global cmap_ndx
        cmap_ndx = saved_dict['cmap_ndx']
        global clock_disp_ndx
        clock_disp_ndx = saved_dict['clock_disp_ndx']   
    
def get_opposite_color(red, green, blue):
    hsv = colorsys.rgb_to_hsv(red/255, green/255, blue/255)
    hsv = list(hsv)
    hsv[0] += 0.5
    if hsv[0] > 1:
        hsv[0] -= 1
    rgb = colorsys.hsv_to_rgb(hsv[0], hsv[1], hsv[2])
    return graphics.Color(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

if __name__ == "__main__":
    main()
