# Screenshot
![img](https://i.imgur.com/MwPk3BI.png)
# Installation & Setup 
- Make sure your OBS Studio supports [scripting](https://obsproject.com/docs/scripting.html)

# Usage 
Setup status displays:
- currently only via modifying source code

Setup interactive menu content:
- always via modifying source code

Default status displays:  
- current time
- current scene 
- mic status of selected source with audio via ([this script](https://github.com/upgradeQ/OBS-Mute-Indicator) installed separately) 

Default menu items:
- select sound to play (not implemented)
- toggle scene item  (not implemented)
- send hotkey to OBS from 0 to 8 
- print number*2 to script log from 0 to 8 ( as an example)

Default hotkeys:
- arrow up - selected next menu/sub menu
- arrow down - selected previous menu/sub menu
- arrow right - proceed to selection, then activate item 
- arrow left - reset to main menu
- 0 - toggle update of all status displays

Known issues:
- After creation of scene with text sources OBS *may* crash when exiting

# Contributions are welcome !
[Forks](https://help.github.com/articles/fork-a-repo) are a great way to contribute to a repository.
After forking a repository, you can send the original author a [pull request](https://help.github.com/articles/using-pull-requests)
