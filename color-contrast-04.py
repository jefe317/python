import colorsys
from math import pow
from typing import Tuple
from datetime import datetime

# Function to calculate relative luminance of a color
def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    def adjust(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)

    r, g, b = rgb
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

# Function to calculate contrast ratio
def contrast_ratio(foreground: Tuple[int, int, int], background: Tuple[int, int, int]) -> float:
    lum1 = relative_luminance(foreground)
    lum2 = relative_luminance(background)
    if lum1 > lum2:
        return (lum1 + 0.05) / (lum2 + 0.05)
    return (lum2 + 0.05) / (lum1 + 0.05)

# Generate HTML table
def generate_html(colors: list):
    html = '<style>* {font-family: sans-serif; text-shadow: none;} .textwhite {color: white;} .textblack {color: black;} .bgwhite.result:hover {text-shadow: 1px 1px 1px #000000;} .bgblack.result:hover {text-shadow: 1px 1px 1px #ffffff;} .label {padding: 0.5em; display: block;} .pass100 {color: #000000; background-color: #9cffac;} .pass80 {color: #000000; background-color: #f2ff9c;} .pass60 {color: #000000; background-color: #ffdb9c} .fail {color: #000000; background-color: #ff9c9c;}</style>'
    html += '<table border="0" style="border-collapse: collapse;">'
    
    # Helper function to determine text color
    def get_text_color(hex_color):
        rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        return "textwhite" if relative_luminance(rgb) < 0.5 else "textblack"

    # Helper function to determine text-shadow color
    def get_text_shadow(hex_color):
        rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        return "bgwhite" if relative_luminance(rgb) >= 0.5 else "bgblack"

    # Top row
    html += '<tr><th style="color: black;">BG &#8594;<br>FG &#8595;</th>'
    for bg in colors:
        text_color = get_text_color(bg[1])
        html += f'<th class="{text_color}" style="background-color: {bg[1]};">{bg[0]}<br>{bg[1]}</th>'
    html += '</tr>'
    
    # Rows for each foreground color
    for fg in colors:
        text_color = get_text_color(fg[1])
        html += f'<tr><td class="{text_color}" style="background-color: {fg[1]};">{fg[0]}<br>{fg[1]}</td>'
        for bg in colors:
            rgb_fg = tuple(int(fg[1].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            rgb_bg = tuple(int(bg[1].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            ratio = round(contrast_ratio(rgb_fg, rgb_bg), 3)
            compliance = (
                "Pass - 100% (AAA >= 7.0)" if ratio >= 7 else
                "Pass - 80% (AA Normal >= 4.5)" if ratio >= 4.5 else
                "Pass - 60% (AA Large >= 3.0)" if ratio >= 3 else
                "Fail - 0% (< 3.0)"
            )
            labelclass = (
                "pass100" if ratio >= 7 else
                "pass80" if ratio >= 4.5 else
                "pass60" if ratio >= 3 else
                "fail"
            )
            text_shadow = get_text_shadow(bg[1])
            html += (
                f'<td style="background-color: {bg[1]}; color: {fg[1]}; padding: 1em;">'
                f'<strong class="result {text_shadow}">{fg[0]} over {bg[0]}</strong>'
                f'<br><span class="label {labelclass}">{compliance} with ratio {ratio}</span>'
                f'</td>'
            )
        html += '</tr>'
    
    html += '</table>'
    return html

# Example color palette with names and hex codes
colors = [
    ("Pure White", "#FFFFFF"),
    ("Pure Black", "#000000"),
    ("Maroon", "#8C2531"),
    ("Black", "#222222"),
    ("Dark Gray", "#404040"),
    ("Medium Gray", "#7F7F7F"),
    ("Light Gray", "#BFBFBF"),
    ("Lightest Gray", "#F6F6F6"),
    ("Tan", "#ADA28C"),
    ("Dark Blue", "#002A3B"),
    ("Dark Green", "#225A41"),
    ("Blue", "#005E84"),
    ("Green", "#7E9A4B"),
    ("Orange", "#B2461F"),
    ("Yellow", "#D88A00"),
    ("Purple", "#3C2D57")
]

html_output = generate_html(colors)

# Generate timestamp for filename
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
filename = f"color_contrast_grid_{timestamp}.html"

# Write to an HTML file
with open(filename, "w") as file:
    file.write(html_output)

print(f"HTML file '{filename}' generated.")
