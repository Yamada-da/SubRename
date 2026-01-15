# -*- coding: utf-8 -*-
import os
import re
import shutil
import sys

# --- ANSI Color Codes ---
COLOR_RED = '\033[91m'
COLOR_GREEN = '\033[92m'
COLOR_RESET = '\033[0m'

# ==============================================================================
# ============================ USER CONFIGURATION ==============================
# ==============================================================================
# Instructions:
# - To preset a value, change 'None' to the desired value.
# - If a value is 'None' or invalid, the script will ask you interactively.
#
CONFIG = {
    # Preset language selection. (automatically identify the language code of the subtitle file name according to the preset below)
    # IMPORTANT: This must be a list of strings. (including [""], see example below for details)
    # Example: ["en", "eng", "enjp", "en-US", "en-GB", "jpen"] to auto-select English.
    # Example: ["all"] to auto-select all found languages.
    # Set to None to be asked every time.
    "PRESET_LANGUAGE": None,

    # Preset whether to add a language suffix (like '.en') to filenames.
    # 1 = No, 2 = Yes, None = Ask
    "PRESET_ADD_SUFFIX": None,

    # Preset the save location for new files.
    # 1 = New 'sub' subfolder, 2 = Same folder as originals, None = Ask
    "PRESET_SAVE_LOCATION": None,

    # Preset whether to delete the original files after processing.
    # 1 = No, 2 = Yes, None = Ask
    "PRESET_DELETE_ORIGINALS": None,
    
    # Preset whether to archive unprocessed subtitle files into separate folders.
    # 1 = Yes, 2 = No, None = Ask
    "PRESET_ARCHIVE_UNPROCESSED": None,

    # Preset how to handle unprocessed font archives (e.g., Fonts.zip).
    # 1 = Archive to a 'Fonts' folder, 2 = Ignore (do nothing), None = Ask
    "PRESET_HANDLE_FONTS": None,

    # Force SP Mode for series. If set to 1, the script will automatically
    # enter SP mode for any detected series, skipping the format prompt.
    # 1 = Yes (Force SP Mode), None = Normal behavior
    "FORCE_SP_MODE": None,
}
# ==============================================================================
# ========================== END OF USER CONFIGURATION =========================
# ==============================================================================


def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def natural_sort_key(s):
    """
    Key for natural sorting. Handles strings, integers, and floats correctly
    by separating them into typed tuples.
    """
    key = []
    # This regex finds all sequences of digits (with optional decimal part)
    # or sequences of non-digits.
    parts = re.findall(r'(\d+\.\d+|\d+|\D+)', s)
    for part in parts:
        try:
            # Mark numbers with a 0 prefix for correct type comparison
            key.append((0, float(part)))
        except ValueError:
            # Mark strings with a 1 prefix
            key.append((1, part.lower()))
    return key

def _convert_chinese_num_to_str(cn_num_str):
    """Helper to convert Chinese numerals up to 99 to a string digit."""
    cn_map = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    
    if len(cn_num_str) == 1:
        if cn_num_str == '十': return '10'
        return str(cn_map.get(cn_num_str, ''))

    num = 0
    if cn_num_str.startswith('十'):
        num = 10 + cn_map.get(cn_num_str[1], 0)
    elif cn_num_str.endswith('十'):
        num = cn_map.get(cn_num_str[0], 0) * 10
    elif '十' in cn_num_str:
        parts = cn_num_str.split('十')
        num = cn_map.get(parts[0], 0) * 10 + cn_map.get(parts[1], 0)
    
    return str(num) if num > 0 else None

