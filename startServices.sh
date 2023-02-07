#! /bin/bash

cd $HOME
if [ "$watchTarget" == "masterofmalts" ]
then
    cd $HOME/masterOfMalts
    python3 watchMasterOfMalts.py
elif [ "$watchTarget" == "nickollsandperks" ]
then
    cd $HOME/nickollsandperks
    python3 watchNickollsAndPerks.py
fi