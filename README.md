A plugin for HLL CRCON (see : https://github.com/MarechJ/hll_rcon_tool)
that does different things on chat commands :  
- `!me` displays statistic data about the player ;
- `!r` offers a "fast redeployment" option, avoiding the 10 secs penalty (autopunish)

![375490122-d8c7be50-aa6e-4949-b789-c327cacb2a1a](https://github.com/user-attachments/assets/4e9105d9-f87b-40e9-a489-da74cbb8f267)

Install (open this file for complete procedure) :
- Create `custom_tools` folder in CRCON's root (`/root/hll_rcon_tool/`) ;
- Copy `hooks_custom_chatcommands.py` in `/root/hll_rcon_tool/custom_tools/` ;
- Copy `restart.sh` in CRCON's root (`/root/hll_rcon_tool/`) ;
- Edit `/root/hll_rcon_tool/hooks.py` and add these lines:
  - in the import part, on top of the file
    ```python
    import custom_tools.hooks_custom_chatcommands as hooks_custom_chatcommands
    ```
  - At the very end of the file
    ```python
    @on_chat
    def commands_onchat(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
        hooks_custom_chatcommands.chat_commands(rcon, struct_log)
    ```
- Restart CRCON :
  ```shell
  cd /root/hll_rcon_tool
  sh ./restart.sh
  ```
⚠️ Any change to these files :
- `/root/hll_rcon_tool/custom_tools/hooks_custom_chatcommands.py` ;
- `/root/hll_rcon_tool/hooks.py`
... will need a CRCON restart with the above commands to be taken in account.