def extract_episode_identifier(filename):
    """
    Extracts a normalized episode identifier from a filename, handling specials and decimals.
    """
    # Chinese Word to Number first
    cn_pattern = r'第([一二三四五六七八九十百]+)(?:集|話|话)'
    cn_match = re.search(cn_pattern, filename)
    if cn_match:
        cn_num_str = cn_match.group(1)
        arabic_num_str = _convert_chinese_num_to_str(cn_num_str)
        if arabic_num_str:
            return arabic_num_str
            
    # Patterns for specials (e.g., OVA 01, SP 02, or just OVA)
    special_patterns = [
        r'(?i)(OVA|SP|OAD|NCOP|NCED|DVDSpot)\s*(\d{1,3}(?:\.\d)?)', # For OVA 01, SP 02 etc.
        r'\[(SP\d+|OAD\d+|OVA\d+|NCOP\d+|NCED\d+|DVDSpot\d+)\]', # For [SP01], [OVA02] etc.
        r'(?i)\b(OVA|SP|OAD|NCOP|NCED|DVDSpot)\b(?!\s*\d)' # For standalone OVA, SP etc. not followed by a number
    ]
    
    for pattern in special_patterns:
        match = re.search(pattern, filename)
        if match:
            # For specials, combine the prefix and number to create a unique ID (e.g., "OVA01")
            groups = [g for g in match.groups() if g is not None]
            # Normalize to remove spaces and ensure consistency
            return "".join(groups).upper()

    # Patterns for regular episodes, now supporting decimals and international formats
    regular_patterns = [
        r'(?i)S\d{1,2}E(\d{1,3}(?:\.\d)?)',       # For S01E01, S01E10.5 etc.
        r'第(\d{1,3}(?:\.\d)?)(?:集|話|话)',      # For 第1集, 第1話, 第1话
        r'(\d{1,3}(?:\.\d)?)\s*화',              # For 1화 (Korean)
        r'(?i)(?:Episodio|Episódio|Episod)\s*(\d{1,3}(?:\.\d)?)', # Italian, Spanish, Portuguese, Malay
        r'(?i)(?:ตอน(?:ที่)?)\s*(\d{1,3}(?:\.\d)?)', # Thai
        r'(?i)(?:Эпизод|Серия)\s*(\d{1,3}(?:\.\d)?)', # For Эпизод 1, Серия 1 (Russian)
        r'(?i)Épisode\s*(\d{1,3}(?:\.\d)?)',     # For Épisode 1 (French)
        r'\[(\d{1,3}(?:\.\d)?(?:v\d)?)\]',        # For [01] or "[01v2]" or "[10.5]"
        r'(?i)[\s\._\-]EP?(\d{1,3}(?:\.\d)?)',    # For E01, EP01, -01, .01, 10.5
        r'-\s*(\d{1,3}(?:\.\d)?)',                # For formats like " - 01"
        r'\s(\d{1,3}(?:\.\d)?)\b',                # For formats like "... 01.ass" or "... 10.5.ass"
        # NEW: For numbers at the end of the filename stem (e.g. name01.ass, name1.ass)
        # Looks for 1-3 digits (optional decimal) before the file extension(s).
        # (?<!\d) ensures we don't match the last 3 digits of a year like 2020.
        r'(?<!\d)(\d{1,3}(?:\.\d)?)(?:v\d)?(?=(?:\.[a-zA-Z0-9]+)+$)',
    ]

    for pattern in regular_patterns:
        match = re.search(pattern, filename)
        if match:
            # Return the last non-empty group, which is always the number
            return [g for g in match.groups() if g is not None][-1].strip()
            
    return None

def expand_paths(paths, recursive=True):
    """
    Expands directories in the list to include files.
    If recursive is True, walks all subdirectories.
    If recursive is False, only checks the top level of directories.
    Handles Font folders as units.
    """
    expanded = []
    for p in paths:
        if os.path.isfile(p):
            expanded.append(p)
        elif os.path.isdir(p):
            # Check if the folder is a Font folder (treat as unit)
            if re.search(r'(?i)font', os.path.basename(p.rstrip(os.sep))):
                expanded.append(p)
            else:
                if recursive:
                    for root, dirs, files in os.walk(p):
                        font_dirs = [d for d in dirs if re.search(r'(?i)font', d)]
                        for fd in font_dirs:
                            expanded.append(os.path.join(root, fd))
                            dirs.remove(fd)
                        
                        for f in files:
                            if f.lower() in ['.ds_store', 'thumbs.db', 'desktop.ini']:
                                continue
                            expanded.append(os.path.join(root, f))
                else:
                    try:
                        for entry in os.scandir(p):
                            if entry.is_file():
                                if entry.name.lower() in ['.ds_store', 'thumbs.db', 'desktop.ini']:
                                    continue
                                expanded.append(entry.path)
                            elif entry.is_dir() and re.search(r'(?i)font', entry.name):
                                expanded.append(entry.path)
                    except PermissionError as e:
                        print(f"{COLOR_RED}Permission denied accessing '{p}': {e}{COLOR_RESET}")

    return expanded

def ask_with_preset(config_key, question, options):
    """Generic function to ask a question or use a preset."""
    preset_value = CONFIG.get(config_key)
    if preset_value is not None and preset_value in options.keys():
        print(f"\nPreset found for '{question}': Choosing '{options[preset_value]}'")
        return preset_value
    
    print(f"\n{question}")
    for key, value in options.items():
        print(f"  {key}. {value}")
    
    while True:
        try:
            choice = int(input(f"Enter your choice ({'/'.join(map(str, options.keys()))}): "))
            if choice in options.keys():
                return choice
            else: print(f"{COLOR_RED}Invalid choice.{COLOR_RESET}")
        except ValueError: print(f"{COLOR_RED}Invalid input.{COLOR_RESET}")

