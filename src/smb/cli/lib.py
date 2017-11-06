import colorama

def get_privileges_text():
    return colorama.Fore.RED + "This tool requires administrative privileges." + colorama.Fore.RESET

def raise_invalid_argument():
    print colorama.Fore.RED + "Invalid Arguments" + colorama.Fore.RESET
    raise

def _init_colorama():
    import os
    from colorama import init
    global output_stream
    if 'TERM' not in os.environ:
        init()

def print_green(text):
    print colorama.Fore.GREEN + text + colorama.Fore.RESET

def print_yellow(text):
    print colorama.Fore.YELLOW + text + colorama.Fore.RESET

def print_red(text):
    print colorama.Fore.RED + text + colorama.Fore.RESET
