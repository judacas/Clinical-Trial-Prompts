import random
from colorama import Fore, Style
import tabulate


def score_to_rgb(score, green_threshold=100, yellow_threshold=50, red_threshold=0):
    """
    Converts a score to an RGB color based on customizable thresholds.
    Green at and above green_threshold, yellow at yellow_threshold, and red at and below red_threshold.
    """
    # Clamp the score to the range [red_threshold, green_threshold]
    score = max(red_threshold, min(score, green_threshold))
    
    # Normalize score to a 0-1 scale based on the thresholds
    if score >= yellow_threshold:
        # Green to yellow transition
        normalized_score = (score - yellow_threshold) / (green_threshold - yellow_threshold)
        r = int(255 * (1 - normalized_score))
        g = 255
        b = 0
    else:
        # Yellow to red transition
        normalized_score = (score - red_threshold) / (yellow_threshold - red_threshold)
        r = 255
        g = int(255 * normalized_score)
        b = 0
    
    return r, g, b


def color_text(text:str, score:int, green_threshold=80, yellow_threshold=50, red_threshold=0):
    if score > 100 or score < 0:
        raise ValueError(f"Invalid score: {score}, must be between 0 and 100")
    if score >= green_threshold:
        color_start = Fore.GREEN
    elif score >= yellow_threshold:
        color_start = Fore.YELLOW
    else:
        color_start = Fore.RED
    color_end = Style.RESET_ALL
    return color_start + text + color_end

random_2d_array = [[random.randint(0, 100) for _ in range(5)] for _ in range(10)]

# Apply colorizeText to each element in the 2D array
testArr = [[color_text(f'Value: {value}', value, 100, 90, 85) for value in row] for row in random_2d_array]

print(color_text("Hello", 90, 100, 90, 85))

print(tabulate.tabulate([testArr], tablefmt='fancy_grid',maxcolwidths=50))