def get_files_from_user(prompt_message):
    """
    Gets a list of file paths from user drag-and-drop input.
    Validates input and asks for recursion if subfolders are detected.
    """
    print(prompt_message)
    print("Press Enter on an empty line to exit.")
    print("-" * 50)
    try:
        paths_input = input()
    except KeyboardInterrupt:
        print(f"\n{COLOR_RED}Operation cancelled by user.{COLOR_RESET}")
        return None

    if not paths_input.strip():
        return None

    # Easter Egg check
    if paths_input.strip().lower() == 'jjj':
        clear_screen()
        print("""
            !#%@^&^%&$#!25.8.22-27 v-0.1$#&^#*&&$#%@
            DeepSeeK test \ ChatGPT test
            Many bugs and doesn't work well

            -------------25.8.29 v0.1-------------
            Gimini Pro Initial Release
            - Supports dragging in subtitle files and generating target subtitle filenames based on user-defined naming.
            - Supports selecting the save location (same folder or \sub folder).
            - Supports selecting which language subtitles to process (based on the language codes in the filename).
            - Supports 'sp mode' to name subtitles individually according to the filename of each video episode.
            (Applicable to files where each episode's filename is different but contains a numerical sequence.)
            - Generates a list showing the filenames before and after renaming.

            -------------25.9.2 v0.2-------------
            - Added the function to return by pressing the Enter key at the end.
            - Improved the handling of multiple language codes (prompts the user to select processing for a single language or all, with the option to add a suffix).
            - Added the optional function to delete the original subtitle files after processing.
            - Added interactive prompting for how to handle unprocessed files.
            - Added a USER CONFIGURATION area.
            (You can modify the configuration to skip prompts if you consistently process subtitle files using a single method.)
            - Added color prompts for errors.

            -------------25.9.2 v0.3-------------
            - Adjusted the disposal method for unprocessed files ↓
            (Moves if the user opts to delete the original subtitle file, copies otherwise.)
            - Fixed a crash when processing special filenames (not modified; later found to be caused by a long file path).
            - Added an example for the PRESET_LANGUAGE preset (string, needs to be enclosed in []).

            -------------25.9.3 v0.4-------------
            - Added interactive processing for Fonts files.
            - Added a USER CONFIGURATION switch for this feature.

            -------------25.9.3 v0.5-------------
            - Added handling for episode numbers that are single digits (keeps the single-digit naming for target files).
            - Added the method of dragging in a target file to obtain the filename (now supports both dragging and input).
            - Added file processing functionality for Movie Mode (no episode numbers).

            -------------25.9.3 v0.6-------------
            - Fixed incorrect numerical sequence recognition in Movie Mode filenames.

            -------------25.9.3 v0.6.1-------------
            - Movie Mode modification removed and changed to a prompt to enter 'sp mode'.
            - Now, dragging in a filename without a numerical sequence automatically prompts whether to enter 'sp mode'.

            -------------25.9.3 v0.6.2-------------
            - Added a USER CONFIGURATION switch for 'sp mode'.

            -------------25.9.5 v0.6.3-------------
            - Added Fonts folder processing.
            - Fixed a variable error in 'sp mode'.

            -------------25.9.5 v0.7-------------
            - Adjusted the order of options for some interactive prompts.
            - Added more red prompts for errors.

            ------------25.9.5 v0.7.1------------
            - Added green success prompts.
            - Added more red prompts for errors.*2

            ------------25.9.5 v0.7.2------------
            - Added the display of unprocessed filenames when handling a mix of movie and series episodes.

            -------------25.9.12 v0.8-------------
            - The display page for new and old target filenames is now sorted by natural number order.
            - Fixed an issue where language codes were not recognized.
            - Added more language codes.

            ------------25.9.12 v0.8.1------------
            - Fixed a crash.

            ------------25.9.12 v0.8.2------------
            - Optimized subtitle filename recognition; now (should) be able to handle files where the title contains numbers.
            (U right → Steins;Gate 0)

            -------------25.9.19 v0.9-------------
            - Added handling for special episode numbers like OVA01 and .5 episodes.
            - Designed the initial version of the icon.

            -----------25.9.19 v0.9.1&2-----------
            - Increased program robustness.

            ------------25.9.19 v0.9.3------------
            - Fixed recognition issues when a filename only contains "OVA," "OAD," etc., without an episode number.
            - Added Chinese support.

            ------------25.9.25 v0.9.4------------
            - Added jjj easter egg.
            - Fixed an issue where entering plain text for the subtitle file location caused an error.
            - Designed the second version of the icon.

            ------------25.9.26 v0.9.5------------
            - Added the Enter key exit function.
            - Added a screen clear for jjj.

            ------------25.9.26 v0.9.6------------
            - Fixed an error when entering a filename without a numerical sequence in 'sp mode'.
            - Fixed the issue where text color was not resetting.
            - Corrected Chinese translation.

            ------------25.9.26 v0.9.7------------
            - Optimized filename recognition to support S1E01 format.
            - Added episode number recognition for Korean, Russian, Spanish, and other language namings.
            - Synchronously updated the recognition script for the 'sp' section.

            ------------25.9.26 v0.9.8------------
            - Fixed Chinese "第x话" recognition, supporting filename recognition for more languages.
            - Optimized the automatic filename recognition mechanism.
            - Significantly improved the Chinese translation.
              
            ------------26.1.12 v0.9.9------------
            - Added support for folders.
            - Fixed the issue where titles and numbers in filenames were not separated, causing to be unrecognized.
            - Fixed the naming issues with special file names like OVA and OAD; now will follow the format entered by the user.

            ----------The above is the boring update log----------

            This program was poorly written by Gemini-CV (Ctrl+C+V) programmer Yamada.
            Please ensure that the program you obtained is free of charge; if you paid for this program, please request a refund immediately and report the seller.
            Please visit https://github.com/Yamada-da/SubRename to get the latest version (probably).
            I await your bizarre issues in the 'issues' section (please include the filename and a description).
              """)
        input("Press Enter to return...")
        return 'restart'

    # Path parsing
    paths = re.findall(r'\"([^\"]+)\"|\'([^\']+)\'|(\S+)', paths_input)
    cleaned_paths = [item for sublist in paths for item in sublist if item]
    cleaned_paths = [path for path in cleaned_paths if path.strip() != '&']
    
    if not cleaned_paths:
        print(f"\n{COLOR_RED}Error: No valid input detected.{COLOR_RESET}")
        input("Press Enter to return...")
        return 'restart'

    # Path validation
    valid_inputs = []
    invalid_found = False
    for path in cleaned_paths:
        if os.path.exists(path):
            valid_inputs.append(path)
        else:
            invalid_found = True

    if not valid_inputs or invalid_found and not valid_inputs:
        print(f"\n{COLOR_RED}Error: Please provide a valid file or folder path. Please drag and drop instead of typing manually.{COLOR_RESET}")
        input("Press Enter to return...")
        return 'restart'

    # Check for subdirectories to ask about recursion
    has_subdirs = False
    for path in valid_inputs:
        if os.path.isdir(path):
            try:
                for entry in os.scandir(path):
                    if entry.is_dir() and not re.search(r'(?i)font', entry.name):
                        has_subdirs = True
                        break
            except PermissionError:
                pass
        if has_subdirs:
            break
    
    recursive = True
    if has_subdirs:
        choice = ask_with_preset(None, "Subdirectories detected. How to process?", 
                                 {1: "Current folder only (Non-recursive)", 2: "Include all subfolders (Recursive)"})
        recursive = (choice == 2)

    return expand_paths(valid_inputs, recursive=recursive)


