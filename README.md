# SubRename
A lightweight tool designed to automate the renaming of subtitle files, specifically optimized for anime collections.<br/>

For Simplified Chinese version： [[简体中文]](https://github.com/Yamada-da/SubRename/blob/main/README.sc.md)

## How to Use
The program features built-in recognition logic for various filename patterns. Simply drag and drop your subtitle files into the window and follow the on-screen prompts (input the corresponding number) to choose your processing method.

## Q&A
**1. Drag & Drop Issues:** If you cannot drag files into the terminal window, please check your Windows UAC (User Account Control) settings. If UAC is set to "Never notify", the program may be running with elevated administrator privileges, which can block drag-and-drop. This program does not require administrator rights; enabling UAC notifications usually resolves this.<br/>
**2. Supported File Types:** The tool handles multiple subtitles per episode (with different language suffixes), movie subtitles (without episode numbers), filenames follow the pattern (The files are named by title and include a numeric sequence) and font files.<br/>
**3. Target Filenames:** You can manually type the target filename or simply drag and drop the target video file into the prompt.<br/>
**4. User Configuration:** You can bypass specific prompts by configuring the User Preset section in the code.
(The `PRESET_LANGUAGE` must be a list. When adding languages, ensure they are enclosed in brackets.
Example: "PRESET_LANGUAGE": ["en", "enjp"])<br/>
**5. Custom Language Tags:** To add more language abbreviations for recognition, add them to the 'known_langs = {}' dictionary within the script.<br/>

**If you encounter bugs, please **open an issue**. To help me fix it, please include:
The filenames, and a description of the error or unexpected behavior.**

Enjoy~
