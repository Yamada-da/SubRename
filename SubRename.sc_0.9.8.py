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
# ================================ 用户预设区 ===================================
# ==============================================================================
# 填写说明:
# - 如需添加脚本预设，请将预设值替换掉 'None' 
# - 如预设值未定义或预设值为 'None' , 脚本则按交互式提问运行
#
CONFIG = {
    # 预设 默认处理语言（自动识别字幕文件名中包含的以下配置中的语言缩写）
    # 请注意: 此处填入的值必须为字符串列表（包含[""]，详见下方示例）
    # 示例1: ["sc", "chs", "scjp", "chs&jpn", "jpsc", "zh-CN", "zh"] 自动识别处理简体中文（列表可添加）
    # 示例2: ["all"] 自动处理所有识别到的语言（默认将在生成文件中添加所有语言缩写）
    # 设置为 None 则每次询问
    "PRESET_LANGUAGE": None,

    # 预设 是否在输出的字幕文件中添加语言后缀（如'.sc'）。
    # 1 = 否, 2 = 是, None = 每次询问
    "PRESET_ADD_SUFFIX": None,

    # 预设 输出字幕文件保存位置
    # 1 = 新建 'sub' 文件夹保存, 2 = 保存在原字幕文件夹下, None = 每次询问
    "PRESET_SAVE_LOCATION": None,

    # 预设 是否删除字幕原文件
    # 1 = 不删除, 2 = 删除, None = 每次询问
    "PRESET_DELETE_ORIGINALS": None,
    
    # 预设 是否归档未处理字幕文件（如未处理 '.tc' 则保存在 'tc' 文件夹下）
    # 1 = 是, 2 = 否, None = 每次询问
    "PRESET_ARCHIVE_UNPROCESSED": None,

    # 预设 如何处理字体文件 (如：Fonts.zip).
    # 1 = 将字体文件归档到 'Fonts' 文件夹, 2 = 忽略 (不进行操作), None = 每次询问
    "PRESET_HANDLE_FONTS": None,

    # 预设 是否默认开启sp模式
    # 开启sp模式将跳过格式提醒，自动进入基于每集视频文件命名，处理每集有不同文件名的模式
    # 1 = 开启sp模式, None = 不开启sp模式
    "FORCE_SP_MODE": None,
}
# ==============================================================================
# ================================ 预设区结束 ===================================
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
            groups = [g for g in match.groups() if g is not None]
            return "".join(groups).upper()

    # Patterns for regular episodes, now supporting decimals and international formats
    regular_patterns = [
        r'(?i)S\d{1,2}E(\d{1,3}(?:\.\d)?)',       # For S01E01, S01E10.5 etc.
        r'第(\d{1,3}(?:\.\d)?)(?:集|話|话)',      # For 第1集, 第1話, 第1话 (Chinese, Japanese)
        r'(\d{1,3}(?:\.\d)?)\s*화',              # For 1화 (Korean)
        r'(?i)(?:Épisode|Episodio|Episódio|Episod)\s*(\d{1,3}(?:\.\d)?)', # For Épisode/Episodio/Episódio/Episod 1 (French, Italian, Spanish, Portuguese, Malay)
        r'(?i)(?:ตอน(?:ที่)?)\s*(\d{1,3}(?:\.\d)?)', # For ตอน 1 (Thai)
        r'(?i)(?:Эпизод|Серия)\s*(\d{1,3}(?:\.\d)?)', # For Эпизод 1, Серия 1 (Russian)
        r'\[(\d{1,3}(?:\.\d)?(?:v\d)?)\]',        # For [01] or "[01v2]" or "[10.5]"
        r'(?i)[\s\._\-]EP?(\d{1,3}(?:\.\d)?)',    # For E01, EP01, -01, .01, 10.5
        r'-\s*(\d{1,3}(?:\.\d)?)',                # For formats like " - 01"
        r'\s(\d{1,3}(?:\.\d)?)\b',                # For formats like "... 01.ass" or "... 10.5.ass"
    ]

    for pattern in regular_patterns:
        match = re.search(pattern, filename)
        if match:
            return [g for g in match.groups() if g is not None][-1].strip()
            
    return None