def get_language_from_filename(filename):
    """Extracts language code from a filename."""
    known_langs = {'ar', 'bg', 'ca', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'hi', 'hu', 'id', 'is', 'it', 'ja', 'jp', 'ko', 'lt', 'lv', 'ms', 'my', 'nb', 'ne', 'nl', 'nn', 'pl', 'pt', 'ro', 'ru', 'sc', 'sk', 'sl', 'sv', 'tc', 'th', 'tl', 'tr', 'uk', 'ur', 'vi', 'zh', 'ara', 'ces', 'chs', 'cht', 'chi', 'cho', 'dan', 'deu', 'ell', 'eng', 'fil', 'fin', 'fra', 'heb', 'hun', 'hy', 'ind', 'isl', 'ita', 'jpn', 'kor', 'lat', 'nor', 'pol', 'por', 'ron', 'rus', 'slk', 'slv', 'spa', 'swe', 'tha', 'tur', 'ukr', 'und', 'vie', 'zho', 'zxx', 'ensc', 'entc', 'enjp', 'jpen', 'jpsc', 'jptc', 'scjp', 'scen', 'tcjp', 'tcen', 'zh-CN', 'zh-HK', 'zh-MO', 'zh-SG', 'zh-TW', 'chs-eng', 'cht-eng', 'de-AT', 'de-CH', 'en-AU', 'en-CA', 'en-GB', 'en-IE', 'en-NZ', 'en-US', 'en-ZA', 'en_sc', 'en_tc', 'en+sc', 'en+tc', 'es-419', 'es-LA', 'es-MX', 'es-ES', 'fr-BE', 'fr-CA', 'it-CH', 'nl-BE', 'pt-BR', 'pt-PT', 'sc-en', 'sc-jp', 'sr-Cyrl', 'sr-Latn', 'tc-en', 'tc-jp', 'zh-Hans', 'zh-Hant', 'chs&jpn', 'cht&jpn', 'eng&jpn', 'engsub', 'en-forced'}
    lang_match = re.search(r'\.([a-zA-Z\d\-_&]{2,15})\.([a-zA-Z]{2,4})$', filename)
    if lang_match and lang_match.group(1).lower() in known_langs:
        return lang_match.group(1).lower()
    return "default"

def group_and_select_languages(file_paths):
    """
    Groups files by episode, determines if it's a movie or series, and selects languages.
    """
    episodes = {}
    language_codes = set()
    for path in file_paths:
        filename = os.path.basename(path)
        if re.search(r'(?i)font', filename):
            continue 
        
        episode_id = extract_episode_identifier(filename)
        if not episode_id:
            base_name_for_grouping = re.sub(r'(\.[a-zA-Z]{2,5})?\.[a-zA-Z]{2,4}$', '', filename)
            episode_id = f"_SINGLE_{base_name_for_grouping}"

        lang = get_language_from_filename(filename)
        if lang != "default":
            language_codes.add(lang)
        if episode_id not in episodes:
            episodes[episode_id] = {}
        episodes[episode_id][lang] = path

    if not episodes:
        return [], "default", False

    has_series = any(not id.startswith("_SINGLE_") for id in episodes.keys())
    has_movies = any(id.startswith("_SINGLE_") for id in episodes.keys())

    if has_series and has_movies:
        print(f"{COLOR_RED}Warning: Mixed series and movie-style files detected. Processing series files only.{COLOR_RESET}")
        movie_files_skipped = []
        for episode_id, lang_files in episodes.items():
            if episode_id.startswith("_SINGLE_"):
                for path in lang_files.values():
                    movie_files_skipped.append(os.path.basename(path))
        if movie_files_skipped:
            print(f"{COLOR_RED}The following movie-style files will be ignored:{COLOR_RESET}")
            for filename in sorted(movie_files_skipped):
                print(f"{COLOR_RED}- {filename}{COLOR_RESET}")
        episodes = {k: v for k, v in episodes.items() if not k.startswith("_SINGLE_")}
    
    is_movie_mode = not has_series and has_movies
    
    preset_lang = CONFIG.get("PRESET_LANGUAGE")
    chosen_lang_str = None
    if isinstance(preset_lang, list):
        preset_lang_lower = [l.lower() for l in preset_lang]
        if 'all' in preset_lang_lower:
             print("\nPreset found: Processing 'all' languages.")
             chosen_lang_str = 'all'
        else:
            found_preset = set(preset_lang_lower) & language_codes
            if found_preset:
                chosen_lang_str = sorted(list(found_preset))[0]
                print(f"\nPreset found: Processing '{chosen_lang_str}' language files.")
            else:
                 print(f"\n{COLOR_RED}Preset language not found in files. Asking for selection.{COLOR_RESET}")
    
    if chosen_lang_str is None:
        if len(language_codes) > 1:
            print("\nMultiple language versions found. Please choose:")
            lang_list = sorted(list(language_codes))
            for i, lang_code in enumerate(lang_list):
                print(f"  {i + 1}. {lang_code}")
            print(f"  {len(lang_list) + 1}. all")
            while True:
                try:
                    choice = int(input(f"Enter your choice (1-{len(lang_list) + 1}): "))
                    if 1 <= choice <= len(lang_list):
                        chosen_lang_str = lang_list[choice - 1]
                        break
                    elif choice == len(lang_list) + 1:
                        chosen_lang_str = "all"
                        break
                    else: print(f"{COLOR_RED}Invalid choice.{COLOR_RESET}")
                except ValueError: print(f"{COLOR_RED}Invalid input.{COLOR_RESET}")
        elif language_codes:
            chosen_lang_str = language_codes.pop()
        else:
            chosen_lang_str = "default"

    files_to_process = []
    sorted_episodes = sorted(episodes.items(), key=lambda item: natural_sort_key(item[0]))

    if chosen_lang_str == "all":
        for _, lang_files in sorted_episodes:
            for lang, path in lang_files.items():
                files_to_process.append((path, lang))
    else:
        for _, lang_files in sorted_episodes:
            if chosen_lang_str in lang_files:
                files_to_process.append((lang_files[chosen_lang_str], chosen_lang_str))
            elif "default" in lang_files:
                files_to_process.append((lang_files["default"], "default"))

    return files_to_process, chosen_lang_str, is_movie_mode

def ask_add_suffix(lang_choice):
    if lang_choice == "all":
        print("\nLanguage suffix will be added to filenames to prevent conflicts.")
        return True
    if lang_choice == "default": return False
    
    choice = ask_with_preset(
        "PRESET_ADD_SUFFIX",
        f"Add '.{lang_choice}' suffix to new filenames?",
        {1: "No", 2: "Yes"}
    )
    return choice == 2

def get_target_format(is_movie_mode=False):
    print("\n" + "-" * 50)
    if is_movie_mode:
        print("Enter the target filename (you can also drag and drop the video file).")
    else:
        print("Enter the target video filename format (or drag and drop a sample video file).")
        print("Example: [Majo no Tabitabi][01][BDRIP][1080P][H264_FLAC]")
        print("Or, type 'sp' for special processing (naming based on other video files).")
    print("-" * 50)
    while True:
        target_input = input("Target format: ")
        
        if not is_movie_mode and target_input.lower() == 'sp': 
            return 'sp'

        cleaned_path = target_input.strip().strip('"\'')
        if os.path.isfile(cleaned_path):
            print(f"File detected, using format: {os.path.basename(cleaned_path)}")
            target_format = os.path.basename(cleaned_path)
        else:
            target_format = target_input

        if re.search(r'[/\\:*\?"<>|]', target_format):
            print(f"{COLOR_RED}Error: Format contains illegal characters.{COLOR_RESET}")
            continue
        
        if not is_movie_mode and not re.search(r'\d+', target_format):
            print(f"{COLOR_RED}Error: Format must contain a number placeholder (e.g., '01').{COLOR_RESET}")
            continue
            
        return os.path.splitext(target_format)[0]