def get_files_from_user(prompt_message):
    """
    Gets a list of file paths from user drag-and-drop input.
    Validates input for file existence and handles easter egg.
    """
    print(prompt_message)
    print("可按回车退出")
    print("-" * 50)
    try:
        paths_input = input()
    except KeyboardInterrupt:
        print(f"\n{COLOR_RED}用户取消操作{COLOR_RESET}")
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
              Gimini Pro初版
              支持拖入字幕文件，按用户命名生成目标字幕文件名
              支持选择保存位置（同文件夹或\sub文件夹）
              支持选择处理哪种语言字幕（依据文件名中的语言缩写）
              支持sp模式根据每一集视频文件名来单独命名字幕
              （适用于每一集文件名不同，但包含数字序列的文件）
              生成列表，展示命名前后文件名

              -------------25.9.2 v0.2-------------
              新增结束时回车键返回功能
              改进多语言缩写时处理方法（提示用户选择单个或全部语言处理，可选增加后缀）
              新增可选删除已处理字幕原文件的功能
              新增交互式询问未处理文件的处理方法
              增加USER CONFIGURATION区域
              （用户如长期单一方法处理字幕文件可修改配置后跳过询问）
              增加错误的颜色提示

              -------------25.9.2 v0.3-------------
              调整未处理文件的处置方法↓
              （依据用户是否删除原字幕文件，删除则move，未删除则copy）
              处理特殊文件名时闪退（未修改，后排查是文件所在路径超长导致）
              增加PRESET_LANGUAGE预设的示例（字符串，需加上[]）

              -------------25.9.3 v0.4-------------
              增加Fonts文件的交互式处理
              并增加USER CONFIGURATION开关

              -------------25.9.3 v0.5-------------
              增加输入集数为个位数的处理方法（保持个位数命名目标文件）
              增加拖入目标文件来获取文件名的方法（现可拖入亦可输入）
              增加电影模式（无集数）的文件处理功能

              -------------25.9.3 v0.6-------------
              修复电影模式文件名数字序列识别错误

              -------------25.9.3 v0.6.1-------------
              删除电影模式修改为提示进入sp模式
              现拖入非数字序列文件名则自动询问是否进入sp模式

              -------------25.9.3 v0.6.2-------------
              添加sp模式的USER CONFIGURATION开关

              -------------25.9.5 v0.6.3-------------
              增加Fonts文件夹处理
              修复sp模式下的一个变量错误

              -------------25.9.5 v0.7-------------
              为部分交互式提问的选项进行前后调整
              增加更多的错误红色提示

              ------------25.9.5 v0.7.1------------
              增加绿色成功提示
              再次新增部分错误红色提示

              ------------25.9.5 v0.7.2------------
              新增了混合电影剧集处理时未处理文件名的展示

              -------------25.9.12 v0.8-------------
              目标文件名新旧的展示页按自然数字排序展示
              修复language codes无法识别问题
              暴增了更多的language codes

              ------------25.9.12 v0.8.1------------
              修复闪退

              ------------25.9.12 v0.8.2------------
              优化字幕文件名识别，现在(应该)可以处理片名内包含数字的文件了
              （是的, 是你→ Steins;Gate 0）

              -------------25.9.19 v0.9-------------
              增加OVA01及.5集等特殊集数的处理
              设计了初版图标

              -----------25.9.19 v0.9.1&2-----------
              增加程序鲁棒性（修闪退）

              ------------25.9.19 v0.9.3------------
              修复当文件名只含有OVA，OAD等无集数的识别问题
              添加了中文支持

              ------------25.9.25 v0.9.4------------
              增加jjj彩蛋
              修复在字幕文件位置输入普通文本导致报错问题
              设计了第二版图标

              ------------25.9.26 v0.9.5------------
              添加回车键退出功能
              为jjj增加一次清屏

              ------------25.9.26 v0.9.6------------
              修复sp模式下输入无数字序列文件名的报错
              修复文字颜色不重置问题
              修正了中文翻译

              ------------25.9.26 v0.9.7------------
              优化文件名识别支持S1E01格式
              增加韩语、俄语、西班牙语等命名的集数
              同步更新sp部分的识别脚本

              ------------25.9.26 v0.9.8------------
              修复中文 第x话 识别，支持更多语言的文件名识别
              优化文件名自动识别机制
              爆改了中文翻译

              ----------以上是无聊的更新日志----------

              此程序由Gemini-CV(Ctrl+C+V)程序猿Yamada乱写制作
              请确定您获取的程序是免费白嫖的，如您已为此程序付费请直接退款并举报
              请访问 https://github.com/Yamada-da/SubRename 获取最新版（大概应该有）
              在issues里等待你遇到的奇葩问题（请附上文件名和描述）
              """)
        input("\n按回车键返回...")
        return 'restart'

    # Path parsing
    paths = re.findall(r'\"([^\"]+)\"|\'([^\']+)\'|(\S+)', paths_input)
    cleaned_paths = [item for sublist in paths for item in sublist if item]
    cleaned_paths = [path for path in cleaned_paths if path.strip() != '&']
    
    if not cleaned_paths:
        print(f"\n{COLOR_RED}错误：无效输入{COLOR_RESET}")
        input("按回车键返回...")
        return 'restart'

    # Path validation
    validated_paths = []
    invalid_found = False
    for path in cleaned_paths:
        if os.path.exists(path):
            validated_paths.append(path)
        else:
            invalid_found = True

    if not validated_paths or invalid_found and not validated_paths:
        print(f"\n{COLOR_RED}错误：文件路径无效，请尝试拖入文件，而非手动输入字符{COLOR_RESET}")
        input("按回车键返回...")
        return 'restart'

    return validated_paths


def get_language_from_filename(filename):
    """Extracts language code from a filename, e.g., '.sc.ass' -> 'sc'."""
    known_langs = {'ar', 'bg', 'ca', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'hi', 'hu', 'id', 'is', 'it', 'ja', 'jp', 'ko', 'lt', 'lv', 'ms', 'my', 'nb', 'ne', 'nl', 'nn', 'pl', 'pt', 'ro', 'ru', 'sc', 'sk', 'sl', 'sv', 'tc', 'th', 'tl', 'tr', 'uk', 'ur', 'vi', 'zh', 'ara', 'ces', 'chs', 'cht', 'chi', 'cho', 'dan', 'deu', 'ell', 'eng', 'fil', 'fin', 'fra', 'heb', 'hun', 'hy', 'ind', 'isl', 'ita', 'jpn', 'kor', 'lat', 'nor', 'pol', 'por', 'ron', 'rus', 'slk', 'slv', 'spa', 'swe', 'tha', 'tur', 'ukr', 'und', 'vie', 'zho', 'zxx', 'ensc', 'entc', 'enjp', 'jpen', 'jpsc', 'jptc', 'scjp', 'scen', 'tcjp', 'tcen', 'zh-CN', 'zh-HK', 'zh-MO', 'zh-SG', 'zh-TW', 'chs-eng', 'cht-eng', 'de-AT', 'de-CH', 'en-AU', 'en-CA', 'en-GB', 'en-IE', 'en-NZ', 'en-US', 'en-ZA', 'en_sc', 'en_tc', 'en+sc', 'en+tc', 'es-419', 'es-LA', 'es-MX', 'es-ES', 'fr-BE', 'fr-CA', 'it-CH', 'nl-BE', 'pt-BR', 'pt-PT', 'sc-en', 'sc-jp', 'sr-Cyrl', 'sr-Latn', 'tc-en', 'tc-jp', 'zh-Hans', 'zh-Hant', 'chs&jpn', 'cht&jpn', 'eng&jpn', 'en-forced'}
    # 如需增加对其他语言缩写的自动识别，请在此增补
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
            continue # Skip font files during initial language grouping
        
        episode_id = extract_episode_identifier(filename)
        if not episode_id:
            base_name_for_grouping = re.sub(r'(\.[a-zA-Z]{2,5})?\.[a-zA-Z]{2,4}$', '', filename)
            episode_id = f"_SINGLE_{base_name_for_grouping}" # Generic ID for files without numbers

        lang = get_language_from_filename(filename)
        if lang != "default":
            language_codes.add(lang)
        if episode_id not in episodes:
            episodes[episode_id] = {}
        episodes[episode_id][lang] = path

    if not episodes:
        return [], "default", False

    # Determine mode (series vs movie)
    has_series = any(not id.startswith("_SINGLE_") for id in episodes.keys())
    has_movies = any(id.startswith("_SINGLE_") for id in episodes.keys())

    if has_series and has_movies:
        print(f"{COLOR_RED}注意：文件中似乎混合了剧集和电影，本会话仅按剧集进行处理{COLOR_RESET}")
        
        movie_files_skipped = []
        for episode_id, lang_files in episodes.items():
            if episode_id.startswith("_SINGLE_"):
                for path in lang_files.values():
                    movie_files_skipped.append(os.path.basename(path))

        if movie_files_skipped:
            print(f"{COLOR_RED}以下非剧集文件将会被忽略：{COLOR_RESET}")
            for filename in sorted(movie_files_skipped):
                print(f"{COLOR_RED}- {filename}{COLOR_RESET}")

        episodes = {k: v for k, v in episodes.items() if not k.startswith("_SINGLE_")}
    
    is_movie_mode = not has_series and has_movies
    
    # --- Preset Logic ---
    preset_lang = CONFIG.get("PRESET_LANGUAGE")
    chosen_lang_str = None
    if isinstance(preset_lang, list):
        preset_lang_lower = [l.lower() for l in preset_lang]
        if 'all' in preset_lang_lower:
             print("\n找到预设 all ：正在处理识别到的所有语言")
             chosen_lang_str = 'all'
        else:
            found_preset = set(preset_lang_lower) & language_codes
            if found_preset:
                chosen_lang_str = sorted(list(found_preset))[0]
                print(f"\n找到预设 '{chosen_lang_str}' ：正在处理 '{chosen_lang_str}' 语言的字幕")
            else:
                 print(f"\n{COLOR_RED}未找到预设语言包含的字幕{COLOR_RESET}")
    
    # --- Interactive Logic ---
    if chosen_lang_str is None:
        if len(language_codes) > 1:
            print("\n识别到多种语言，请选择：")
            lang_list = sorted(list(language_codes))
            for i, lang_code in enumerate(lang_list):
                print(f"  {i + 1}. {lang_code}")
            print(f"  {len(lang_list) + 1}. all")
            while True:
                try:
                    choice = int(input(f"请选择您想处理的语言 (1-{len(lang_list) + 1}): "))
                    if 1 <= choice <= len(lang_list):
                        chosen_lang_str = lang_list[choice - 1]
                        break
                    elif choice == len(lang_list) + 1:
                        chosen_lang_str = "all"
                        break
                    else: print(f"{COLOR_RED}无效选择{COLOR_RESET}")
                except ValueError: print(f"{COLOR_RED}无效输入{COLOR_RESET}")
        elif language_codes:
            chosen_lang_str = language_codes.pop()
        else:
            chosen_lang_str = "default"

    # --- File Filtering ---
    files_to_process = []
    # Sort episodes naturally before processing
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

def ask_with_preset(config_key, question, options):
    """Generic function to ask a question or use a preset."""
    preset_value = CONFIG.get(config_key)
    if preset_value is not None and preset_value in options.keys():
        print(f"\n发现预设值 '{question}': 将选择 '{options[preset_value]}'进行处理")
        return preset_value
    
    print(f"\n{question}")
    for key, value in options.items():
        print(f"  {key}. {value}")
    
    while True:
        try:
            choice = int(input(f"请输入您的选择 ({'/'.join(map(str, options.keys()))}): "))
            if choice in options.keys():
                return choice
            else: print(f"{COLOR_RED}无效选择{COLOR_RESET}")
        except ValueError: print(f"{COLOR_RED}无效输入{COLOR_RESET}")

def ask_add_suffix(lang_choice):
    if lang_choice == "all":
        print("\n程序将添加对应语言缩写到目标文件名，防止文件名冲突")
        return True
    if lang_choice == "default": return False
    
    choice = ask_with_preset(
        "PRESET_ADD_SUFFIX",
        f"是否添加 '.{lang_choice}' 缩写到输出字幕文件名？",
        {1: "否", 2: "是"}
    )
    return choice == 2

def get_target_format(is_movie_mode=False):
    print("\n" + "-" * 50)
    if is_movie_mode:
        print("请输入目标视频的文件名（也可以直接拖入目标视频文件）")
    else:
        print("请输入目标视频的文件名（您也可以拖入任意一集目标视频文件）")
        print("示例: [Majo no Tabitabi][01][BDRIP][1080P][H24_FLAC]")
        print("或者，您可以输入'sp'进入特殊模式（将基于每集视频文件命名，用于处理每集有不同文件名的剧集）")
    print("-" * 50)
    while True:
        target_input = input("目标格式: ")
        
        if not is_movie_mode and target_input.lower() == 'sp': 
            return 'sp'

        cleaned_path = target_input.strip().strip('"\'')
        if os.path.isfile(cleaned_path):
            print(f"将使用以下格式: {os.path.basename(cleaned_path)}")
            target_format = os.path.basename(cleaned_path)
        else:
            target_format = target_input

        if re.search(r'[/\\:*\?"<>|]', target_format):
            print(f"{COLOR_RED}错误：格式包含非法字符{COLOR_RESET}")
            continue
        
        if not is_movie_mode and not re.search(r'\d+', target_format):
            print(f"{COLOR_RED}错误：格式中必须包含一个数字（例如，'01'）{COLOR_RESET}")
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
        # Use more specific patterns to find the episode number placeholder in the target format.
        patterns = [
            r'(?i)S\d{1,2}E(\d{1,3}(?:\.\d)?)',
            r'第(\d{1,3}(?:\.\d)?)(?:集|話|话)',
            r'(\d{1,3}(?:\.\d)?)\s*화',
            r'(?i)(?:Épisode|Episodio|Episódio|Episod)\s*(\d{1,3}(?:\.\d)?)',
            r'(?i)(?:ตอน(?:ที่)?)\s*(\d{1,3}(?:\.\d)?)',
            r'(?i)(?:Эпизод|Серия)\s*(\d{1,3}(?:\.\d)?)',
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
            print(f"{COLOR_RED}错误：未能在目标格式中识别到集数{COLOR_RESET}")
            print(f"{COLOR_RED}目标格式: '{target_format}'{COLOR_RESET}")
            return []

        placeholder_group_index = len(best_match.groups())
        placeholder_number_part = best_match.group(placeholder_group_index)
        
        padding = len(placeholder_number_part.split('.')[0]) if '.' in placeholder_number_part else len(placeholder_number_part)

        start, end = best_match.span(placeholder_group_index)

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
        video_prompt = "拖入目标文件，然后按回车键："
        cleaned_video_paths = get_files_from_user(video_prompt)
        
        if cleaned_video_paths == 'restart':
            return 'restart'

        if not cleaned_video_paths:
            print(f"\n{COLOR_RED}错误: 未找到视频文件 正在停止...{COLOR_RESET}")
            return None
        video_map = {}
        for v_path in cleaned_video_paths:
            v_filename = os.path.basename(v_path)
            episode_id = extract_episode_identifier(v_filename)
            if episode_id: video_map[episode_id] = v_path
            else: print(f"{COLOR_RED}警告：无法确定剧集 '{v_filename}' 集数ID，它将被忽略\n（请附上字幕及视频文件名，并在提交issue中描述下出现过程，感谢您的协助，它将会在未来版本修复）{COLOR_RESET}")

        for old_path, lang_code in files_with_lang:
            old_filename = os.path.basename(old_path)
            base_ext = "." + old_filename.split('.')[-1]
            episode_id = extract_episode_identifier(old_filename)
            if episode_id in video_map:
                video_basename = os.path.splitext(os.path.basename(video_map[episode_id]))[0]
                new_filename = f"{video_basename}.{lang_code}{base_ext}" if add_suffix and lang_code != 'default' else video_basename + base_ext
                rename_plan.append((old_path, new_filename))
            else:
                print(f"{COLOR_RED}警告：未找到与剧集 ID 为 '{episode_id}' 的字幕所匹配视频文件 跳过...{COLOR_RESET}")
    return rename_plan

def execute_rename_plan(rename_plan):
    """
    Executes the rename plan and returns the target directory and the user's choice about deleting originals.
    """
    if not rename_plan:
        print(f"\n{COLOR_RED}未执行重命名{COLOR_RESET}")
        return None, 1
        
    # Sort the final plan naturally based on the new filename
    rename_plan.sort(key=lambda item: natural_sort_key(item[1]))

    clear_screen()
    print("字幕文件将按照以下格式重命名，请确认：")
    print("=" * 60)
    for old_path, new_name in rename_plan:
        print(f"原: {os.path.basename(old_path)}\n    现 →: {new_name}\n")
    print("=" * 60)
    if input("按回车键继续，或输入其他任意键取消：") != "":
        print(f"\n{COLOR_RED}用户取消操作{COLOR_RESET}")
        return None, 1
    
    location_choice = ask_with_preset("PRESET_SAVE_LOCATION", "您想将字幕文件保存在哪个位置？", {1: "新建 'sub' 文件夹保存", 2: "在原字幕文件夹保存"})
    
    source_dir = os.path.dirname(rename_plan[0][0])
    target_dir = os.path.join(source_dir, 'sub') if location_choice == 1 else source_dir
    if location_choice == 1:
        os.makedirs(target_dir, exist_ok=True)
        print(f"\n已创建目录: {target_dir}")

    print("\n正在处理文件...")
    count = 0
    for old_path, new_name in rename_plan:
        try:
            shutil.copy2(old_path, os.path.join(target_dir, new_name))
            count += 1
        except Exception as e:
            print(f"{COLOR_RED}在复制 '{os.path.basename(old_path)}' 时出错: {e}{COLOR_RESET}")
    print(f"\n{COLOR_GREEN}已成功在 '{os.path.abspath(target_dir)} 中创建 {count} 个新文件'.{COLOR_RESET}")

    delete_choice = 1
    if count > 0:
        delete_choice = ask_with_preset("PRESET_DELETE_ORIGINALS", "是否删除原文件？", {1: "否", 2: "是"})
        if delete_choice == 2:
            print("\n正在删除原文件...")
            deleted_count = 0
            for old_path, _ in rename_plan:
                try:
                    os.remove(old_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"{COLOR_RED}删除 '{os.path.basename(old_path)}' 时出错: {e}{COLOR_RESET}")
            print(f"{COLOR_GREEN}成功删除 {deleted_count} 个原文件{COLOR_RESET}")
    return target_dir, delete_choice

def handle_unprocessed_files(all_files, processed_files, target_dir, delete_choice):
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
    action_verb = "移动" if delete_choice == 2 else "复制"

    if font_files:
        handle_fonts_choice = ask_with_preset(
            "PRESET_HANDLE_FONTS",
            "如何处理字体文件？",
            {1: "新建 'Fonts' 文件夹保存", 2: "忽略 (不进行操作)"}
        )
        if handle_fonts_choice == 1:
            print(f"\n正在 {action_verb} 字体文件...")
            fonts_dir = os.path.join(target_dir, "Fonts")
            os.makedirs(fonts_dir, exist_ok=True)
            font_count = 0
            for path in font_files:
                try:
                    if os.path.isdir(path):
                        if action == shutil.move:
                            for item_name in os.listdir(path):
                                source_item = os.path.join(path, item_name)
                                dest_item = os.path.join(fonts_dir, item_name)
                                shutil.move(source_item, dest_item)
                            os.rmdir(path)
                        else: # copy action
                            # dirs_exist_ok is available in Python 3.8+
                            if sys.version_info >= (3, 8):
                                shutil.copytree(path, fonts_dir, dirs_exist_ok=True)
                            else: # Fallback for older python
                                for item in os.listdir(path):
                                    s = os.path.join(path, item)
                                    d = os.path.join(fonts_dir, item)
                                    if os.path.isdir(s):
                                        shutil.copytree(s, d, symlinks=True)
                                    else:
                                        shutil.copy2(s, d)
                        font_count += 1
                    else: # It's a file
                        action(path, os.path.join(fonts_dir, os.path.basename(path)))
                        font_count += 1
                except Exception as e:
                    print(f"{COLOR_RED}在处理字体 '{os.path.basename(path)}' 时出错: {e}{COLOR_RESET}")
            print(f"{COLOR_GREEN}成功处理 {font_count} 个字体{COLOR_RESET}")


    if other_unprocessed:
        archive_choice = ask_with_preset(
            "PRESET_ARCHIVE_UNPROCESSED",
            f"是否将其他未处理的字幕文件{action_verb}到对应语言缩写的文件夹中？",
            {1: "是", 2: "否"}
        )
        if archive_choice == 1:
            print(f"\n正在 {action_verb} 未处理的字幕文件...")
            archived_count = 0
            for path in other_unprocessed:
                filename = os.path.basename(path)
                lang = get_language_from_filename(filename)
                if lang == "default":
                    lang = "misc"
                
                lang_dir = os.path.join(target_dir, lang)
                os.makedirs(lang_dir, exist_ok=True)
                
                try:
                    action(path, os.path.join(lang_dir, filename))
                    archived_count += 1
                except Exception as e:
                    print(f"{COLOR_RED}在处理 '{filename}' 时出错: {e}{COLOR_RESET}")
            print(f"{COLOR_GREEN}成功归档 {archived_count} 个未处理的字幕文件{COLOR_RESET}")

def main():
    while True:
        clear_screen()
        print("Subtitle Renamer (v 0.9.8)")
        all_subtitle_paths = get_files_from_user("请拖入所有待处理字幕文件并按回车: ")
        
        if all_subtitle_paths == 'restart':
            continue
        if not all_subtitle_paths: 
            break

        files_to_process, lang_choice, is_movie_mode = group_and_select_languages(all_subtitle_paths)
        if not files_to_process:
            print(f"\n{COLOR_RED}在所选的语言中未找到需要处理的文件{COLOR_RESET}")
        else:
            add_suffix = ask_add_suffix(lang_choice)
            target_format = None

            # Check for forced SP mode preset for series
            force_sp_preset = CONFIG.get("FORCE_SP_MODE")
            if not is_movie_mode and force_sp_preset == 1:
                print("\n找到预设: 自动进入 SP 模式（将基于每集视频文件命名，用于处理每集有不同文件名的剧集）")
                target_format = 'sp'
            
            # If not forced into SP mode, proceed with normal logic
            if target_format is None:
                if is_movie_mode:
                    print("\n" + "-" * 50)
                    print(f"{COLOR_RED}字幕文件中未找到集数{COLOR_RESET}")
                    movie_choice = ask_with_preset(
                        None, # This is a dynamic choice, not suitable for a simple preset
                        "如何继续？",
                        {
                            1: "电影模式（根据输入的单个目标文件名进行重命名）",
                            2: "剧集模式（尝试视为剧集，输入目标格式中需要包含数字）"
                        }
                    )
                    if movie_choice == 1:
                        target_format = get_target_format(is_movie_mode=True)
                    else: # Choice is 2
                        print("\n按照剧集模式运行")
                        is_movie_mode = False # Override detection
                        target_format = get_target_format(is_movie_mode=False)
                else: # Regular series mode
                    target_format = get_target_format(is_movie_mode=False)

            if not target_format:
                if input("\n按回车键重新开始，或输入其他任意键退出：") != "":
                    break
                else:
                    continue

            # Generate plan using the final is_movie_mode value which might have been overridden
            rename_plan = generate_rename_plan(files_to_process, target_format, add_suffix, is_movie_mode)
            
            if rename_plan == 'restart':
                continue

            target_dir, delete_choice = execute_rename_plan(rename_plan)

            if target_dir:
                processed_paths = [item[0] for item in rename_plan] if rename_plan else []
                handle_unprocessed_files(all_subtitle_paths, processed_paths, target_dir, delete_choice)

        if input("\n按回车键重新开始，或输入其他任意键退出：") != "":
            break

if __name__ == "__main__":
    if sys.platform == "win32":
        os.system('')
    main()