def generate_rename_plan(files_with_lang, target_format, add_suffix, is_movie_mode=False):
    rename_plan = []
    
    if is_movie_mode:
        for old_path, lang_code in files_with_lang:
            base_ext = "." + old_path.split('.')[-1]
            new_filename = f"{target_format}.{lang_code}{base_ext}" if add_suffix and lang_code != 'default' else target_format + base_ext
            rename_plan.append((old_path, new_filename))
        return rename_plan

    if target_format != 'sp':
        best_match = None
        patterns = [
            r'(?i)S\d{1,2}E(\d{1,3}(?:\.\d)?)',
            r'第(\d{1,3}(?:\.\d)?)(?:集|話|话)',
            r'(\d{1,3}(?:\.\d)?)\s*화',
            r'(?i)(?:Episodio|Episódio|Episod)\s*(\d{1,3}(?:\.\d)?)',
            r'(?i)(?:ตอน(?:ที่)?)\s*(\d{1,3}(?:\.\d)?)',
            r'(?i)(?:Эпизод|Серия)\s*(\d{1,3}(?:\.\d)?)',
            r'(?i)Épisode\s*(\d{1,3}(?:\.\d)?)',
            r'-\s*(\d{1,3}(?:\.\d)?)',
            r'[\s\._]EP(\d{1,3}(?:\.\d)?)',
            r'\[(\d{1,3}(?:\.\d)?(?:v\d)?)\]',
            r'\s(\d{1,3}(?:\.\d)?)\b(?!p|i)',
        ]
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, target_format, re.IGNORECASE))
            if matches:
                best_match = matches[-1]
                break
        
        if not best_match:
            all_numbers = list(re.finditer(r'(\d+\.?\d*)', target_format))
            for match in reversed(all_numbers):
                end_pos = match.end()
                if end_pos == len(target_format) or not target_format[end_pos].isalpha():
                    best_match = match
                    break
        
        if not best_match:
            print(f"{COLOR_RED}Error: Could not reliably identify an episode number placeholder in the target format.{COLOR_RESET}")
            print(f"{COLOR_RED}Target format: '{target_format}'{COLOR_RESET}")
            return []

        placeholder_group_index = len(best_match.groups())
        placeholder_number_part = best_match.group(placeholder_group_index)
        
        padding = len(placeholder_number_part.split('.')[0]) if '.' in placeholder_number_part else len(placeholder_number_part)
        start, end = best_match.span(placeholder_group_index)

        # Check if the character immediately preceding the number is alphanumeric
        prev_char_is_alnum = False
        if start > 0 and target_format[start-1].isalnum():
            prev_char_is_alnum = True

        for old_path, lang_code in files_with_lang:
            old_filename = os.path.basename(old_path)
            base_ext = "." + old_filename.split('.')[-1]
            episode_id = extract_episode_identifier(old_filename)
            if not episode_id: continue
            
            special_match = re.match(r'([A-Z]+)(\d+\.?\d*)', episode_id, re.IGNORECASE)
            if special_match:
                prefix = special_match.group(1)
                num_part = special_match.group(2)
                try:
                    formatted_num = f"{int(float(num_part)):0{padding}d}"
                    
                    # Logic: If compact (test1), keep compact (testOVA1). 
                    # If spaced/symbol (test 01, [01]), force space (test OVA 01, [OVA 01]).
                    if prev_char_is_alnum:
                        formatted_episode_id = f"{prefix}{formatted_num}"
                    else:
                        formatted_episode_id = f"{prefix} {formatted_num}"
                        
                except ValueError:
                    formatted_episode_id = episode_id
            else:
                try:
                    if '.' in episode_id:
                        integer_part, decimal_part = episode_id.split('.')
                        formatted_episode_id = f"{int(integer_part):0{padding}d}.{decimal_part}"
                    else:
                        formatted_episode_id = f"{int(episode_id):0{padding}d}"
                except ValueError:
                    formatted_episode_id = episode_id
            
            new_filename_base = target_format[:start] + formatted_episode_id + target_format[end:]
            new_filename = f"{new_filename_base}.{lang_code}{base_ext}" if add_suffix and lang_code != 'default' else new_filename_base + base_ext
            rename_plan.append((old_path, new_filename))

    else: # 'sp' mode
        video_prompt = "Please drag and drop the corresponding VIDEO files and press Enter:"
        cleaned_video_paths = get_files_from_user(video_prompt)
        
        if cleaned_video_paths == 'restart':
            return 'restart'

        if not cleaned_video_paths:
            print(f"\n{COLOR_RED}Error: No video files provided. Aborting.{COLOR_RESET}")
            return None
        video_map = {}
        for v_path in cleaned_video_paths:
            v_filename = os.path.basename(v_path)
            episode_id = extract_episode_identifier(v_filename)
            if episode_id: video_map[episode_id] = v_path
            else: print(f"{COLOR_RED}Warning: Could not determine episode ID for video '{v_filename}'. It will be ignored.{COLOR_RESET}")

        for old_path, lang_code in files_with_lang:
            old_filename = os.path.basename(old_path)
            base_ext = "." + old_filename.split('.')[-1]
            episode_id = extract_episode_identifier(old_filename)
            if episode_id in video_map:
                video_basename = os.path.splitext(os.path.basename(video_map[episode_id]))[0]
                new_filename = f"{video_basename}.{lang_code}{base_ext}" if add_suffix and lang_code != 'default' else video_basename + base_ext
                rename_plan.append((old_path, new_filename))
            else:
                print(f"{COLOR_RED}Warning: No matching video file found for subtitle with episode ID '{episode_id}'. Skipping.{COLOR_RESET}")
    return rename_plan

def execute_rename_plan(rename_plan):
    """
    Executes the rename plan and returns a list of target directories.
    """
    if not rename_plan:
        print(f"\n{COLOR_RED}Nothing to rename.{COLOR_RESET}")
        return None, 1
        
    # Sort by directory first, then by new filename naturally
    rename_plan.sort(key=lambda item: (os.path.dirname(item[0]), natural_sort_key(item[1])))

    clear_screen()
    print("The following files will be created. Please review:")
    print("=" * 60)
    
    current_dir = None
    for old_path, new_name in rename_plan:
        file_dir = os.path.dirname(old_path)
        if file_dir != current_dir:
            if current_dir is not None:
                print("") # Spacing between groups
            print(f"Path: {file_dir}")
            current_dir = file_dir
        
        print(f"Original: {os.path.basename(old_path)}")
        print(f"    New →: {new_name}\n")

    print("=" * 60)
    if input("Press ENTER to continue, or any other key to cancel: ") != "":
        print(f"\n{COLOR_RED}Operation cancelled by user.{COLOR_RESET}")
        return None, 1
    
    location_choice = ask_with_preset("PRESET_SAVE_LOCATION", "Where would you like to save the new files?", {1: "In a new 'sub' subfolder", 2: "In the same folder"})
    
    print("\nProcessing files...")
    count = 0
    # Track used directories for report and subsequent font processing
    used_directories = set()

    for old_path, new_name in rename_plan:
        try:
            # Determine target directory relative to the *source file*
            source_dir = os.path.dirname(old_path)
            if location_choice == 1: # Sub folder
                target_dir = os.path.join(source_dir, 'sub')
            else:
                target_dir = source_dir
            
            os.makedirs(target_dir, exist_ok=True)
            used_directories.add(target_dir)

            shutil.copy2(old_path, os.path.join(target_dir, new_name))
            count += 1
        except Exception as e:
            print(f"{COLOR_RED}Error copying '{os.path.basename(old_path)}': {e}{COLOR_RESET}")
    
    print(f"\n{COLOR_GREEN}Successfully created {count} new files.{COLOR_RESET}")

    delete_choice = 1
    if count > 0:
        delete_choice = ask_with_preset("PRESET_DELETE_ORIGINALS", "Delete the original processed files?", {1: "No", 2: "Yes"})
        if delete_choice == 2:
            print("\nDeleting original files...")
            deleted_count = 0
            for old_path, _ in rename_plan:
                try:
                    os.remove(old_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"{COLOR_RED}Error deleting '{os.path.basename(old_path)}': {e}{COLOR_RESET}")
            print(f"{COLOR_GREEN}Successfully deleted {deleted_count} original files.{COLOR_RESET}")
    
    return location_choice, delete_choice

def handle_unprocessed_files(all_files, processed_files, location_choice, delete_choice):
    processed_set = set(processed_files)
    unprocessed_files = [path for path in all_files if path not in processed_set]

    if not unprocessed_files:
        return

    font_files = []
    other_unprocessed = []
    for path in unprocessed_files:
        if re.search(r'(?i)font', os.path.basename(path)):
            font_files.append(path)
        else:
            other_unprocessed.append(path)
    
    action = shutil.move if delete_choice == 2 else shutil.copy2
    action_verb = "Moving" if delete_choice == 2 else "Copying"

    if font_files:
        handle_fonts_choice = ask_with_preset(
            "PRESET_HANDLE_FONTS",
            "How to handle unprocessed font items (archives or folders)?",
            {1: "Archive to 'Fonts' folder", 2: "Ignore (do nothing)"}
        )
        if handle_fonts_choice == 1:
            print(f"\n{action_verb} font items...")
            font_count = 0
            for path in font_files:
                try:
                    # Determine target dir relative to this font item
                    source_dir = os.path.dirname(path)
                    if location_choice == 1:
                        target_dir = os.path.join(source_dir, 'sub', 'Fonts')
                    else:
                        target_dir = os.path.join(source_dir, 'Fonts')
                    
                    os.makedirs(target_dir, exist_ok=True)

                    if os.path.isdir(path):
                        if action == shutil.move:
                            for item_name in os.listdir(path):
                                source_item = os.path.join(path, item_name)
                                dest_item = os.path.join(target_dir, item_name)
                                shutil.move(source_item, dest_item)
                            os.rmdir(path)
                        else: # copy action
                            if sys.version_info >= (3, 8):
                                shutil.copytree(path, target_dir, dirs_exist_ok=True)
                            else:
                                for item in os.listdir(path):
                                    s = os.path.join(path, item)
                                    d = os.path.join(target_dir, item)
                                    if os.path.isdir(s):
                                        shutil.copytree(s, d, symlinks=True)
                                    else:
                                        shutil.copy2(s, d)
                        font_count += 1
                    else: # It's a file
                        action(path, os.path.join(target_dir, os.path.basename(path)))
                        font_count += 1
                except Exception as e:
                    print(f"{COLOR_RED}Error processing font item '{os.path.basename(path)}': {e}{COLOR_RESET}")
            print(f"{COLOR_GREEN}Successfully processed {font_count} font items.{COLOR_RESET}")


    if other_unprocessed:
        archive_choice = ask_with_preset(
            "PRESET_ARCHIVE_UNPROCESSED",
            "Move/Copy other unprocessed subtitle files into language-specific folders?",
            {1: "Yes", 2: "No"}
        )
        if archive_choice == 1:
            print(f"\n{action_verb} other unprocessed files...")
            archived_count = 0
            for path in other_unprocessed:
                filename = os.path.basename(path)
                lang = get_language_from_filename(filename)
                if lang == "default":
                    lang = "misc"
                
                # Determine target dir relative to this file
                source_dir = os.path.dirname(path)
                if location_choice == 1:
                    target_dir = os.path.join(source_dir, 'sub', lang)
                else:
                    target_dir = os.path.join(source_dir, lang)
                
                os.makedirs(target_dir, exist_ok=True)
                
                try:
                    action(path, os.path.join(target_dir, filename))
                    archived_count += 1
                except Exception as e:
                    print(f"{COLOR_RED}Error processing '{filename}': {e}{COLOR_RESET}")
            print(f"{COLOR_GREEN}Successfully processed {archived_count} other unprocessed files.{COLOR_RESET}")

def main():
    while True:
        clear_screen()
        print("Subtitle Renamer (v 0.9.9)")
        all_subtitle_paths = get_files_from_user("Please drag and drop SUBTITLE files or FOLDERS and press Enter:")
        
        if all_subtitle_paths == 'restart':
            continue
        if not all_subtitle_paths: 
            break

        files_to_process, lang_choice, is_movie_mode = group_and_select_languages(all_subtitle_paths)
        if not files_to_process:
            print(f"\n{COLOR_RED}No files left to process after language selection.{COLOR_RESET}")
        else:
            add_suffix = ask_add_suffix(lang_choice)
            target_format = None

            # Check for forced SP mode preset for series
            force_sp_preset = CONFIG.get("FORCE_SP_MODE")
            if not is_movie_mode and force_sp_preset == 1:
                print("\nPreset found: Automatically entering SP Mode for this series.")
                target_format = 'sp'
            
            # If not forced into SP mode, proceed with normal logic
            if target_format is None:
                if is_movie_mode:
                    print("\n" + "-" * 50)
                    print(f"{COLOR_RED}No episode numbers were detected in the subtitle files.{COLOR_RESET}")
                    movie_choice = ask_with_preset(
                        None, # This is a dynamic choice, not suitable for a simple preset
                        "How to proceed?",
                        {
                            1: "Enter Movie Mode (rename based on a single target filename)",
                            2: "Proceed Normally (treat as a series, requires a number in format)"
                        }
                    )
                    if movie_choice == 1:
                        target_format = get_target_format(is_movie_mode=True)
                    else: # Choice is 2
                        print("\nProceeding in Series Mode as requested.")
                        is_movie_mode = False # Override detection
                        target_format = get_target_format(is_movie_mode=False)
                else: # Regular series mode
                    target_format = get_target_format(is_movie_mode=False)

            if not target_format:
                if input("\nPress ENTER to start another conversion, or any other key to exit: ") != "":
                    break
                else:
                    continue

            # Generate plan using the final is_movie_mode value which might have been overridden
            rename_plan = generate_rename_plan(files_to_process, target_format, add_suffix, is_movie_mode)
            
            if rename_plan == 'restart':
                continue

            location_choice, delete_choice = execute_rename_plan(rename_plan)

            # location_choice is None if cancelled
            if location_choice:
                processed_paths = [item[0] for item in rename_plan] if rename_plan else []
                handle_unprocessed_files(all_subtitle_paths, processed_paths, location_choice, delete_choice)

        if input("\nPress ENTER to start another conversion, or any other key to exit: ") != "":
            break

if __name__ == "__main__":
    if sys.platform == "win32":
        os.system('')
    main()
